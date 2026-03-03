#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Run MetaPredict disorder prediction on a single species proteome
# Human: Eric Edsinger

# =============================================================================
# 002_ai-bash-run_metapredict.sh
# =============================================================================
#
# Runs MetaPredict disorder prediction on a single species proteome FASTA file.
# Produces per-residue disorder scores and intrinsically disordered region (IDR)
# boundary predictions.
#
# Input:
#   --input-fasta: Path to a single species proteome FASTA file (.aa)
#   --output-dir: Directory for output files
#   --phyloname: GIGANTIC phyloname for the species (used in output naming)
#   --prediction-types: Comma-separated list of predictions (disorder,idrs,plddt)
#
# Output:
#   {phyloname}_metapredict_disorder.tsv - Per-residue disorder scores
#   {phyloname}_metapredict_idrs.tsv - Intrinsically disordered region boundaries
#   2_ai-log-run_metapredict_{phyloname}.log - Execution log
#
# Prerequisites:
#   - MetaPredict Python library installed (pip install metapredict)
#   - conda environment with metapredict activated
#
# Usage:
#   bash 002_ai-bash-run_metapredict.sh \
#       --input-fasta /path/to/species.aa \
#       --output-dir . \
#       --phyloname Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens \
#       --prediction-types disorder,idrs
#
# =============================================================================

set -e  # Exit on error

# =============================================================================
# CONFIGURATION
# =============================================================================

# Default values
INPUT_FASTA=""
OUTPUT_DIR="."
PHYLONAME=""
PREDICTION_TYPES="disorder,idrs"

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --input-fasta)
            INPUT_FASTA="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --phyloname)
            PHYLONAME="$2"
            shift 2
            ;;
        --prediction-types)
            PREDICTION_TYPES="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# LOGGING SETUP
# =============================================================================

LOG_DIR="${OUTPUT_DIR}"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/2_ai-log-run_metapredict_${PHYLONAME}.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

# =============================================================================
# VALIDATE INPUTS
# =============================================================================

log_message "========================================================================"
log_message "Script 002: Run MetaPredict Disorder Prediction"
log_message "========================================================================"

# Validate required arguments
if [ -z "${INPUT_FASTA}" ]; then
    log_message "CRITICAL ERROR: --input-fasta is required but not provided!"
    exit 1
fi

if [ -z "${PHYLONAME}" ]; then
    log_message "CRITICAL ERROR: --phyloname is required but not provided!"
    exit 1
fi

# Validate input file exists
if [ ! -f "${INPUT_FASTA}" ]; then
    log_message "CRITICAL ERROR: Input FASTA file does not exist!"
    log_message "Expected path: ${INPUT_FASTA}"
    log_message "Ensure the proteome file is accessible from the execution directory."
    exit 1
fi

# Validate input file is not empty
if [ ! -s "${INPUT_FASTA}" ]; then
    log_message "CRITICAL ERROR: Input FASTA file is empty!"
    log_message "Path: ${INPUT_FASTA}"
    exit 1
fi

# Check if metapredict is available
if ! python3 -c "import metapredict" 2>/dev/null; then
    log_message "CRITICAL ERROR: metapredict Python library not found!"
    log_message "Install with: pip install metapredict"
    log_message "Or ensure the correct conda environment is activated."
    exit 1
fi

log_message "Input FASTA: ${INPUT_FASTA}"
log_message "Output directory: ${OUTPUT_DIR}"
log_message "Phyloname: ${PHYLONAME}"
log_message "Prediction types: ${PREDICTION_TYPES}"

# Count input sequences
SEQUENCE_COUNT=$(grep -c '^>' "${INPUT_FASTA}")
log_message "Input sequences: ${SEQUENCE_COUNT}"

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# =============================================================================
# OUTPUT FILE PATHS
# =============================================================================

OUTPUT_DISORDER="${OUTPUT_DIR}/${PHYLONAME}_metapredict_disorder.tsv"
OUTPUT_IDRS="${OUTPUT_DIR}/${PHYLONAME}_metapredict_idrs.tsv"

# =============================================================================
# RUN METAPREDICT - DISORDER SCORES
# =============================================================================

if echo "${PREDICTION_TYPES}" | grep -q "disorder"; then
    log_message ""
    log_message "Running MetaPredict disorder prediction..."
    log_message "This predicts per-residue disorder scores for each protein."
    log_message ""

    python3 << PYTHON_DISORDER_SCRIPT
import sys
from pathlib import Path

try:
    import metapredict as meta
except ImportError:
    print( "CRITICAL ERROR: Could not import metapredict", file = sys.stderr )
    sys.exit( 1 )

input_fasta_path = Path( "${INPUT_FASTA}" )
output_disorder_path = Path( "${OUTPUT_DISORDER}" )

# Read FASTA file and extract sequences
identifiers___sequences = {}
current_identifier = None
current_sequence_lines = []

with open( input_fasta_path, 'r' ) as input_fasta:
    for line in input_fasta:
        line = line.strip()
        if line.startswith( '>' ):
            if current_identifier is not None:
                identifiers___sequences[ current_identifier ] = ''.join( current_sequence_lines )
            current_identifier = line[ 1: ].split()[ 0 ]
            current_sequence_lines = []
        else:
            current_sequence_lines.append( line )

    # Add the last sequence
    if current_identifier is not None:
        identifiers___sequences[ current_identifier ] = ''.join( current_sequence_lines )

print( f"Read {len( identifiers___sequences )} sequences from FASTA" )

# Run disorder prediction and write output
sequence_count = 0
error_count = 0

with open( output_disorder_path, 'w' ) as output_disorder:
    # Write header
    header = 'Protein_Identifier (protein sequence identifier from FASTA header)' + '\t'
    header += 'Disorder_Scores (comma delimited per residue disorder scores from MetaPredict ranging 0 to 1)' + '\t'
    header += 'Mean_Disorder_Score (mean of all per residue disorder scores for the protein)' + '\t'
    header += 'Sequence_Length (number of amino acid residues in the protein)' + '\n'
    output_disorder.write( header )

    for identifier in identifiers___sequences:
        sequence = identifiers___sequences[ identifier ]
        sequence_count += 1

        try:
            disorder_scores = meta.predict_disorder( sequence )
            disorder_scores_list = [ round( score, 4 ) for score in disorder_scores ]
            disorder_scores_string = ','.join( str( score ) for score in disorder_scores_list )

            mean_disorder_score = round( sum( disorder_scores_list ) / len( disorder_scores_list ), 4 ) if len( disorder_scores_list ) > 0 else 0.0
            sequence_length = len( sequence )

            output = identifier + '\t'
            output += disorder_scores_string + '\t'
            output += str( mean_disorder_score ) + '\t'
            output += str( sequence_length ) + '\n'
            output_disorder.write( output )

        except Exception as prediction_error:
            error_count += 1
            print( f"WARNING: Failed to predict disorder for {identifier}: {prediction_error}", file = sys.stderr )

            # Write row with empty scores so we do not lose track of the protein
            output = identifier + '\t'
            output += 'PREDICTION_FAILED' + '\t'
            output += 'NA' + '\t'
            output += str( len( sequence ) ) + '\n'
            output_disorder.write( output )

print( f"Disorder prediction complete: {sequence_count} sequences processed, {error_count} errors" )

if error_count > 0 and error_count == sequence_count:
    print( "CRITICAL ERROR: All disorder predictions failed!", file = sys.stderr )
    sys.exit( 1 )
PYTHON_DISORDER_SCRIPT

    log_message "Disorder prediction complete: ${OUTPUT_DISORDER}"
else
    log_message "Skipping disorder prediction (not in prediction_types)"
    # Create the file with header only so pipeline does not fail on missing output
    printf 'Protein_Identifier (protein sequence identifier from FASTA header)\tDisorder_Scores (comma delimited per residue disorder scores from MetaPredict ranging 0 to 1)\tMean_Disorder_Score (mean of all per residue disorder scores for the protein)\tSequence_Length (number of amino acid residues in the protein)\n' > "${OUTPUT_DISORDER}"
    log_message "Created header-only disorder file: ${OUTPUT_DISORDER}"
fi

# =============================================================================
# RUN METAPREDICT - INTRINSICALLY DISORDERED REGIONS
# =============================================================================

if echo "${PREDICTION_TYPES}" | grep -q "idrs"; then
    log_message ""
    log_message "Running MetaPredict IDR prediction..."
    log_message "This identifies intrinsically disordered region boundaries."
    log_message ""

    python3 << PYTHON_IDR_SCRIPT
import sys
from pathlib import Path

try:
    import metapredict as meta
except ImportError:
    print( "CRITICAL ERROR: Could not import metapredict", file = sys.stderr )
    sys.exit( 1 )

input_fasta_path = Path( "${INPUT_FASTA}" )
output_idrs_path = Path( "${OUTPUT_IDRS}" )

# Read FASTA file and extract sequences
identifiers___sequences = {}
current_identifier = None
current_sequence_lines = []

with open( input_fasta_path, 'r' ) as input_fasta:
    for line in input_fasta:
        line = line.strip()
        if line.startswith( '>' ):
            if current_identifier is not None:
                identifiers___sequences[ current_identifier ] = ''.join( current_sequence_lines )
            current_identifier = line[ 1: ].split()[ 0 ]
            current_sequence_lines = []
        else:
            current_sequence_lines.append( line )

    # Add the last sequence
    if current_identifier is not None:
        identifiers___sequences[ current_identifier ] = ''.join( current_sequence_lines )

print( f"Read {len( identifiers___sequences )} sequences from FASTA" )

# Run IDR prediction and write output
sequence_count = 0
total_idr_count = 0
error_count = 0

with open( output_idrs_path, 'w' ) as output_idrs:
    # Write header
    header = 'Protein_Identifier (protein sequence identifier from FASTA header)' + '\t'
    header += 'IDR_Boundaries (comma delimited intrinsically disordered region boundaries as start-end pairs)' + '\t'
    header += 'IDR_Count (number of intrinsically disordered regions identified in the protein)' + '\t'
    header += 'Sequence_Length (number of amino acid residues in the protein)' + '\n'
    output_idrs.write( header )

    for identifier in identifiers___sequences:
        sequence = identifiers___sequences[ identifier ]
        sequence_count += 1

        try:
            idr_boundaries = meta.predict_disorder_domains( sequence )

            # Extract disordered regions (list of [start, end] boundaries)
            disordered_regions = idr_boundaries.disordered_domain_boundaries
            idr_count = len( disordered_regions )
            total_idr_count += idr_count

            # Format boundaries as comma-delimited start-end pairs
            if idr_count > 0:
                boundaries_strings = []
                for region in disordered_regions:
                    boundary_string = str( region[ 0 ] ) + '-' + str( region[ 1 ] )
                    boundaries_strings.append( boundary_string )
                idr_boundaries_string = ','.join( boundaries_strings )
            else:
                idr_boundaries_string = 'NONE'

            sequence_length = len( sequence )

            output = identifier + '\t'
            output += idr_boundaries_string + '\t'
            output += str( idr_count ) + '\t'
            output += str( sequence_length ) + '\n'
            output_idrs.write( output )

        except Exception as prediction_error:
            error_count += 1
            print( f"WARNING: Failed to predict IDRs for {identifier}: {prediction_error}", file = sys.stderr )

            output = identifier + '\t'
            output += 'PREDICTION_FAILED' + '\t'
            output += 'NA' + '\t'
            output += str( len( sequence ) ) + '\n'
            output_idrs.write( output )

print( f"IDR prediction complete: {sequence_count} sequences processed, {total_idr_count} IDRs found, {error_count} errors" )

if error_count > 0 and error_count == sequence_count:
    print( "CRITICAL ERROR: All IDR predictions failed!", file = sys.stderr )
    sys.exit( 1 )
PYTHON_IDR_SCRIPT

    log_message "IDR prediction complete: ${OUTPUT_IDRS}"
else
    log_message "Skipping IDR prediction (not in prediction_types)"
    # Create the file with header only so pipeline does not fail on missing output
    printf 'Protein_Identifier (protein sequence identifier from FASTA header)\tIDR_Boundaries (comma delimited intrinsically disordered region boundaries as start-end pairs)\tIDR_Count (number of intrinsically disordered regions identified in the protein)\tSequence_Length (number of amino acid residues in the protein)\n' > "${OUTPUT_IDRS}"
    log_message "Created header-only IDR file: ${OUTPUT_IDRS}"
fi

# =============================================================================
# VALIDATE OUTPUTS
# =============================================================================

log_message ""
log_message "Validating outputs..."

# Check disorder output
if [ ! -f "${OUTPUT_DISORDER}" ]; then
    log_message "CRITICAL ERROR: Disorder output file was not created!"
    log_message "Expected: ${OUTPUT_DISORDER}"
    exit 1
fi

DISORDER_LINE_COUNT=$(wc -l < "${OUTPUT_DISORDER}")
log_message "Disorder output: ${DISORDER_LINE_COUNT} lines (including header)"

if [ "${DISORDER_LINE_COUNT}" -le 1 ] && echo "${PREDICTION_TYPES}" | grep -q "disorder"; then
    log_message "CRITICAL ERROR: Disorder output file contains only a header (no data rows)!"
    log_message "MetaPredict disorder prediction produced no results."
    exit 1
fi

# Check IDR output
if [ ! -f "${OUTPUT_IDRS}" ]; then
    log_message "CRITICAL ERROR: IDR output file was not created!"
    log_message "Expected: ${OUTPUT_IDRS}"
    exit 1
fi

IDR_LINE_COUNT=$(wc -l < "${OUTPUT_IDRS}")
log_message "IDR output: ${IDR_LINE_COUNT} lines (including header)"

if [ "${IDR_LINE_COUNT}" -le 1 ] && echo "${PREDICTION_TYPES}" | grep -q "idrs"; then
    log_message "CRITICAL ERROR: IDR output file contains only a header (no data rows)!"
    log_message "MetaPredict IDR prediction produced no results."
    exit 1
fi

# =============================================================================
# COMPLETION
# =============================================================================

log_message ""
log_message "========================================================================"
log_message "Script 002 completed successfully for: ${PHYLONAME}"
log_message "========================================================================"
log_message "Disorder output: ${OUTPUT_DISORDER}"
log_message "IDR output: ${OUTPUT_IDRS}"
log_message "Log file: ${LOG_FILE}"
