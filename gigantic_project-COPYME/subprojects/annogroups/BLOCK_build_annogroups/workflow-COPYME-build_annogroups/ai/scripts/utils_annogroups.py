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
