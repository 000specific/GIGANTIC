# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 18 | Purpose: Shared helpers + parser-plugin interface for the annogroups framework
# Human: Eric Edsinger

"""
Shared helpers for the annogroups subproject.

The annogroups framework builds the four canonical annogroup types — feature,
combination, architecture, absent — per source database, from the per-source
annotation outputs of annotations_hmms. The construction of the four types is
identical for every source; only the parsing of a source's annotations into a
normalized per-sequence feature list is source-specific.

Parser-plugin contract
-----------------------
Each source has a parser module at `parsers/<source>.py` exposing:

    SOURCE = "<source>"                          # e.g. "pfam"

    def parse_source_features( workflow_root, config ) -> dict:
        '''
        Return { sequence_identifier: [ Feature, Feature, ... ] } for every
        sequence in the species set that has >=1 feature from this source.
        Feature is a utils_annogroups.Feature namedtuple:
            ( accession, start, stop, is_positional )
        start/stop are ints for positional features; None for whole-protein /
        position-less features (is_positional = False).
        '''

Adding a source = drop a new `parsers/<source>.py` in; nothing else changes.
"""

import sys
from collections import namedtuple
from pathlib import Path
import yaml

# In-column multi-value delimiter — bare comma per gigantic_conventions §34.
DELIM = ','


# ============================================================================
# Composite Clades (configurable species-tree clade groupings, 2026-06-27)
# ============================================================================
# A "composite clade" is a user-defined named group of one or more species-tree
# clades, used to ask a focused question about where a feature unit's member
# species fall on the species tree. The building-block GROUPS are defined in
# START_HERE-user_config.yaml under `composite_clades` (default: the five metazoan
# clades Ctenophora, Porifera, Placozoa, Cnidaria, Bilateria within the Metazoa
# scope; members outside the scope carry the outside label, e.g. NonMetazoa).
# These are CLADES, not phyla — Bilateria is a clade (not a phylum); the machinery
# operates on ANY species-tree clades. The composite clades to REPORT are curated in
# INPUT_user/composite_clades_manifest.tsv. This GENERALIZES the earlier hardcoded
# analysis that fixed those five metazoan clades.
#
# Each manifest row names an ALGORITHM that tests an annogroup's member species:
#   - exact            : members come from EXACTLY the listed component clades
#                        (one-per-annogroup; auto-named cc_<components>-exact)
#   - absent           : members are ABSENT from ALL listed clades
#   - core_urclade     : members in >=1 OUTGROUP of the target clade AND >=1 listed
#                        ingroup -> the target's Ur (last-common-ancestor) core
#   - core_early_clade : members in >=2 listed ingroups, where the ingroups are the
#                        ambiguous (unresolved) nodes defining the target's "Early"
#                        window (its early descendant branches)
# `Ur` = last common ancestor of a clade; `Early` = the early descendants of a
# clade (the phylogenetic window spanned by the species tree's ambiguous nodes).
# absent / core_urclade / core_early_clade are independent membership tests, so one
# annogroup may match several composite clades of those algorithms at once.
# NOTE: composition is over the trees_species clade groupings, NOT the raw NCBI
# Phylum field used by phylum_from_phyloname() elsewhere in this module.


def load_composite_clades( config: dict, mappings_path: Path ) -> dict:
    """
    Load composite-clade definitions from config['composite_clades'] and resolve
    each group + the scope to species sets (from the trees_species clade->species
    mapping at the configured reference structure; Rule 6 => stable across trees).

    config['composite_clades'] schema:
        reference_structure : str       (structure whose clade->species to read)
        scope_clade_id_name : str       (ancestor the groups ideally partition)
        outside_label       : str       (name for members outside the scope)
        groups : [ { name: str, clade_id_names: [ clade_id_name, ... ] }, ... ]

    Returns dict { names, names___species, scope_species, outside_label } where
    `names` preserves config order (the signature order).

    Fail-fast: exits 1 if the block, a group's clades, or the scope resolve to zero
    species (a typo must not silently mis-classify every feature).
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

    # Display name for the scope clade (e.g. "Metazoa" from "C082_Metazoa"), so the
    # manifest can name the scope as a target without the clade_id prefix.
    scope_name = scope_clade_id_name.split( '_', 1 )[ 1 ] if '_' in scope_clade_id_name else scope_clade_id_name

    return { "names": names, "names___species": names___species,
             "scope_species": scope_species, "outside_label": outside_label,
             "scope_clade_id_name": scope_clade_id_name, "scope_name": scope_name,
             "reference_structure": reference_structure, "mappings_path": mappings_path }


def exact_components_of_species( member_species: set, composites: dict ) -> list:
    """
    The EXACT set of composite-clade components a feature unit occupies, from its
    member species, as an ordered list: the configured groups it has >=1 member
    species in (in config order), then the outside label when it has any member
    species outside the scope clade. This ordered list canonically names the
    feature's composite clade (see composite_clade_id).
    """
    components = [ name for name in composites[ "names" ]
                  if member_species & composites[ "names___species" ][ name ] ]
    if member_species - composites[ "scope_species" ]:
        components.append( composites[ "outside_label" ] )
    return components


def composite_clade_id_auto( ordered_tokens: list, algorithm: str ) -> str:
    """
    Auto-derived identifier for the DETERMINISTIC algorithms (exact, absent), which
    do not vary for a given clade set and therefore need no user name or number:
        cc_<token1>_<token2>_..._-<algorithm>
    e.g. composite_clade_id_auto( [ 'NonMetazoa' ], 'absent' ) -> 'cc_NonMetazoa-absent';
         composite_clade_id_auto( [ 'Porifera', 'Cnidaria' ], 'exact' ) -> 'cc_Porifera_Cnidaria-exact'.
    """
    return "cc_" + "_".join( ordered_tokens ) + "-" + algorithm


def composite_clade_id( ordered_components: list ) -> str:
    """Exact composite-clade identifier: cc_<components>-exact (see composite_clade_id_auto)."""
    return composite_clade_id_auto( ordered_components, "exact" )


# The four composite-clade algorithms (see the module header for definitions).
COMPOSITE_CLADE_ALGORITHMS = ( "exact", "absent", "core_urclade", "core_early_clade" )


def composite_clade_id_named( name: str, algorithm: str ) -> str:
    """
    Canonical identifier for a user-named composite clade (absent / core_urclade /
    core_early_clade):  cc_<Name>-<algorithm>
    e.g. composite_clade_id_named( 'Urmetazoa_001', 'core_urclade' )
         -> 'cc_Urmetazoa_001-core_urclade'.
    (`exact` composite clades are auto-named from their components by composite_clade_id.)
    """
    return f"cc_{name}-{algorithm}"


def resolve_clade_species( name: str, composites: dict ) -> set:
    """
    Resolve a composite-clades manifest clade NAME to its species set. A name may be
    a config group name (e.g. Ctenophora), the scope clade's display name or its
    clade_id_name (Metazoa / C082_Metazoa), or any raw clade_id_name present in the
    trees_species mapping at the reference structure. Fail-fast on an unresolvable
    name (a typo must not silently mis-classify every annogroup).
    """
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
    """
    Build one detail-table column spec ( label, kind, species_set ) for a building-
    block component. The outside label is a complement column ('out' = species NOT
    in the scope); a group is an 'in' column (species in that group).
    """
    if component == composites[ "outside_label" ]:
        return ( component, "out", composites[ "scope_species" ] )
    return ( component, "in", composites[ "names___species" ][ component ] )


def _order_absent_clades( clades: list, composites: dict ) -> list:
    """
    Canonical order for an absent composite clade's clade list (so its auto-derived
    cc_id is deterministic regardless of how the user listed them): building-block
    groups + the outside label in config order, then the scope name, then any other
    names alphabetically.
    """
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
    Read the curated composite-clades manifest — a columnar TSV, one composite clade
    per row, with columns:

        Algorithm <TAB> Name <TAB> Target_Clade <TAB> Clades

      - Algorithm    : exact | absent | core_urclade | core_early_clade
      - Name         : the composite clade's short name (blank for exact, which
                       auto-names from its components); required for the others
      - Target_Clade : the focal clade (core_urclade / core_early_clade); blank for
                       exact and absent
      - Clades       : comma-delimited clade names — the COMPONENTS (exact), the
                       clades the members must be ABSENT from (absent), or the
                       INGROUPS (core_urclade / core_early_clade)

    Blank lines, '#'-comment lines, and a header row (column 0 == 'Algorithm') are
    skipped. Each clade name resolves via resolve_clade_species. Returns a list of
    entry dicts (config/manifest order), each carrying its algorithm, cc_id, a human-
    readable definition, the resolved species sets the matching test needs, and the
    detail-table column specs. Fail-fast on unknown algorithm, missing fields, an
    unknown clade, or an empty manifest.
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

            if algorithm.lower() == "algorithm":           # header row
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
        # exact / absent do not vary for a given clade set -> auto-named, no user Name.
        # The outside label (e.g. NonMetazoa) is allowed: "absent from <outside>" means
        # no members fall outside the scope clade.
        absent_from_outside = composites[ "outside_label" ] in clades
        union_species = set()
        for clade in ( clade for clade in clades if clade != composites[ "outside_label" ] ):
            union_species |= resolve_clade_species( clade, composites )
        ordered_clades = _order_absent_clades( clades, composites )
        # Detail columns show where the members ARE (the building-block groups +
        # outside) -- by definition none fall in the absent-from clades.
        detail_columns = [ _component_detail_column( group, composites ) for group in composites[ "names" ] ]
        detail_columns.append( ( composites[ "outside_label" ], "out", composites[ "scope_species" ] ) )
        return { "algorithm": "absent", "name": "", "cc_id": composite_clade_id_auto( ordered_clades, "absent" ),
                 "clades": ordered_clades, "union_species": union_species, "absent_from_outside": absent_from_outside,
                 "definition": "absent from " + ','.join( ordered_clades ),
                 "detail_columns": detail_columns }

    # core_urclade / core_early_clade -- need a user Name + a target clade + ingroups
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

    # core_early_clade
    detail_columns = [ ( ingroup, "in", ingroups___species[ ingroup ] ) for ingroup in clades ]
    return { "algorithm": "core_early_clade", "name": name, "cc_id": composite_clade_id_named( name, "core_early_clade" ),
             "target_name": target_name, "target_species": target_species,
             "ingroups": clades, "ingroups___species": ingroups___species, "ingroup_union": ingroup_union,
             "definition": f"target {target_name}; ingroups " + ','.join( clades ) + " (present in >=2)",
             "detail_columns": detail_columns }


def annogroup_matches_composite_clade( entry: dict, member_species: set, composites: dict ) -> bool:
    """
    True if an annogroup (its set of member Genus_species) matches one composite-clade
    manifest entry, per that entry's algorithm:
      - exact            : the annogroup's exact component set equals the entry's
      - absent           : no member species in ANY of the entry's clades
      - core_urclade     : >=1 member outside the target AND >=1 member in an ingroup
      - core_early_clade : members in >=2 of the entry's ingroups
    """
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


def load_clade_species( mappings_path: Path, reference_structure: str, clade_id_name: str ) -> set:
    """
    Read a clade's descendant-species set (Genus_species) for one structure from
    the trees_species clade->species mapping. Returns a set; empty if not found
    (caller should fail-fast on empty for required clades).
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

# One annotation-feature instance on a sequence.
#   accession      : the source annotation identifier (e.g. 'PF00001')
#   start, stop    : residue coordinates (int) for positional features, else None
#   is_positional  : True if the feature has a sequence location (orderable)
Feature = namedtuple( 'Feature', [ 'accession', 'start', 'stop', 'is_positional' ] )


def load_config( config_path: str ) -> dict:
    """Load START_HERE-user_config.yaml into a nested dict."""
    with open( config_path, 'r' ) as input_config:
        config = yaml.safe_load( input_config )
    return config


def workflow_root_from_output_dir( output_dir: str ) -> Path:
    """
    The workflow root is the parent of OUTPUT_pipeline. Input paths in the YAML
    are written relative to the workflow root (gigantic_conventions §5).
    """
    return Path( output_dir ).resolve().parent


def resolve_input_path( workflow_root: Path, relative_path: str ) -> Path:
    """Resolve a YAML-relative input path against the workflow root."""
    return ( workflow_root / relative_path ).resolve()


def genus_species_from_phyloname( phyloname: str ) -> str:
    """
    Extract Genus_species from a GIGANTIC phyloname
    (Kingdom_Phylum_Class_Order_Family_Genus_species; genus+species at parts[5:]).
    Multi-word species (e.g. Hoilungia_hongkongensis_H13) are preserved.
    """
    parts_phyloname = phyloname.split( '_' )
    if len( parts_phyloname ) >= 7:
        return '_'.join( parts_phyloname[ 5: ] )
    return phyloname


def genus_species_from_full_id( full_id: str ) -> str:
    """Genus_species from a full GIGANTIC sequence ID (… -n_<phyloname>)."""
    if '-n_' not in full_id:
        return ''
    return genus_species_from_phyloname( full_id.split( '-n_' )[ -1 ] )


def phylum_from_phyloname( phyloname: str ) -> str:
    """
    Phylum field from a GIGANTIC phyloname
    (Kingdom_Phylum_Class_Order_Family_Genus_species; Phylum at parts[1]).
    May be 'UNOFFICIAL' or 'PhylumNNNNN' for unplaced taxa — returned as-is.
    """
    parts_phyloname = phyloname.split( '_' )
    if len( parts_phyloname ) >= 2:
        return parts_phyloname[ 1 ]
    return ''


def phylum_from_full_id( full_id: str ) -> str:
    """Phylum from a full GIGANTIC sequence ID (… -n_<phyloname>)."""
    if '-n_' not in full_id:
        return ''
    return phylum_from_phyloname( full_id.split( '-n_' )[ -1 ] )


def build_header_index( header_line: str ) -> dict:
    """
    Map self-documenting header IDs to column indices. A GIGANTIC header column
    looks like 'Match_Start (residue start position)'; the header_ID is the text
    before ' ('. Returns { header_ID : index }.
    """
    header_ids___indices = {}
    parts_header_line = header_line.rstrip( '\n' ).split( '\t' )
    for index, column in enumerate( parts_header_line ):
        header_id = column.split( ' (' )[ 0 ].strip()
        header_ids___indices[ header_id ] = index
    return header_ids___indices


def annogroup_counter_id( source: str, annogroup_type: str, counter: int ) -> str:
    """
    Canonical counter-based annogroup identifier for combination / architecture:
        annogroup_<source>_<type><zero-padded counter>
    e.g. annogroup_pfam_architecture00001, annogroup_superfamilies_combination00010.
    """
    return f"annogroup_{source}_{annogroup_type}{counter:05d}"


def annogroup_feature_id( source: str, accession: str ) -> str:
    """Natural feature annogroup identifier: annogroup_<source>_<accession>."""
    return f"annogroup_{source}_{accession}"


def annogroup_absent_id( source: str ) -> str:
    """Absent annogroup identifier: annogroup_<source>_absent."""
    return f"annogroup_{source}_absent"


def architecture_member_string( ordered_features ) -> str:
    """
    The coordinate-tagged ordered feature list stored on a sequence's
    architecture membership row: 'PF00001_start10_stop50,PF00001_start100_stop150,...'
    ordered_features is a list of Feature (positional, already N→C ordered).
    """
    return DELIM.join( f"{feature.accession}_start{feature.start}_stop{feature.stop}"
                       for feature in ordered_features )


def sanitize_annotation_text( text: str ) -> str:
    """
    Make one annotation description safe to embed in a single TSV column. Tabs
    and newlines would break the column/row structure, so they collapse to
    spaces. Commas, semicolons and '=' are left intact (the 'definition ==accession'
    format relies on them; TSV only splits on tabs).
    """
    if text is None:
        return ''
    return text.replace( '\t', ' ' ).replace( '\r', ' ' ).replace( '\n', ' ' ).strip()


def format_annotation_definitions( accessions, accessions___definitions ) -> str:
    """
    Build the Annotation_Definitions string for one annogroup — the canonical
    GIGANTIC format shared with the OCL / integrator outputs.

    Accessions are DEDUPLICATED (first-occurrence order preserved): an
    architecture can repeat the same accession, but its definition appears once.

    Returns semicolon-delimited 'definition ==accession' pairs over the UNIQUE
    accessions, e.g. 'Protein kinase domain ==PF00069; WD40 repeat ==PF00400'.
    Note the literal ' ==' separator (space + two equals). Missing definitions
    render as '==accession' (no leading text).
    """
    seen_accessions = set()
    pairs = []
    for accession in accessions:
        if accession in seen_accessions:
            continue
        seen_accessions.add( accession )
        definition = sanitize_annotation_text( accessions___definitions.get( accession, '' ) )
        pairs.append( f"{definition} =={accession}" if definition else f"=={accession}" )
    return '; '.join( pairs )


# ============================================================================
# Category (aspect) split columns — generic, parser-driven (2026-06-28)
# ============================================================================
# A source whose annotations fall into a small fixed set of CATEGORIES (e.g. GO's
# three aspects: molecular_function, biological_process, cellular_component) can
# split each annogroup's defining accessions into per-category identifier +
# definition columns. The parser declares this via:
#     CATEGORIES = [ ( category_key, column_label ), ... ]   (module attribute)
#     parse_source_categories( workflow_root, config ) -> { accession: category_key }
# The map builder (Script 002) then emits two columns per category
# (<label>_Identifiers, <label>_Definitions) right after Annotation_Definitions.
# Sources without CATEGORIES are unaffected. Downstream scripts carry these extra
# columns forward generically via carry_forward_map_columns() — they need no
# per-source knowledge.


def category_aspect_headers( category_specs: list ) -> list:
    """
    The self-documenting header strings for the per-category split columns: two per
    category — <label>_Identifiers then <label>_Definitions — in category_specs order.
    category_specs is the parser's CATEGORIES: list of ( category_key, column_label ).
    """
    headers = []
    for ( category_key, label ) in category_specs:
        headers.append( f"{label}_Identifiers (comma delimited accessions of this annogroup whose category is {category_key})" )
        headers.append( f"{label}_Definitions (comma delimited definitions for {label}_Identifiers, in the same order)" )
    return headers


def category_aspect_values( accessions, accessions___definitions, accessions___categories, category_specs ) -> list:
    """
    The per-category split cell values for one annogroup: for each category (in
    category_specs order) the comma-delimited accessions whose category matches
    (in the given accession order), then their comma-delimited definitions in the
    same order. Returns a flat list of 2 * len( category_specs ) strings. Accessions
    with no known category fall into no column (they remain in Defining_Features /
    Annotation_Definitions).
    """
    cells = []
    for ( category_key, label ) in category_specs:
        category_accessions = [ accession for accession in accessions
                                if accessions___categories.get( accession ) == category_key ]
        category_definitions = [ sanitize_annotation_text( accessions___definitions.get( accession, '' ) )
                                 for accession in category_accessions ]
        cells.append( DELIM.join( category_accessions ) )
        cells.append( DELIM.join( category_definitions ) )
    return cells


def carry_forward_map_columns( map_header_line: str,
                               start_header_id: str = "Annotation_Definitions",
                               end_header_id: str = "Sequence_Count" ) -> tuple:
    """
    The map columns strictly BETWEEN two anchor columns (default: the source-specific
    category-split columns inserted by Script 002 between Annotation_Definitions and
    Sequence_Count). Lets downstream scripts (005, 006) carry these extra columns
    forward generically — no per-source knowledge. Returns
    ( [ header_strings ], [ column_indices ] ); ( [], [] ) when there are none.
    """
    parts_header_line = map_header_line.rstrip( '\n' ).split( '\t' )
    header_ids___indices = build_header_index( map_header_line )
    start_index = header_ids___indices.get( start_header_id )
    end_index = header_ids___indices.get( end_header_id )
    if start_index is None or end_index is None or end_index <= start_index + 1:
        return ( [], [] )
    indices = list( range( start_index + 1, end_index ) )
    return ( [ parts_header_line[ index ] for index in indices ], indices )
