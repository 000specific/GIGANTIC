# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 28 | Purpose: annogroups source parser for FunFam (per-species InterProScan-parsed funfam files)
# Human: Eric Edsinger

"""
annogroups source parser — funfam.

Reads the per-species FunFam annotation files exposed by annotations_hmms at
  annotations_hmms/output_to_input/BLOCK_interproscan_parsed/funfam/funfam-<phyloname>.tsv
and returns, per sequence, the list of FunFam features (all positional).

CATH FunFam functional families (G3DSA ...:FF: accessions). Each match carries residue coordinates (Match_Start / Match_End), so
funfam participates in all four annogroup types (feature, combination,
architecture, absent) -- combination groups by the whole-protein set of FunFam
accessions, architecture by their sub-protein N->C arrangement.

The parsed funfam files share the identical 15-column self-documenting schema as
the pfam files, so this parser mirrors parsers/pfam.py (only SOURCE and the source
subpath differ). Example accession: G3DSA:2.60.40.10:FF:000033.

Parser-plugin contract (see utils_annogroups): expose SOURCE and
parse_source_features( workflow_root, config ) -> { sequence_id: [ Feature, ... ] }.
"""

import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent.parent ) )
import utils_annogroups as U

SOURCE = "funfam"

# Path to this source's annotation files, relative to the workflow root. The config
# exposes the annotations_hmms output_to_input root; each parser appends its own
# source-specific subpath.
RELATIVE_SUBPATH = "BLOCK_interproscan_parsed/funfam"


def parse_source_features( workflow_root: Path, config: dict ) -> dict:
    """sequence_identifier -> [ Feature(accession, start, stop, is_positional=True) ]."""
    annotations_dir = U.resolve_input_path(
        workflow_root, config[ "inputs" ][ "annotations_hmms_dir" ]
    ) / RELATIVE_SUBPATH

    if not annotations_dir.is_dir():
        print( f"CRITICAL ERROR: funfam annotation directory not found: {annotations_dir}", file = sys.stderr )
        print( "  Verify annotations_hmms exposed BLOCK_interproscan_parsed/funfam/ in output_to_input.", file = sys.stderr )
        sys.exit( 1 )

    source_files = sorted( annotations_dir.glob( "funfam-*.tsv" ) )
    if not source_files:
        print( f"CRITICAL ERROR: no funfam-*.tsv files in {annotations_dir}", file = sys.stderr )
        sys.exit( 1 )

    proteins___features = {}
    for source_file in source_files:
        with open( source_file, 'r' ) as input_source:
            # Protein_Identifier (...)\tMD5 (...)\tSequence_Length (...)\tAnalysis_Database (...)\tAccession (...)\tDescription (...)\tMatch_Start (...)\tMatch_End (...)\t...
            header_ids___indices = U.build_header_index( input_source.readline() )
            index_protein = header_ids___indices[ "Protein_Identifier" ]
            index_accession = header_ids___indices[ "Accession" ]
            index_start = header_ids___indices[ "Match_Start" ]
            index_stop = header_ids___indices[ "Match_End" ]
            for line in input_source:
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
                    # A positional match must have integer coordinates; a malformed
                    # row is a genuine upstream data problem -- fail fast (section 36).
                    print( f"CRITICAL ERROR: non-integer Match_Start/Match_End in {source_file.name}: {line[ :120 ]}", file = sys.stderr )
                    sys.exit( 1 )
                proteins___features.setdefault( protein, [] ).append(
                    U.Feature( accession = accession, start = start, stop = stop, is_positional = True )
                )

    return proteins___features


def parse_source_definitions( workflow_root: Path, config: dict ) -> dict:
    """
    accession -> human-readable definition (FunFam signature description, column
    'Description'). First non-empty description seen per accession wins.

    Optional half of the parser contract: a source that exposes this lets the builder
    attach Annotation_Definitions to the annogroup map. Sources without descriptions
    can omit this function (the builder then emits empty definitions).
    """
    annotations_dir = U.resolve_input_path(
        workflow_root, config[ "inputs" ][ "annotations_hmms_dir" ]
    ) / RELATIVE_SUBPATH

    source_files = sorted( annotations_dir.glob( "funfam-*.tsv" ) )

    accessions___definitions = {}
    for source_file in source_files:
        with open( source_file, 'r' ) as input_source:
            header_ids___indices = U.build_header_index( input_source.readline() )
            index_accession = header_ids___indices[ "Accession" ]
            index_description = header_ids___indices[ "Description" ]
            for line in input_source:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                accession = parts[ index_accession ]
                description = U.sanitize_annotation_text( parts[ index_description ] ) if index_description < len( parts ) else ''
                if description and description != '-' and accession not in accessions___definitions:
                    accessions___definitions[ accession ] = description

    return accessions___definitions
