#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Run SignalP 6 signal peptide prediction on a single species proteome
# Human: Eric Edsinger

# =============================================================================
# 002_ai-bash-run_signalp.sh
# =============================================================================
#
# Runs SignalP 6 signal peptide prediction on a single species proteome FASTA
# file. Parses the SignalP output to create a filtered TSV containing only
# proteins with predicted signal peptides, including cleavage site positions
# and probability scores.
#
# Input:
#   --input-fasta: Path to a single species proteome FASTA file (.aa)
#   --output-dir: Directory for output files
#   --phyloname: GIGANTIC phyloname for the species (used in output naming)
#   --organism-type: Organism group for SignalP (eukarya, gram_positive, gram_negative, archaea)
#   --mode: Prediction mode (slow for accuracy, fast for speed)
#
# Output:
#   {phyloname}_signalp_predictions.tsv - Filtered signal peptide predictions
#       Only includes proteins with predicted signal peptides (not OTHER)
#       Columns: Protein_Identifier, Prediction, Cleavage_Site_Position, SP_Probability
#   2_ai-log-run_signalp_{phyloname}.log - Execution log
#
# Prerequisites:
#   - SignalP 6 installed and available as signalp6
#   - conda environment ai_gigantic_signalp activated
#
# Usage:
#   bash 002_ai-bash-run_signalp.sh \
#       --input-fasta /path/to/species.aa \
#       --output-dir . \
#       --phyloname Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens \
#       --organism-type eukarya \
#       --mode slow
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
ORGANISM_TYPE="eukarya"
MODE="slow"

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
        --organism-type)
            ORGANISM_TYPE="$2"
            shift 2
            ;;
        --mode)
            MODE="$2"
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
LOG_FILE="${LOG_DIR}/2_ai-log-run_signalp_${PHYLONAME}.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

# =============================================================================
# VALIDATE INPUTS
# =============================================================================

log_message "========================================================================"
log_message "Script 002: Run SignalP Signal Peptide Prediction"
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

# Check if signalp6 is available
if ! command -v signalp6 &> /dev/null; then
    log_message "CRITICAL ERROR: signalp6 command not found!"
    log_message "Ensure SignalP 6 is installed and the ai_gigantic_signalp conda environment is activated."
    log_message "SignalP 6 requires a license from DTU Health Tech: https://services.healthtech.dtu.dk/services/SignalP-6.0/"
    exit 1
fi

# Validate organism type
case "${ORGANISM_TYPE}" in
    eukarya|gram_positive|gram_negative|archaea)
        ;;
    *)
        log_message "CRITICAL ERROR: Invalid organism type '${ORGANISM_TYPE}'!"
        log_message "Valid options: eukarya, gram_positive, gram_negative, archaea"
        log_message "For GIGANTIC species (eukaryotic proteomes), use 'eukarya'."
        exit 1
        ;;
esac

# Validate mode
case "${MODE}" in
    slow|fast)
        ;;
    *)
        log_message "CRITICAL ERROR: Invalid mode '${MODE}'!"
        log_message "Valid options: slow (higher accuracy), fast (speed)"
        exit 1
        ;;
esac

log_message "Input FASTA: ${INPUT_FASTA}"
log_message "Output directory: ${OUTPUT_DIR}"
log_message "Phyloname: ${PHYLONAME}"
log_message "Organism type: ${ORGANISM_TYPE}"
log_message "Mode: ${MODE}"

# Count input sequences
SEQUENCE_COUNT=$(grep -c '^>' "${INPUT_FASTA}")
log_message "Input sequences: ${SEQUENCE_COUNT}"

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# =============================================================================
# OUTPUT FILE PATHS
# =============================================================================

SIGNALP_RAW_DIR="${OUTPUT_DIR}/signalp_raw_output_${PHYLONAME}"

# =============================================================================
# RUN SIGNALP 6
# =============================================================================

log_message ""
log_message "Running SignalP 6 signal peptide prediction..."
log_message "This predicts signal peptides and cleavage sites for each protein."
log_message ""

mkdir -p "${SIGNALP_RAW_DIR}"

signalp6 \
    --fastafile "${INPUT_FASTA}" \
    --output_dir "${SIGNALP_RAW_DIR}" \
    --mode "${MODE}" \
    --organism "${ORGANISM_TYPE}" \
    --format txt \
    2>&1 | tee -a "${LOG_FILE}"

SIGNALP_EXIT_CODE=${PIPESTATUS[0]}

if [ ${SIGNALP_EXIT_CODE} -ne 0 ]; then
    log_message "CRITICAL ERROR: SignalP 6 failed with exit code ${SIGNALP_EXIT_CODE}!"
    log_message "Check the log above for specific error messages."
    log_message "Common issues:"
    log_message "  - License not found or expired"
    log_message "  - Invalid FASTA format"
    log_message "  - Insufficient memory"
    exit 1
fi

log_message "SignalP 6 raw output written to: ${SIGNALP_RAW_DIR}"

# =============================================================================
# LOCATE SIGNALP OUTPUT FILE
# =============================================================================
# SignalP 6 writes a summary file (prediction_results.txt or output.txt)
# in the output directory. We need to find and parse it.
# =============================================================================

SIGNALP_RESULTS_FILE=""

# Check common SignalP 6 output filenames
for candidate_filename in "prediction_results.txt" "output.txt" "processed_entries.txt"; do
    if [ -f "${SIGNALP_RAW_DIR}/${candidate_filename}" ]; then
        SIGNALP_RESULTS_FILE="${SIGNALP_RAW_DIR}/${candidate_filename}"
        break
    fi
done

# If no standard filename found, look for any .txt file with results
if [ -z "${SIGNALP_RESULTS_FILE}" ]; then
    SIGNALP_RESULTS_FILE=$(find "${SIGNALP_RAW_DIR}" -maxdepth 1 -name "*.txt" -type f | head -1)
fi

if [ -z "${SIGNALP_RESULTS_FILE}" ] || [ ! -f "${SIGNALP_RESULTS_FILE}" ]; then
    log_message "CRITICAL ERROR: Could not locate SignalP output file!"
    log_message "Expected results in: ${SIGNALP_RAW_DIR}"
    log_message "Directory contents:"
    ls -la "${SIGNALP_RAW_DIR}" 2>&1 | tee -a "${LOG_FILE}"
    exit 1
fi

log_message "SignalP6 raw output present at: ${SIGNALP_RESULTS_FILE}"

# =============================================================================
# VALIDATE RAW OUTPUT
# =============================================================================
# We preserve the raw SignalP6 output directory unchanged. No parsing or
# reduction is performed here — that violates GIGANTIC convention. NextFlow
# publishes ${SIGNALP_RAW_DIR} into OUTPUT_pipeline/2-output/ as declared in
# main.nf.
#
# SignalP6 raw outputs in ${SIGNALP_RAW_DIR}:
#   prediction_results.txt         (per-protein predictions: OTHER/SP/LIPO/TAT
#                                   probabilities + CS Position line)
#   processed_entries.fasta        (input sequences as processed)
#   region_output.gff3             (per-protein region annotations)
#   output_<protein_id>_plot.txt   (per-protein cleavage probability plots,
#                                   one file per protein predicted as SP)
# =============================================================================

# Verify the SignalP6 raw output dir has the predictions file
if [ ! -s "${SIGNALP_RESULTS_FILE}" ]; then
    log_message "CRITICAL ERROR: SignalP6 prediction_results.txt is missing or empty!"
    log_message "Raw output dir: ${SIGNALP_RAW_DIR}"
    log_message "Directory contents:"
    ls -la "${SIGNALP_RAW_DIR}" 2>&1 | tee -a "${LOG_FILE}"
    exit 1
fi

# Report proteins with signal peptide predictions (Prediction != OTHER)
SIGNAL_PEPTIDE_COUNT=$(awk -F'\t' '!/^#/ && NF>1 && $2 != "OTHER" {c++} END {print c+0}' "${SIGNALP_RESULTS_FILE}")
log_message "Proteins with non-OTHER prediction (SP/LIPO/TAT): ${SIGNAL_PEPTIDE_COUNT}"
log_message "Total proteins in input: ${SEQUENCE_COUNT}"
if [ "${SEQUENCE_COUNT}" -gt 0 ]; then
    log_message "Signal peptide detection rate: approximately $(echo "scale=1; ${SIGNAL_PEPTIDE_COUNT} * 100 / ${SEQUENCE_COUNT}" | bc 2>/dev/null || echo "N/A")%"
fi

# =============================================================================
# COMPLETION
# =============================================================================

log_message ""
log_message "========================================================================"
log_message "Script 002 completed successfully for: ${PHYLONAME}"
log_message "========================================================================"
log_message "SignalP6 raw output dir: ${SIGNALP_RAW_DIR}"
log_message "Log file: ${LOG_FILE}"
