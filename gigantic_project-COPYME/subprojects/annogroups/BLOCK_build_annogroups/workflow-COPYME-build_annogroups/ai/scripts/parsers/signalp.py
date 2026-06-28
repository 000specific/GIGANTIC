# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 28 | Purpose: annogroups source parser for SignalP 6 (per-species signal-peptide predictions, SLOW model)
# Human: Eric Edsinger

"""
annogroups source parser — signalp.

Reads the per-species SignalP 6 prediction files exposed by annotations_hmms at
  annotations_hmms/output_to_input/BLOCK_signalp/<phyloname>_signalp_SLOW_predictions.tsv
and returns, per sequence, its signal-peptide type.

SignalP runs in two modes (FAST and SLOW); this parser uses the SLOW (full-model)
predictions for accuracy (user decision 2026-06-28). A protein has at most one
signal peptide, and signal-peptide presence is treated as a WHOLE-PROTEIN property
(by type), so signalp is NON-positional and yields THREE annogroup types — feature,
combination, absent — with NO architecture.

The feature is the signal-peptide TYPE from the Signal_Peptide_Call column:
  Sec/SPI  (standard), Sec/SPII (lipoprotein), Tat/SPI (twin-arginine).
'None' (no signal peptide / OTHER) contributes no feature -> the protein falls into
annogroup_signalp_absent. The call is used as the accession with '/' replaced by '_'
(e.g. 'Sec/SPI' -> 'Sec_SPI') for clean identifiers; the original call + meaning is
exposed as the definition.

Caveat (shared with the other per-protein tools): proteins not scored by SignalP
(e.g. dropped upstream by the long-header filter) have no feature here and fall into
annogroup_signalp_absent — 'absent' = 'no signal peptide in the available output'.

Parser-plugin contract (see utils_annogroups): expose SOURCE and
parse_source_features( workflow_root, config ) -> { sequence_id: [ Feature, ... ] }.
"""

import sys
from pathlib import Path

sys.path.insert( 0, str( Path( __file__ ).parent.parent ) )
import utils_annogroups as U

SOURCE = "signalp"
RELATIVE_SUBPATH = "BLOCK_signalp"

# Human-readable meaning per SignalP6 call (used for the accession definition).
CALL_DEFINITIONS = {
    "Sec/SPI": "Sec/SPI standard signal peptide",
    "Sec/SPII": "Sec/SPII lipoprotein signal peptide",
    "Tat/SPI": "Tat/SPI twin-arginine signal peptide",
    "Tat/SPII": "Tat/SPII twin-arginine lipoprotein signal peptide",
}


def _call_accession( call: str ) -> str:
    """Clean accession from a signal-peptide call ('Sec/SPI' -> 'Sec_SPI')."""
    return call.strip().replace( '/', '_' )


def parse_source_features( workflow_root: Path, config: dict ) -> dict:
    """sequence_identifier -> [ Feature(accession=signal_peptide_type, start=None, stop=None, is_positional=False) ]."""
    annotations_dir = U.resolve_input_path(
        workflow_root, config[ "inputs" ][ "annotations_hmms_dir" ]
    ) / RELATIVE_SUBPATH

    if not annotations_dir.is_dir():
        print( f"CRITICAL ERROR: signalp annotation directory not found: {annotations_dir}", file = sys.stderr )
        print( "  Verify annotations_hmms exposed BLOCK_signalp/ in output_to_input.", file = sys.stderr )
        sys.exit( 1 )

    signalp_files = sorted( annotations_dir.glob( "*_signalp_SLOW_predictions.tsv" ) )
    if not signalp_files:
        print( f"CRITICAL ERROR: no *_signalp_SLOW_predictions.tsv files in {annotations_dir}", file = sys.stderr )
        sys.exit( 1 )

    proteins___features = {}
    for signalp_file in signalp_files:
        with open( signalp_file, 'r' ) as input_signalp:
            # Protein_Identifier (...)\tSequence_Length (...)\tSignal_Peptide_Call (...)\t...
            # g_A1BG-...-n_..._Homo_sapiens\t495\tSec/SPI\t1\t21\t...
            header_ids___indices = U.build_header_index( input_signalp.readline() )
            index_protein = header_ids___indices[ "Protein_Identifier" ]
            index_call = header_ids___indices[ "Signal_Peptide_Call" ]
            for line in input_signalp:
                line = line.rstrip( '\n' )
                if not line:
                    continue
                parts = line.split( '\t' )
                call = parts[ index_call ].strip() if index_call < len( parts ) else "None"
                if not call or call == "None":
                    continue
                accession = _call_accession( call )
                proteins___features.setdefault( parts[ index_protein ], [] ).append(
                    U.Feature( accession = accession, start = None, stop = None, is_positional = False )
                )

    return proteins___features


def parse_source_definitions( workflow_root: Path, config: dict ) -> dict:
    """accession -> human-readable signal-peptide type (e.g. 'Sec_SPI' -> 'Sec/SPI standard signal peptide')."""
    accessions___definitions = {}
    for ( call, definition ) in CALL_DEFINITIONS.items():
        accessions___definitions[ _call_accession( call ) ] = definition
    return accessions___definitions
