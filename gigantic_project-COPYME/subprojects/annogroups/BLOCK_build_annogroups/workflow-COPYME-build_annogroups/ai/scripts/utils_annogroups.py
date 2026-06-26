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

from collections import namedtuple
from pathlib import Path
import yaml

# In-column multi-value delimiter — bare comma per gigantic_conventions §34.
DELIM = ','


# ============================================================================
# Metazoan phylum composition (annogroup phylum-composition classes, 2026-06-23)
# ============================================================================
# NOTE: this is the trees_species METAZOAN-GROUP partition (Ctenophora, Porifera,
# Placozoa, Cnidaria, Bilateria — the five groups that partition Metazoa), NOT the
# raw NCBI Phylum field used by phylum_from_phyloname() elsewhere in this module.
# Same approved vocabulary as the integrator + OCL blocks. Each named signature
# splits into a disjoint PAIR by non-metazoan presence: the bare `_Only` name (no
# non-metazoan members) and `<name>_With_NonMetazoan` (same metazoan phyla plus
# non-metazoan outgroups). Siblings, NOT nested.
METAZOAN_PHYLA = [ "Ctenophora", "Porifera", "Placozoa", "Cnidaria", "Bilateria" ]
NON_BILATERIAN_PHYLA = frozenset( { "Ctenophora", "Porifera", "Placozoa", "Cnidaria" } )

PHYLUM_SIGNATURE___CLASS_KEY = {
    frozenset( { "Ctenophora" } ):                                      "Ctenophora_Only",
    frozenset( { "Porifera" } ):                                        "Porifera_Only",
    frozenset( { "Placozoa" } ):                                        "Placozoa_Only",
    frozenset( { "Cnidaria" } ):                                        "Cnidaria_Only",
    frozenset( { "Ctenophora", "Porifera" } ):                         "Mixed_Ctenophora_Porifera_Only",
    frozenset( { "Ctenophora", "Placozoa" } ):                         "Mixed_Ctenophora_Placozoa_Only",
    frozenset( { "Ctenophora", "Cnidaria" } ):                         "Mixed_Ctenophora_Cnidaria_Only",
    frozenset( { "Ctenophora", "Bilateria" } ):                        "Mixed_Ctenophora_Bilateria_Only",
    frozenset( { "Ctenophora", "Porifera", "Placozoa" } ):             "Mixed_Ctenophora_Porifera_Placozoa_Only",
    frozenset( { "Ctenophora", "Porifera", "Placozoa", "Cnidaria" } ): "Mixed_Ctenophora_Porifera_Placozoa_Cnidaria_Only",
    frozenset( { "Porifera", "Placozoa" } ):                           "Mixed_Porifera_Placozoa_Only",
    frozenset( { "Porifera", "Placozoa", "Cnidaria" } ):               "Mixed_Porifera_Placozoa_Cnidaria_Only",
    frozenset( { "Placozoa", "Cnidaria" } ):                           "Mixed_Placozoa_Cnidaria_Only",
    frozenset( { "Placozoa", "Bilateria" } ):                          "Mixed_Placozoa_Bilateria_Only",
    frozenset( { "Cnidaria", "Bilateria" } ):                          "Mixed_Cnidaria_Bilateria_Only",
}

PHYLUM_COMPOSITION_CLASS_KEYS = []
for _base_key in PHYLUM_SIGNATURE___CLASS_KEY.values():
    PHYLUM_COMPOSITION_CLASS_KEYS.append( _base_key )
    PHYLUM_COMPOSITION_CLASS_KEYS.append( _base_key + "_With_NonMetazoan" )


def parse_signature_cell( signature_cell: str ) -> frozenset:
    """Metazoan_Phylum_Signature cell (comma-delimited, may be empty) -> frozenset."""
    return frozenset( token for token in signature_cell.split( DELIM ) if token )


def phylum_signature_of_species( member_species: set, phyla___species: dict, metazoan_species: set ):
    """
    One annogroup's metazoan phylum signature from its member species.
    Returns ( signature_cell, has_nonmetazoan ): metazoan phyla present comma-joined
    in fixed METAZOAN_PHYLA order, and whether any member is not in Metazoa.
    """
    present = [ phylum for phylum in METAZOAN_PHYLA if member_species & phyla___species[ phylum ] ]
    has_nonmetazoan = bool( member_species - metazoan_species )
    return ( DELIM.join( present ), has_nonmetazoan )


def named_phylum_class( signature: frozenset, has_nonmetazoan: bool ):
    """
    Named phylum-composition class from the EXACT metazoan signature + whether any
    member is non-metazoan. Returns a class key (or 'unclassified' when the
    signature is not one of the named signatures). The `_Only` and
    `<key>_With_NonMetazoan` variants are DISJOINT siblings, not nested.
    """
    base_key = PHYLUM_SIGNATURE___CLASS_KEY.get( signature )
    if base_key is None:
        return "unclassified"
    return base_key + "_With_NonMetazoan" if has_nonmetazoan else base_key


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
