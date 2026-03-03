#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Run DeepLoc 2.1 subcellular localization prediction on a single species proteome
# Human: Eric Edsinger

# =============================================================================
# 002_ai-bash-run_deeploc.sh
# =============================================================================
#
# Runs DeepLoc 2.1 subcellular localization prediction on a single species
# proteome FASTA file. DeepLoc uses deep learning to predict protein
# localization to subcellular compartments (nucleus, cytoplasm, extracellular,
# membrane, mitochondrion, etc.) and whether proteins are membrane-bound or
# soluble.
#
# Input:
#   --input-fasta: Path to a single species proteome FASTA file (.aa)
#   --output-dir: Directory for output files
#   --phyloname: GIGANTIC phyloname for the species (used in output naming)
#   --model-type: DeepLoc model type ("Accurate" or "Fast")
#
# Output:
#   {phyloname}_deeploc_predictions.csv - DeepLoc localization predictions
#       CSV with columns: protein ID, localization prediction, and probability
#       scores for each subcellular compartment (Membrane, Nucleus, Cytoplasm,
#       Extracellular, Mitochondrion, Cell_membrane, Endoplasmic_reticulum,
#       Plastid, Golgi_apparatus, Lysosome/Vacuole, Peroxisome)
#
#   2_ai-log-run_deeploc_{phyloname}.log - Execution log
#
# Prerequisites:
#   - DeepLoc 2.1 installed and available as deeploc2
#   - conda environment ai_gigantic_deeploc activated
#   - GPU recommended for reasonable runtime (CPU mode is very slow)
#
# Usage:
#   bash 002_ai-bash-run_deeploc.sh \
#       --input-fasta /path/to/species.aa \
#       --output-dir . \
#       --phyloname Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens \
#       --model-type Accurate
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
MODEL_TYPE="Accurate"

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
        --model-type)
            MODEL_TYPE="$2"
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
LOG_FILE="${LOG_DIR}/2_ai-log-run_deeploc_${PHYLONAME}.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

# =============================================================================
# VALIDATE INPUTS
# =============================================================================

log_message "========================================================================"
log_message "Script 002: Run DeepLoc Subcellular Localization Prediction"
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

# Check if deeploc2 is available
if ! command -v deeploc2 &> /dev/null; then
    log_message "CRITICAL ERROR: deeploc2 command not found!"
    log_message "Ensure DeepLoc 2.1 is installed and the ai_gigantic_deeploc conda environment is activated."
    log_message "DeepLoc 2.1 requires manual download from DTU Health Tech:"
    log_message "  https://services.healthtech.dtu.dk/services/DeepLoc-2.1/"
    exit 1
fi

# Validate model type
case "${MODEL_TYPE}" in
    Accurate|Fast)
        ;;
    *)
        log_message "CRITICAL ERROR: Invalid model type '${MODEL_TYPE}'!"
        log_message "Valid options: Accurate (higher quality, slower), Fast (lower quality, faster)"
        log_message "For publication-quality results, use 'Accurate'."
        exit 1
        ;;
esac

log_message "Input FASTA: ${INPUT_FASTA}"
log_message "Output directory: ${OUTPUT_DIR}"
log_message "Phyloname: ${PHYLONAME}"
log_message "Model type: ${MODEL_TYPE}"

# Count input sequences
SEQUENCE_COUNT=$(grep -c '^>' "${INPUT_FASTA}")
log_message "Input sequences: ${SEQUENCE_COUNT}"

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# =============================================================================
# OUTPUT FILE PATHS
# =============================================================================

DEEPLOC_RAW_DIR="${OUTPUT_DIR}/deeploc_raw_output_${PHYLONAME}"
OUTPUT_PREDICTIONS="${OUTPUT_DIR}/${PHYLONAME}_deeploc_predictions.csv"

# =============================================================================
# RUN DEEPLOC 2.1
# =============================================================================

log_message ""
log_message "Running DeepLoc 2.1 subcellular localization prediction..."
log_message "This predicts subcellular localization for each protein."
log_message "Model: ${MODEL_TYPE}"
log_message ""

mkdir -p "${DEEPLOC_RAW_DIR}"

deeploc2 \
    -f "${INPUT_FASTA}" \
    -o "${DEEPLOC_RAW_DIR}" \
    --model "${MODEL_TYPE}" \
    2>&1 | tee -a "${LOG_FILE}"

DEEPLOC_EXIT_CODE=${PIPESTATUS[0]}

if [ ${DEEPLOC_EXIT_CODE} -ne 0 ]; then
    log_message "CRITICAL ERROR: DeepLoc 2.1 failed with exit code ${DEEPLOC_EXIT_CODE}!"
    log_message "Check the log above for specific error messages."
    log_message "Common issues:"
    log_message "  - CUDA/GPU not available (DeepLoc is very slow on CPU)"
    log_message "  - Model weights not downloaded (first run downloads automatically)"
    log_message "  - Python version mismatch (DeepLoc requires Python 3.10)"
    log_message "  - Insufficient GPU memory"
    log_message "  - Invalid FASTA format"
    exit 1
fi

log_message "DeepLoc 2.1 raw output written to: ${DEEPLOC_RAW_DIR}"

# =============================================================================
# LOCATE DEEPLOC OUTPUT FILE
# =============================================================================
# DeepLoc 2.1 writes a CSV results file in the output directory.
# Common output filenames: results.csv, output.csv, or similar.
# We need to find and copy it to the standardized output name.
# =============================================================================

DEEPLOC_RESULTS_FILE=""

# Check common DeepLoc 2.1 output filenames
for candidate_filename in "results.csv" "output.csv" "predictions.csv" "deeploc_results.csv"; do
    if [ -f "${DEEPLOC_RAW_DIR}/${candidate_filename}" ]; then
        DEEPLOC_RESULTS_FILE="${DEEPLOC_RAW_DIR}/${candidate_filename}"
        break
    fi
done

# If no standard filename found, look for any .csv file with results
if [ -z "${DEEPLOC_RESULTS_FILE}" ]; then
    DEEPLOC_RESULTS_FILE=$(find "${DEEPLOC_RAW_DIR}" -maxdepth 1 -name "*.csv" -type f | head -1)
fi

if [ -z "${DEEPLOC_RESULTS_FILE}" ] || [ ! -f "${DEEPLOC_RESULTS_FILE}" ]; then
    log_message "CRITICAL ERROR: Could not locate DeepLoc output file!"
    log_message "Expected CSV results in: ${DEEPLOC_RAW_DIR}"
    log_message "Directory contents:"
    ls -la "${DEEPLOC_RAW_DIR}" 2>&1 | tee -a "${LOG_FILE}"
    exit 1
fi

log_message "Found DeepLoc results: ${DEEPLOC_RESULTS_FILE}"

# =============================================================================
# COPY RESULTS TO STANDARDIZED OUTPUT NAME
# =============================================================================
# DeepLoc CSV output columns typically include:
#   Protein_ID, Localizations, Signals, Membrane, Nucleus, Cytoplasm,
#   Extracellular, Mitochondrion, Cell_membrane, Endoplasmic_reticulum,
#   Plastid, Golgi_apparatus, Lysosome/Vacuole, Peroxisome
#
# We preserve the DeepLoc CSV as-is since it already contains the protein ID,
# predicted localization, and probability scores for all compartments.
# =============================================================================

cp "${DEEPLOC_RESULTS_FILE}" "${OUTPUT_PREDICTIONS}"
log_message "Copied DeepLoc results to: ${OUTPUT_PREDICTIONS}"

# =============================================================================
# CLEAN UP RAW OUTPUT
# =============================================================================
# Remove the raw DeepLoc output directory to save disk space.
# The copied CSV contains all needed information.
# =============================================================================

rm -rf "${DEEPLOC_RAW_DIR}"
log_message "Cleaned up raw DeepLoc output directory"

# =============================================================================
# VALIDATE OUTPUTS
# =============================================================================

log_message ""
log_message "Validating outputs..."

# Check predictions output exists
if [ ! -f "${OUTPUT_PREDICTIONS}" ]; then
    log_message "CRITICAL ERROR: Predictions output file was not created!"
    log_message "Expected: ${OUTPUT_PREDICTIONS}"
    exit 1
fi

# Check predictions output is not empty
if [ ! -s "${OUTPUT_PREDICTIONS}" ]; then
    log_message "CRITICAL ERROR: Predictions output file is empty!"
    log_message "Path: ${OUTPUT_PREDICTIONS}"
    exit 1
fi

PREDICTIONS_LINE_COUNT=$(wc -l < "${OUTPUT_PREDICTIONS}")
log_message "Predictions output: ${PREDICTIONS_LINE_COUNT} lines (including header)"

# The file should have at least the header line plus one data line
if [ "${PREDICTIONS_LINE_COUNT}" -lt 2 ]; then
    log_message "CRITICAL ERROR: Predictions output file has no data rows!"
    log_message "Only ${PREDICTIONS_LINE_COUNT} line(s) found (expected header + data)."
    exit 1
fi

# Report count of predicted proteins (data lines = total - 1 header)
PREDICTED_PROTEIN_COUNT=$((PREDICTIONS_LINE_COUNT - 1))
log_message "Proteins with localization predictions: ${PREDICTED_PROTEIN_COUNT}"
log_message "Total proteins in input: ${SEQUENCE_COUNT}"

# Verify predicted count matches input count
if [ "${PREDICTED_PROTEIN_COUNT}" -ne "${SEQUENCE_COUNT}" ]; then
    log_message "WARNING: Prediction count (${PREDICTED_PROTEIN_COUNT}) does not match input sequence count (${SEQUENCE_COUNT})!"
    log_message "Some sequences may have been skipped by DeepLoc."
    log_message "This can happen with very short sequences or sequences with non-standard characters."
fi

# Show localization distribution summary from the CSV
log_message ""
log_message "Localization distribution summary:"
# Extract the localization column (typically column 2) and count occurrences
# Skip header line, cut the localization column, sort, and count
if command -v csvtool &> /dev/null; then
    # If csvtool is available, use it for proper CSV parsing
    tail -n +2 "${OUTPUT_PREDICTIONS}" | csvtool col 2 - 2>/dev/null | sort | uniq -c | sort -rn | while read count localization; do
        log_message "  ${localization}: ${count} proteins"
    done
else
    # Fallback: use Python for CSV parsing
    python3 << PYTHON_SUMMARY_SCRIPT
import csv
import sys
from collections import Counter

input_predictions_path = "${OUTPUT_PREDICTIONS}"

localizations___counts = Counter()

with open( input_predictions_path, 'r' ) as input_predictions:
    reader = csv.reader( input_predictions )
    header = next( reader )

    # Find the localization column (usually named "Localizations" or "Localization")
    localization_column_index = None
    for column_index, column_name in enumerate( header ):
        if 'localization' in column_name.lower() or 'location' in column_name.lower():
            localization_column_index = column_index
            break

    if localization_column_index is None:
        # Default to column 1 (second column) if no match found
        localization_column_index = 1

    for row in reader:
        if len( row ) > localization_column_index:
            localization = row[ localization_column_index ]
            localizations___counts[ localization ] += 1

for localization, count in localizations___counts.most_common():
    print( f"  {localization}: {count} proteins" )
PYTHON_SUMMARY_SCRIPT
fi

# =============================================================================
# COMPLETION
# =============================================================================

log_message ""
log_message "========================================================================"
log_message "Script 002 completed successfully for: ${PHYLONAME}"
log_message "========================================================================"
log_message "Predictions output: ${OUTPUT_PREDICTIONS}"
log_message "Log file: ${LOG_FILE}"
