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
# clades (clade_id_names), treated as a single unit for composition analysis. The
# set of composite clades to analyze is defined in START_HERE-user_config.yaml
# under `composite_clades` (see load_composite_clades). The DEFAULT set is the five
# metazoan phylum groups (Ctenophora, Porifera, Placozoa, Cnidaria, Bilateria)
# within the Metazoa scope (members outside the scope -> the "outside" label, e.g.
# NonMetazoan), but ANY grouping of clades can be configured when biologically
# appropriate. This GENERALIZES the earlier "phylum-composition" analysis, which
# hardcoded the five metazoan phyla.
#
# A feature unit's COMPOSITE SIGNATURE is the set of composite clades it occupies
# (>=1 member species in the composite's species set), listed in config order. Its
# COMPOSITE CLASS is the signature plus an outside flag, as a disjoint sibling pair:
#   <G1>_<G2>_Only                  (no members outside the scope clade)
#   <G1>_<G2>_With_<OutsideLabel>   (same composites plus outside-scope members)
# NOTE: this composition is over the trees_species clade groupings, NOT the raw
# NCBI Phylum field used by phylum_from_phyloname() elsewhere in this module.


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

    return { "names": names, "names___species": names___species,
             "scope_species": scope_species, "outside_label": outside_label }


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


def composite_clade_id( ordered_components: list ) -> str:
    """
    Canonical composite-clade identifier for an exact component list:
        cc_<component1>_<component2>_..._-exact   (components already in canonical order)
    e.g. [ 'Porifera', 'Cnidaria', 'NonMetazoa' ] -> 'cc_Porifera_Cnidaria_NonMetazoa-exact'.
    """
    return "cc_" + "_".join( ordered_components ) + "-exact"


def load_composite_clades_manifest( manifest_path: Path, composites: dict ) -> list:
    """
    Read the curated composite-clades manifest (the user's list of composite clades
    to report; one composite clade per row, each a comma-delimited list of component
    names; blank and '#'-comment lines skipped). Each component must be a configured
    group name or the outside label. Components are re-sorted into the canonical
    config order, so the user may list them in any order.

    Returns a list of { 'components': [ordered names], 'frozenset': frozenset,
    'cc_id': str }. Fail-fast on unknown components or an empty manifest.
    """
    valid_components = list( composites[ "names" ] ) + [ composites[ "outside_label" ] ]
    canonical_order = { name: index for index, name in enumerate( valid_components ) }

    manifest = []
    seen = set()
    with open( manifest_path, 'r' ) as input_manifest:
        for line in input_manifest:
            line = line.strip()
            if not line or line.startswith( '#' ):
                continue
            requested = [ token.strip() for token in line.split( ',' ) if token.strip() ]
            unknown = [ token for token in requested if token not in canonical_order ]
            if unknown:
                print( f"CRITICAL ERROR: composite_clades manifest row '{line}' has unknown component(s) {unknown}; "
                       f"valid components are {valid_components}", file = sys.stderr )
                sys.exit( 1 )
            ordered = sorted( set( requested ), key = lambda name: canonical_order[ name ] )
            components_frozenset = frozenset( ordered )
            if components_frozenset in seen:
                continue
            seen.add( components_frozenset )
            manifest.append( { "components": ordered, "frozenset": components_frozenset,
                               "cc_id": composite_clade_id( ordered ) } )

    if not manifest:
        print( f"CRITICAL ERROR: composite_clades manifest has no entries: {manifest_path}", file = sys.stderr )
        sys.exit( 1 )
    return manifest


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
