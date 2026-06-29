# AI: Claude Code | Opus 4.6 | 2026 April 18 | Purpose: Shared utility for emitting run summary fragments
# AI: Claude Code | Opus 4.8 | 2026 June 05 | Purpose: Add annogroup annotation lookup so downstream scripts can append Pfam accessions + definitions
# Human: Eric Edsinger

"""
Run Summary Fragment Utility

Each pipeline script (001-005) calls emit_run_summary_fragment() at the end of
its work with a dict of key stats. The fragment is written as JSON to:

    {workflow_dir}/ai/logs/run_summary_fragments/{script_number:03d}_{structure_id}.json

Script 007 (the aggregator) reads all fragments, aggregates across structures,
and builds RUN_SUMMARY.md at the workflow root. See Script 007 for the
aggregation rules and output format.

This fragment-first design solves the concurrent-write problem when 105
structures run in parallel -- each structure writes its own file rather than
appending to a shared document.
"""

import json
import sys
from datetime import datetime
from pathlib import Path


def get_fragments_directory( workflow_directory ):
    """
    Get the fragments directory for this workflow run.

    Args:
        workflow_directory: Path to workflow directory (contains ai/, INPUT_user/, etc.)

    Returns:
        Path: {workflow_directory}/ai/logs/run_summary_fragments/
    """
    workflow_path = Path( workflow_directory )
    return workflow_path / 'ai' / 'logs' / 'run_summary_fragments'


def emit_run_summary_fragment( script_number, structure_id, stats, source = None, workflow_directory = None ):
    """
    Write a run summary fragment for this (source, script, structure) tuple.

    Called by each pipeline script at the end of its work with a dict of
    interesting stats (counts, durations, key numbers). The aggregator
    (Script 009) reads all fragments and builds RUN_SUMMARY.md.

    Args:
        script_number: int, 1-6 for the per-structure analysis scripts
        structure_id: str, e.g. "001"
        stats: dict of stats to record. Expected keys vary by script but
               typically include 'duration_seconds' and script-specific counts.
        source: str, the annotation source (e.g. "pfam", "go", "panther"). The
               run fans out over sources x structures, so the fragment filename
               INCLUDES the source to keep per-source fragments distinct (without
               it, pfam structure_001 and go structure_001 would collide). None is
               accepted for backward compatibility (single-source runs).
        workflow_directory: Path to workflow directory. If None, inferred as
               two levels up from this script's __file__ location.

    Returns:
        Path to the written fragment file.
    """
    # Resolve workflow directory if not provided.
    # This script lives at: {workflow_dir}/ai/scripts/utils_run_summary.py
    # So workflow_dir is two levels up.
    if workflow_directory is None:
        workflow_directory = Path( __file__ ).parent.parent.parent

    fragments_directory = get_fragments_directory( workflow_directory )
    fragments_directory.mkdir( parents = True, exist_ok = True )

    if source:
        fragment_filename = f"{script_number:03d}_{source}_{structure_id}.json"
    else:
        fragment_filename = f"{script_number:03d}_{structure_id}.json"
    fragment_path = fragments_directory / fragment_filename

    # Add standard metadata
    fragment_data = {
        'script_number': script_number,
        'source': source,
        'structure_id': structure_id,
        'timestamp': datetime.now().isoformat(),
        'stats': stats
    }

    with open( fragment_path, 'w' ) as output_file:
        json.dump( fragment_data, output_file, indent = 2 )

    return fragment_path


def read_all_fragments( workflow_directory ):
    """
    Read all run summary fragments in a workflow's fragments directory.

    Args:
        workflow_directory: Path to workflow directory

    Returns:
        list of dicts, one per fragment, sorted by (script_number, structure_id)
    """
    fragments_directory = get_fragments_directory( workflow_directory )

    if not fragments_directory.exists():
        return []

    fragments = []
    for fragment_path in sorted( fragments_directory.glob( '*.json' ) ):
        try:
            with open( fragment_path, 'r' ) as input_file:
                fragment_data = json.load( input_file )
                fragments.append( fragment_data )
        except ( json.JSONDecodeError, IOError ):
            continue

    fragments.sort( key = lambda f: ( f.get( 'script_number', 0 ), f.get( 'source' ) or '', f.get( 'structure_id', '' ) ) )

    return fragments


def clear_fragments_directory( workflow_directory ):
    """
    Remove all existing fragments (called at start of a run to ensure clean state).

    Args:
        workflow_directory: Path to workflow directory
    """
    fragments_directory = get_fragments_directory( workflow_directory )

    if not fragments_directory.exists():
        return

    for fragment_path in fragments_directory.glob( '*.json' ):
        try:
            fragment_path.unlink()
        except OSError:
            pass


# ============================================================================
# Annogroup annotation lookup (Pfam accessions + definitions)
# ============================================================================
#
# Script 001 writes the authoritative annogroup map with two annotation columns:
#   Annotation_Accessions  -- comma delimited database accessions (e.g. PF00069);
#                             empty for the absent annogroup type
#   Annotation_Definitions -- semicolon delimited "definition ==accession" pairs, where
#                             definition is the InterProScan signature description
#                             (e.g. "Protein kinase domain ==PF00069; WD40 repeat ==PF00400")
#
# Downstream scripts (002, 003, 004) carry these two columns onto every output
# that bears an Annogroup_ID by looking them up here by Annogroup_ID. They are
# always appended as the final two columns so existing positional parsers (which
# read fixed low indices) are unaffected.


def sanitize_annotation_text( text ):
    """
    Make a single annotation field safe to embed inside one TSV column.

    Tabs and newlines would break the column/row structure, so they are
    collapsed to spaces. Commas, semicolons and '=' are left intact (the
    "definition ==accession" ... format relies on them and TSV only splits on
    tabs). Returns the cleaned string.
    """
    if text is None:
        return ''
    return text.replace( '\t', ' ' ).replace( '\r', ' ' ).replace( '\n', ' ' ).strip()


def format_annotation_definitions( accessions, accessions___descriptions ):
    """
    Build the Annotation_Definitions string for one annogroup.

    Accessions are DEDUPLICATED here (first-occurrence order preserved): a
    combo architecture can repeat the same accession many times (e.g. a protein
    with 300 PF00041 hits), but its definition only needs to appear once. The
    full multiplicity is retained in the separate Annotation_Accessions column;
    Annotation_Definitions is the unique domain glossary for the annogroup.

    Args:
        accessions: list of database accessions for this annogroup (may contain
            duplicates), in the same order used for Annotation_Accessions.
        accessions___descriptions: dict mapping accession -> definition text.

    Returns:
        str: semicolon delimited 'definition ==accession' pairs over the UNIQUE
             accessions, e.g. 'Protein kinase domain ==PF00069; WD40 repeat ==PF00400'.
             Note the literal ' ==' separator (space + two equals signs); the
             definition comes first so the column reads as human text with the
             accession appended for provenance. Missing definitions render as
             '==accession' (no leading text).
    """
    seen_accessions = set()
    pairs = []
    for accession in accessions:
        if accession in seen_accessions:
            continue
        seen_accessions.add( accession )
        definition = sanitize_annotation_text( accessions___descriptions.get( accession, '' ) )
        pairs.append( f"{definition} =={accession}" if definition else f"=={accession}" )
    return '; '.join( pairs )


def load_annogroup_annotation_lookup( annogroup_map_file ):
    """
    Load Annogroup_ID -> ( Annotation_Accessions, Annotation_Definitions ) from
    the Script 001 annogroup map. Used by downstream scripts (002, 003, 004) to
    append these two columns to their annogroup-bearing outputs.

    Columns are located by their header_ID (the text before the first ' (' in a
    self-documenting header), so column order in the map does not matter.

    Args:
        annogroup_map_file: Path to 1_ai-structure_NNN_annogroup_map.tsv

    Returns:
        dict: { annogroup_id: { 'accessions': str, 'definitions': str } }
              Empty dict if the file is missing or lacks the columns (callers
              then emit empty cells, never crash).
    """
    annogroup_ids___annotation_columns = {}

    map_path = Path( annogroup_map_file )
    if not map_path.exists():
        return annogroup_ids___annotation_columns

    with open( map_path, 'r' ) as input_file:
        # Annogroup_ID (...)	Annogroup_Type (...)	Annotation_Database (...)	Annotation_Accessions (...)	Annotation_Definitions (...)	...
        header_line = input_file.readline().rstrip( '\n' )
        header_parts = header_line.split( '\t' )

        column_names___indices = {}
        for index, column_header in enumerate( header_parts ):
            column_name = column_header.split( ' (' )[ 0 ] if ' (' in column_header else column_header
            column_names___indices[ column_name ] = index

        annogroup_id_index = column_names___indices.get( 'Annogroup_ID' )
        accessions_index = column_names___indices.get( 'Annotation_Accessions' )
        definitions_index = column_names___indices.get( 'Annotation_Definitions' )

        if annogroup_id_index is None:
            return annogroup_ids___annotation_columns

        for line in input_file:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            if annogroup_id_index >= len( parts ):
                continue
            annogroup_id = parts[ annogroup_id_index ]
            accessions = parts[ accessions_index ] if accessions_index is not None and accessions_index < len( parts ) else ''
            definitions = parts[ definitions_index ] if definitions_index is not None and definitions_index < len( parts ) else ''
            annogroup_ids___annotation_columns[ annogroup_id ] = {
                'accessions': accessions,
                'definitions': definitions
            }

    return annogroup_ids___annotation_columns


# ============================================================================
# Composite Clades — shared core (ported from annogroups, 2026-06-28)
# ============================================================================
# Self-contained copy of the annogroups composite-clades core so this OCL BLOCK
# stays autonomous. A "composite clade" is a user-defined question about where an
# annogroup's member species fall on the species tree; each manifest row names an
# ALGORITHM (exact / absent / core_urclade / core_early_clade). See the subproject
# README / AI_GUIDE for definitions (Ur = a clade's last common ancestor; Early =
# its early descendant branches = the species tree's ambiguous/unresolved nodes).

DELIM = ','

COMPOSITE_CLADE_ALGORITHMS = ( "exact", "absent", "core_urclade", "core_early_clade" )


def build_header_index( header_line: str ) -> dict:
    """Map self-documenting header IDs ('Clade_ID_Name (...)' -> 'Clade_ID_Name') to indices."""
    header_ids___indices = {}
    parts_header_line = header_line.rstrip( '\n' ).split( '\t' )
    for index, column in enumerate( parts_header_line ):
        header_id = column.split( ' (' )[ 0 ].strip()
        header_ids___indices[ header_id ] = index
    return header_ids___indices


def load_clade_species( mappings_path: Path, reference_structure: str, clade_id_name: str ) -> set:
    """
    Read a clade's descendant-species set (Genus_species) for one structure from the
    trees_species clade->species mapping. Returns a set; empty if not found.
    """
    clade_species = set()
    with open( mappings_path, 'r' ) as input_mappings:
        header_ids___indices = build_header_index( input_mappings.readline() )
        index_structure = header_ids___indices[ "Structure_ID" ]
        index_clade = header_ids___indices[ "Clade_ID_Name" ]
        index_species_list = header_ids___indices[ "Descendant_Species_List" ]
        for line in input_mappings:
            line = line.rstrip( '\n' )
            if not line:
                continue
            parts = line.split( '\t' )
            if parts[ index_structure ] == reference_structure and parts[ index_clade ] == clade_id_name:
                species_cell = parts[ index_species_list ] if index_species_list < len( parts ) else ""
                clade_species = { s for s in species_cell.split( ',' ) if s }
                break
    return clade_species


def load_composite_clades( config: dict, mappings_path: Path ) -> dict:
    """
    Load composite-clade building-block groups + scope from config['composite_clades']
    and resolve them to species sets (clade->species at the reference structure).
    Returns { names, names___species, scope_species, outside_label, scope_clade_id_name,
    scope_name, reference_structure, mappings_path }. Fail-fast on zero species.
    """
    block = config.get( "composite_clades" )
    if not block:
        print( "CRITICAL ERROR: config is missing the 'composite_clades' block", file = sys.stderr )
        sys.exit( 1 )
    reference_structure = block[ "reference_structure" ]
    scope_clade_id_name = block[ "scope_clade_id_name" ]
    outside_label = block[ "outside_label" ]

    scope_species = load_clade_species( mappings_path, reference_structure, scope_clade_id_name )
    if not scope_species:
        print( f"CRITICAL ERROR: scope clade '{scope_clade_id_name}' resolved to zero species for {reference_structure}", file = sys.stderr )
        sys.exit( 1 )

    names = []
    names___species = {}
    for group in block[ "groups" ]:
        group_name = group[ "name" ]
        group_species = set()
        for clade_id_name in group[ "clade_id_names" ]:
            group_species |= load_clade_species( mappings_path, reference_structure, clade_id_name )
        if not group_species:
            print( f"CRITICAL ERROR: composite clade '{group_name}' resolved to zero species "
                   f"(clades {group[ 'clade_id_names' ]}, {reference_structure})", file = sys.stderr )
            sys.exit( 1 )
        names.append( group_name )
        names___species[ group_name ] = group_species

    scope_name = scope_clade_id_name.split( '_', 1 )[ 1 ] if '_' in scope_clade_id_name else scope_clade_id_name
    return { "names": names, "names___species": names___species,
             "scope_species": scope_species, "outside_label": outside_label,
             "scope_clade_id_name": scope_clade_id_name, "scope_name": scope_name,
             "reference_structure": reference_structure, "mappings_path": mappings_path }


def exact_components_of_species( member_species: set, composites: dict ) -> list:
    """The EXACT ordered components an annogroup occupies (config-order groups it has a
    member species in, then the outside label when it has members outside the scope)."""
    components = [ name for name in composites[ "names" ]
                  if member_species & composites[ "names___species" ][ name ] ]
    if member_species - composites[ "scope_species" ]:
        components.append( composites[ "outside_label" ] )
    return components


def composite_clade_id_auto( ordered_tokens: list, algorithm: str ) -> str:
    """Auto identifier for the deterministic algorithms: cc_<tokens>-<algorithm>."""
    return "cc_" + "_".join( ordered_tokens ) + "-" + algorithm


def composite_clade_id( ordered_components: list ) -> str:
    """Exact composite-clade identifier: cc_<components>-exact."""
    return composite_clade_id_auto( ordered_components, "exact" )


def composite_clade_id_named( name: str, algorithm: str ) -> str:
    """User-named identifier: cc_<Name>-<algorithm> (core_urclade / core_early_clade)."""
    return f"cc_{name}-{algorithm}"


def resolve_clade_species( name: str, composites: dict ) -> set:
    """Resolve a manifest clade NAME (group name / scope name / scope or raw clade_id_name)
    to its species set. Fail-fast on an unresolvable name."""
    if name in composites[ "names___species" ]:
        return composites[ "names___species" ][ name ]
    if name == composites[ "scope_name" ] or name == composites[ "scope_clade_id_name" ]:
        return composites[ "scope_species" ]
    species = load_clade_species( composites[ "mappings_path" ], composites[ "reference_structure" ], name )
    if not species:
        print( f"CRITICAL ERROR: composite_clades manifest clade '{name}' is not a config group, "
               f"the scope ({composites[ 'scope_name' ]}), or a known clade_id_name for "
               f"{composites[ 'reference_structure' ]}", file = sys.stderr )
        sys.exit( 1 )
    return species


def _component_detail_column( component: str, composites: dict ) -> tuple:
    """Detail-table column spec ( label, kind, species_set ) for a building-block component."""
    if component == composites[ "outside_label" ]:
        return ( component, "out", composites[ "scope_species" ] )
    return ( component, "in", composites[ "names___species" ][ component ] )


def _order_absent_clades( clades: list, composites: dict ) -> list:
    """Canonical order for an absent clade list (config-order groups+outside, then scope, then alpha)."""
    valid_components = list( composites[ "names" ] ) + [ composites[ "outside_label" ] ]
    component_order = { component: index for index, component in enumerate( valid_components ) }

    def order_key( name ):
        if name in component_order:
            return ( 0, component_order[ name ], name )
        if name == composites[ "scope_name" ] or name == composites[ "scope_clade_id_name" ]:
            return ( 1, 0, name )
        return ( 2, 0, name )

    return sorted( set( clades ), key = order_key )


def load_composite_clades_manifest( manifest_path: Path, composites: dict ) -> list:
    """
    Read the columnar composite-clades manifest (Algorithm  Name  Target_Clade  Clades).
    exact + absent auto-named; core_* user-named. Returns a list of validated entry dicts.
    Fail-fast on unknown algorithm, missing fields, unknown clade, or empty manifest.
    """
    entries = []
    seen_ids = set()
    with open( manifest_path, 'r' ) as input_manifest:
        for line in input_manifest:
            line = line.rstrip( '\n' )
            if not line.strip() or line.lstrip().startswith( '#' ):
                continue
            parts = line.split( '\t' )
            while len( parts ) < 4:
                parts.append( '' )
            algorithm = parts[ 0 ].strip()
            name = parts[ 1 ].strip()
            target_name = parts[ 2 ].strip()
            clades = [ token.strip() for token in parts[ 3 ].split( ',' ) if token.strip() ]

            if algorithm.lower() == "algorithm":
                continue
            if algorithm not in COMPOSITE_CLADE_ALGORITHMS:
                print( f"CRITICAL ERROR: composite_clades manifest row '{line}' has unknown algorithm "
                       f"'{algorithm}'; valid: {', '.join( COMPOSITE_CLADE_ALGORITHMS )}", file = sys.stderr )
                sys.exit( 1 )
            if not clades:
                print( f"CRITICAL ERROR: composite_clades manifest row '{line}' lists no clades (column 4)", file = sys.stderr )
                sys.exit( 1 )

            entry = _build_composite_clade_entry( algorithm, name, target_name, clades, composites, line )
            if entry[ "cc_id" ] in seen_ids:
                continue
            seen_ids.add( entry[ "cc_id" ] )
            entries.append( entry )

    if not entries:
        print( f"CRITICAL ERROR: composite_clades manifest has no entries: {manifest_path}", file = sys.stderr )
        sys.exit( 1 )
    return entries


def _build_composite_clade_entry( algorithm, name, target_name, clades, composites, raw_line ):
    """Validate one manifest row and build its composite-clade entry (per algorithm)."""
    valid_components = list( composites[ "names" ] ) + [ composites[ "outside_label" ] ]
    component_order = { component: index for index, component in enumerate( valid_components ) }

    if algorithm == "exact":
        unknown = [ token for token in clades if token not in component_order ]
        if unknown:
            print( f"CRITICAL ERROR: composite_clades exact row '{raw_line}' has unknown component(s) {unknown}; "
                   f"valid components are {valid_components}", file = sys.stderr )
            sys.exit( 1 )
        ordered = sorted( set( clades ), key = lambda token: component_order[ token ] )
        return { "algorithm": "exact", "name": "", "cc_id": composite_clade_id( ordered ),
                 "components": ordered, "components_frozenset": frozenset( ordered ),
                 "definition": ','.join( ordered ),
                 "detail_columns": [ _component_detail_column( component, composites ) for component in ordered ] }

    if algorithm == "absent":
        absent_from_outside = composites[ "outside_label" ] in clades
        union_species = set()
        for clade in ( clade for clade in clades if clade != composites[ "outside_label" ] ):
            union_species |= resolve_clade_species( clade, composites )
        ordered_clades = _order_absent_clades( clades, composites )
        detail_columns = [ _component_detail_column( group, composites ) for group in composites[ "names" ] ]
        detail_columns.append( ( composites[ "outside_label" ], "out", composites[ "scope_species" ] ) )
        return { "algorithm": "absent", "name": "", "cc_id": composite_clade_id_auto( ordered_clades, "absent" ),
                 "clades": ordered_clades, "union_species": union_species, "absent_from_outside": absent_from_outside,
                 "definition": "absent from " + ','.join( ordered_clades ),
                 "detail_columns": detail_columns }

    if not name:
        print( f"CRITICAL ERROR: composite_clades {algorithm} row '{raw_line}' needs a Name (column 2)", file = sys.stderr )
        sys.exit( 1 )
    if not target_name:
        print( f"CRITICAL ERROR: composite_clades {algorithm} row '{raw_line}' needs a Target_Clade (column 3)", file = sys.stderr )
        sys.exit( 1 )
    target_species = resolve_clade_species( target_name, composites )
    ingroups___species = { ingroup: resolve_clade_species( ingroup, composites ) for ingroup in clades }
    ingroup_union = set().union( *ingroups___species.values() )

    if algorithm == "core_urclade":
        detail_columns = [ ( ingroup, "in", ingroups___species[ ingroup ] ) for ingroup in clades ]
        detail_columns.append( ( f"Outside_{target_name}", "out", target_species ) )
        return { "algorithm": "core_urclade", "name": name, "cc_id": composite_clade_id_named( name, "core_urclade" ),
                 "target_name": target_name, "target_species": target_species,
                 "ingroups": clades, "ingroups___species": ingroups___species, "ingroup_union": ingroup_union,
                 "definition": f"target {target_name}; ingroups " + ','.join( clades ),
                 "detail_columns": detail_columns }

    detail_columns = [ ( ingroup, "in", ingroups___species[ ingroup ] ) for ingroup in clades ]
    return { "algorithm": "core_early_clade", "name": name, "cc_id": composite_clade_id_named( name, "core_early_clade" ),
             "target_name": target_name, "target_species": target_species,
             "ingroups": clades, "ingroups___species": ingroups___species, "ingroup_union": ingroup_union,
             "definition": f"target {target_name}; ingroups " + ','.join( clades ) + " (present in >=2)",
             "detail_columns": detail_columns }


def annogroup_matches_composite_clade( entry: dict, member_species: set, composites: dict ) -> bool:
    """True if an annogroup's member species match one composite-clade entry (per its algorithm)."""
    algorithm = entry[ "algorithm" ]
    if algorithm == "exact":
        return frozenset( exact_components_of_species( member_species, composites ) ) == entry[ "components_frozenset" ]
    if algorithm == "absent":
        if member_species & entry[ "union_species" ]:
            return False
        if entry[ "absent_from_outside" ] and ( member_species - composites[ "scope_species" ] ):
            return False
        return True
    if algorithm == "core_urclade":
        return bool( member_species - entry[ "target_species" ] ) and bool( member_species & entry[ "ingroup_union" ] )
    if algorithm == "core_early_clade":
        present = sum( 1 for ingroup_species in entry[ "ingroups___species" ].values() if member_species & ingroup_species )
        return present >= 2
    return False
