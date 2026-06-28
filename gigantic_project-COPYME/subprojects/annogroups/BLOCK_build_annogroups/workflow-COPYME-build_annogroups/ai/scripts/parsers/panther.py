# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 28 | Purpose: annogroups source parser for PANTHER (per-species InterProScan-parsed panther files)
# Human: Eric Edsinger

"""
annogroups source parser — panther.

Reads the per-species PANTHER annotation files exposed by annotations_hmms at
  annotations_hmms/output_to_input/BLOCK_interproscan_parsed/panther/panther-<phyloname>.tsv
and returns, per sequence, the list of PANTHER family features (all positional).

PANTHER assigns each match a protein-family accession (PTHR#####) with residue
coordinates (Match_Start / Match_End). The parsed files carry FAMILY-level
accessions only (no PTHRxxxxx:SFnn subfamily suffix). Because the matches are
positional, PANTHER participates in all four annogroup types (feature,
combination, architecture, absent) — combination groups by the whole-protein set
of families, architecture by their sub-protein N->C arrangement.

The parsed panther files share the identical 15-column self-documenting schema as
the pfam files, so this parser mirrors parsers/pfam.py (only SOURCE and the
source subpath differ).

Parser-plugin contract (see utils_annogroups): expose SOURCE and
parse_source_features( workflow_root, config ) -> { sequence_id: [ Feature, ... ] }.
"""

import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent.parent ) )
import utils_annogroups as U

SOURCE = "panther"

# Path to this source's annotation files, relative to the workflow root. The
# config exposes the annotations_hmms output_to_input root; each parser appends
# its own source-specific subpath.
RELATIVE_SUBPATH = "BLOCK_interproscan_parsed/panther"


def parse_source_features( workflow_root: Path, config: dict ) -> dict:
    """sequence_identifier -> [ Feature(accession, start, stop, is_positional=True) ]."""
    annotations_dir = U.resolve_input_path(
        workflow_root, config[ "inputs" ][ "annotations_hmms_dir" ]
    ) / RELATIVE_SUBPATH

    if not annotations_dir.is_dir():
        print( f"CRITICAL ERROR: panther annotation directory not found: {annotations_dir}", file = sys.stderr )
        print( "  Verify annotations_hmms exposed BLOCK_interproscan_parsed/panther/ in output_to_input.", file = sys.stderr )
        sys.exit( 1 )

    panther_files = sorted( annotations_dir.glob( "panther-*.tsv" ) )
    if not panther_files:
        print( f"CRITICAL ERROR: no panther-*.tsv files in {annotations_dir}", file = sys.stderr )
        sys.exit( 1 )

    proteins___features = {}
    for panther_file in panther_files:
        with open( panther_file, 'r' ) as input_panther:
            # Protein_Identifier (...)\tMD5 (...)\tSequence_Length (...)\tAnalysis_Database (...)\tAccession (...)\tDescription (...)\tMatch_Start (...)\tMatch_End (...)\t...
            # g_A1BG-...-n_..._Homo_sapiens\t40b7...\t495\tPANTHER\tPTHR11738\tMHC CLASS I NK CELL RECEPTOR\t401\t493\t...
            header_ids___indices = U.build_header_index( input_panther.readline() )
            index_protein = header_ids___indices[ "Protein_Identifier" ]
            index_accession = header_ids___indices[ "Accession" ]
            index_start = header_ids___indices[ "Match_Start" ]
            index_stop = header_ids___indices[ "Match_End" ]
            for line in input_panther:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                protein = parts[ index_protein ]
                accession = parts[ index_accession ]
                try:
                    start = int( parts[ index_start ] )
                    stop = int( parts[ index_stop ] )
                except ( ValueError, IndexError ):
                    # A PANTHER match must have integer coordinates; a malformed row
                    # is a genuine upstream data problem — fail fast (§36).
                    print( f"CRITICAL ERROR: non-integer Match_Start/Match_End in {panther_file.name}: {line[ :120 ]}", file = sys.stderr )
                    sys.exit( 1 )
                proteins___features.setdefault( protein, [] ).append(
                    U.Feature( accession = accession, start = start, stop = stop, is_positional = True )
                )

    return proteins___features


def parse_source_definitions( workflow_root: Path, config: dict ) -> dict:
    """
    accession -> human-readable definition (PANTHER family description, column
    'Description'). First non-empty description seen per accession wins.

    Optional half of the parser contract: a source that exposes this lets the
    builder attach Annotation_Definitions to the annogroup map. Sources without
    descriptions can omit this function (the builder then emits empty definitions).
    """
    annotations_dir = U.resolve_input_path(
        workflow_root, config[ "inputs" ][ "annotations_hmms_dir" ]
    ) / RELATIVE_SUBPATH

    panther_files = sorted( annotations_dir.glob( "panther-*.tsv" ) )

    accessions___definitions = {}
    for panther_file in panther_files:
        with open( panther_file, 'r' ) as input_panther:
            # Protein_Identifier (...)\t...\tAccession (...)\tDescription (...)\t...
            header_ids___indices = U.build_header_index( input_panther.readline() )
            index_accession = header_ids___indices[ "Accession" ]
            index_description = header_ids___indices[ "Description" ]
            for line in input_panther:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                accession = parts[ index_accession ]
                description = U.sanitize_annotation_text( parts[ index_description ] ) if index_description < len( parts ) else ''
                if description and description != '-' and accession not in accessions___definitions:
                    accessions___definitions[ accession ] = description

    return accessions___definitions
