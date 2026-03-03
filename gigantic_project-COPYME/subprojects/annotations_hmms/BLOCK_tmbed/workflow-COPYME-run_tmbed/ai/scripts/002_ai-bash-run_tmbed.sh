#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Run TMbed transmembrane topology prediction on a single species proteome
# Human: Eric Edsinger

# =============================================================================
# 002_ai-bash-run_tmbed.sh
# =============================================================================
#
# Runs TMbed transmembrane topology prediction on a single species proteome
# FASTA file. TMbed uses protein language models to predict transmembrane
# topology (alpha-helical and beta-barrel) and signal peptides.
#
# Input:
#   --input-fasta: Path to a single species proteome FASTA file (.aa)
#   --output-dir: Directory for output files
#   --phyloname: GIGANTIC phyloname for the species (used in output naming)
#   --batch-size: Number of sequences per prediction batch (default: 1)
#   --use-gpu: Whether to use GPU acceleration (true/false, default: true)
#   --cpu-fallback: Whether to fall back to CPU if GPU unavailable (true/false, default: true)
#
# Output:
#   {phyloname}_tmbed_predictions.3line - TMbed topology predictions in 3-line format
#       Per protein:
#         >protein_id
#         AMINOACIDSEQUENCE...
#         ....HHHHHHHHHH....  (topology annotation string)
#       Topology codes:
#         H/h = transmembrane helix (alpha-helical)
#         B/b = transmembrane beta strand (beta-barrel)
#         S   = signal peptide
#         .   = other (non-membrane, non-signal)
#
#   2_ai-log-run_tmbed_{phyloname}.log - Execution log
#
# Prerequisites:
#   - TMbed installed and available as tmbed
#   - conda environment ai_gigantic_tmbed activated
#   - GPU recommended but CPU fallback supported
#
# Usage:
#   bash 002_ai-bash-run_tmbed.sh \
#       --input-fasta /path/to/species.aa \
#       --output-dir . \
#       --phyloname Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens \
#       --batch-size 1 \
#       --use-gpu true \
#       --cpu-fallback true
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
BATCH_SIZE=1
USE_GPU="true"
CPU_FALLBACK="true"

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
        --batch-size)
            BATCH_SIZE="$2"
            shift 2
            ;;
        --use-gpu)
            USE_GPU="$2"
            shift 2
            ;;
        --cpu-fallback)
            CPU_FALLBACK="$2"
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
LOG_FILE="${LOG_DIR}/2_ai-log-run_tmbed_${PHYLONAME}.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

# =============================================================================
# VALIDATE INPUTS
# =============================================================================

log_message "========================================================================"
log_message "Script 002: Run TMbed Transmembrane Topology Prediction"
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

# Check if tmbed is available
if ! command -v tmbed &> /dev/null; then
    log_message "CRITICAL ERROR: tmbed command not found!"
    log_message "Ensure TMbed is installed and the ai_gigantic_tmbed conda environment is activated."
    log_message "Install with: pip install tmbed"
    exit 1
fi

log_message "Input FASTA: ${INPUT_FASTA}"
log_message "Output directory: ${OUTPUT_DIR}"
log_message "Phyloname: ${PHYLONAME}"
log_message "Batch size: ${BATCH_SIZE}"
log_message "Use GPU: ${USE_GPU}"
log_message "CPU fallback: ${CPU_FALLBACK}"

# Count input sequences
SEQUENCE_COUNT=$(grep -c '^>' "${INPUT_FASTA}")
log_message "Input sequences: ${SEQUENCE_COUNT}"

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# =============================================================================
# OUTPUT FILE PATHS
# =============================================================================

OUTPUT_PREDICTIONS="${OUTPUT_DIR}/${PHYLONAME}_tmbed_predictions.3line"

# =============================================================================
# BUILD TMBED COMMAND
# =============================================================================
# TMbed predict command:
#   tmbed predict -f INPUT -p OUTPUT [--use-gpu] [--cpu-fallback] [--batch-size N]
#
# The output is a 3-line format file per protein:
#   >protein_id
#   SEQUENCE...
#   ....HHHHHHHHHH....  (topology string)
# =============================================================================

log_message ""
log_message "Running TMbed transmembrane topology prediction..."
log_message "This predicts transmembrane helices, beta barrels, and signal peptides."
log_message ""

# Build the tmbed command with conditional flags
TMBED_COMMAND="tmbed predict -f ${INPUT_FASTA} -p ${OUTPUT_PREDICTIONS} --batch-size ${BATCH_SIZE}"

if [ "${USE_GPU}" = "true" ]; then
    TMBED_COMMAND="${TMBED_COMMAND} --use-gpu"
    log_message "GPU acceleration: enabled"
fi

if [ "${CPU_FALLBACK}" = "true" ]; then
    TMBED_COMMAND="${TMBED_COMMAND} --cpu-fallback"
    log_message "CPU fallback: enabled"
fi

log_message "Command: ${TMBED_COMMAND}"
log_message ""

# Run TMbed
eval ${TMBED_COMMAND} 2>&1 | tee -a "${LOG_FILE}"

TMBED_EXIT_CODE=${PIPESTATUS[0]}

if [ ${TMBED_EXIT_CODE} -ne 0 ]; then
    log_message "CRITICAL ERROR: TMbed failed with exit code ${TMBED_EXIT_CODE}!"
    log_message "Check the log above for specific error messages."
    log_message "Common issues:"
    log_message "  - Insufficient GPU memory (try reducing --batch-size or using --cpu-fallback)"
    log_message "  - Invalid FASTA format (non-standard amino acid characters)"
    log_message "  - Missing model weights (TMbed downloads on first run)"
    log_message "  - Insufficient system memory for large proteomes"
    exit 1
fi

log_message "TMbed prediction complete."

# =============================================================================
# VALIDATE OUTPUTS
# =============================================================================

log_message ""
log_message "Validating outputs..."

# Check predictions output exists
if [ ! -f "${OUTPUT_PREDICTIONS}" ]; then
    log_message "CRITICAL ERROR: Predictions output file was not created!"
    log_message "Expected: ${OUTPUT_PREDICTIONS}"
    log_message "TMbed may have completed without writing output."
    exit 1
fi

# Check predictions output is not empty
if [ ! -s "${OUTPUT_PREDICTIONS}" ]; then
    log_message "CRITICAL ERROR: Predictions output file is empty!"
    log_message "Path: ${OUTPUT_PREDICTIONS}"
    log_message "TMbed produced no output. Check input FASTA format."
    exit 1
fi

# Count predicted proteins in the 3-line output (count header lines starting with >)
PREDICTED_COUNT=$(grep -c '^>' "${OUTPUT_PREDICTIONS}")
log_message "Proteins with predictions: ${PREDICTED_COUNT}"
log_message "Total proteins in input: ${SEQUENCE_COUNT}"

# Verify all input sequences received predictions
if [ "${PREDICTED_COUNT}" -ne "${SEQUENCE_COUNT}" ]; then
    log_message "WARNING: Prediction count (${PREDICTED_COUNT}) does not match input sequence count (${SEQUENCE_COUNT})!"
    log_message "Some sequences may have been skipped by TMbed."
    log_message "This can happen with very short sequences or sequences with non-standard characters."
fi

# Count transmembrane proteins (proteins with at least one H, h, B, or b in topology line)
# In 3-line format, every 3rd line (lines 3, 6, 9, ...) is the topology annotation
TRANSMEMBRANE_COUNT=$(awk 'NR%3==0 && /[HhBb]/' "${OUTPUT_PREDICTIONS}" | wc -l)
log_message "Proteins with predicted transmembrane regions: ${TRANSMEMBRANE_COUNT}"

if [ "${PREDICTED_COUNT}" -gt 0 ]; then
    TRANSMEMBRANE_PERCENT=$(echo "scale=1; ${TRANSMEMBRANE_COUNT} * 100 / ${PREDICTED_COUNT}" | bc 2>/dev/null || echo "N/A")
    log_message "Transmembrane protein rate: approximately ${TRANSMEMBRANE_PERCENT}%"
fi

# Count signal peptide proteins (proteins with S in topology line)
SIGNAL_PEPTIDE_COUNT=$(awk 'NR%3==0 && /S/' "${OUTPUT_PREDICTIONS}" | wc -l)
log_message "Proteins with predicted signal peptides: ${SIGNAL_PEPTIDE_COUNT}"

# =============================================================================
# COMPLETION
# =============================================================================

log_message ""
log_message "========================================================================"
log_message "Script 002 completed successfully for: ${PHYLONAME}"
log_message "========================================================================"
log_message "Predictions output: ${OUTPUT_PREDICTIONS}"
log_message "Log file: ${LOG_FILE}"
