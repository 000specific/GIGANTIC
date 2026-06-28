# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 28 | Purpose: annogroups source parser for DeepLoc (per-species subcellular-localization predictions)
# Human: Eric Edsinger

"""
annogroups source parser — deeploc.

Reads the per-species DeepLoc 2 prediction files exposed by annotations_hmms at
  annotations_hmms/output_to_input/BLOCK_deeploc/<phyloname>_deeploc_predictions.csv
and returns, per sequence, its subcellular-localization labels.

DeepLoc predicts WHOLE-PROTEIN subcellular localization (no residue coordinates),
so deeploc is NON-positional and yields THREE annogroup types — feature,
combination, absent — with NO architecture (combination = the whole-protein set of
localizations a protein is assigned). A protein can have multiple localizations
(the 'Localizations' column is pipe-delimited, e.g. 'Cytoplasm|Nucleus'); each
becomes one feature.

The localization label is used as the accession with spaces and '/' replaced by '_'
(e.g. 'Cell membrane' -> 'Cell_membrane', 'Lysosome/Vacuole' -> 'Lysosome_Vacuole')
so annogroup identifiers are clean; the original human-readable label is exposed as
the accession's definition.

NOTE: this is the FINAL-CALL 'Localizations' column (DeepLoc's thresholded
prediction), not the raw per-class probabilities.

Caveat (shared with the other per-protein tools): proteins that were not scored by
DeepLoc (e.g. dropped upstream by the long-header filter) simply have no feature
here and therefore fall into annogroup_deeploc_absent — i.e. 'absent' means 'no
DeepLoc localization in the available output', which can include a small number of
not-evaluated proteins.

Parser-plugin contract (see utils_annogroups): expose SOURCE and
parse_source_features( workflow_root, config ) -> { sequence_id: [ Feature, ... ] }.
"""

import csv
import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent.parent ) )
import utils_annogroups as U

SOURCE = "deeploc"
RELATIVE_SUBPATH = "BLOCK_deeploc"


def _localization_accession( label: str ) -> str:
    """Clean accession from a localization label (spaces and '/' -> '_')."""
    return label.strip().replace( ' ', '_' ).replace( '/', '_' )


def parse_source_features( workflow_root: Path, config: dict ) -> dict:
    """sequence_identifier -> [ Feature(accession=localization, start=None, stop=None, is_positional=False) ]."""
    annotations_dir = U.resolve_input_path(
        workflow_root, config[ "inputs" ][ "annotations_hmms_dir" ]
    ) / RELATIVE_SUBPATH

    if not annotations_dir.is_dir():
        print( f"CRITICAL ERROR: deeploc annotation directory not found: {annotations_dir}", file = sys.stderr )
        print( "  Verify annotations_hmms exposed BLOCK_deeploc/ in output_to_input.", file = sys.stderr )
        sys.exit( 1 )

    deeploc_files = sorted( annotations_dir.glob( "*_deeploc_predictions.csv" ) )
    if not deeploc_files:
        print( f"CRITICAL ERROR: no *_deeploc_predictions.csv files in {annotations_dir}", file = sys.stderr )
        sys.exit( 1 )

    proteins___features = {}
    for deeploc_file in deeploc_files:
        with open( deeploc_file, newline = '' ) as input_deeploc:
            # Protein_ID,Localizations,Signals,Membrane types,Cytoplasm,Nucleus,...
            # g_A1BG-...-n_..._Homo_sapiens,Extracellular,Signal peptide,Soluble,0.28,...
            reader = csv.reader( input_deeploc )
            header = next( reader, None )
            if header is None:
                continue
            try:
                index_protein = header.index( "Protein_ID" )
                index_localizations = header.index( "Localizations" )
            except ValueError:
                print( f"CRITICAL ERROR: deeploc file missing Protein_ID/Localizations columns: {deeploc_file.name}", file = sys.stderr )
                sys.exit( 1 )
            for parts in reader:
                if not parts or len( parts ) <= index_localizations:
                    continue
                protein = parts[ index_protein ]
                localizations_cell = parts[ index_localizations ].strip()
                if not localizations_cell:
                    continue
                for label in localizations_cell.split( '|' ):
                    label = label.strip()
                    if not label:
                        continue
                    accession = _localization_accession( label )
                    proteins___features.setdefault( protein, [] ).append(
                        U.Feature( accession = accession, start = None, stop = None, is_positional = False )
                    )

    return proteins___features


def parse_source_definitions( workflow_root: Path, config: dict ) -> dict:
    """accession -> human-readable localization label (e.g. 'Cell_membrane' -> 'Cell membrane')."""
    annotations_dir = U.resolve_input_path(
        workflow_root, config[ "inputs" ][ "annotations_hmms_dir" ]
    ) / RELATIVE_SUBPATH

    deeploc_files = sorted( annotations_dir.glob( "*_deeploc_predictions.csv" ) )

    accessions___definitions = {}
    for deeploc_file in deeploc_files:
        with open( deeploc_file, newline = '' ) as input_deeploc:
            reader = csv.reader( input_deeploc )
            header = next( reader, None )
            if header is None:
                continue
            index_localizations = header.index( "Localizations" )
            for parts in reader:
                if not parts or len( parts ) <= index_localizations:
                    continue
                for label in parts[ index_localizations ].split( '|' ):
                    label = label.strip()
                    if not label:
                        continue
                    accession = _localization_accession( label )
                    if accession not in accessions___definitions:
                        accessions___definitions[ accession ] = label

    return accessions___definitions
