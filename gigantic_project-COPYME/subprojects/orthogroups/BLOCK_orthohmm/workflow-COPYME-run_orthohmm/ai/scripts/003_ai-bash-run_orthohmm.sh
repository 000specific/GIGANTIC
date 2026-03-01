#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: Run OrthoHMM clustering on proteomes
# Human: Eric Edsinger

# =============================================================================
# 003_ai-bash-run_orthohmm.sh
# =============================================================================
#
# Runs OrthoHMM clustering on short-header proteomes from script 002.
# OrthoHMM uses profile Hidden Markov Models to identify orthologous groups.
#
# Input:
#   Short-header proteomes from OUTPUT_pipeline/2-output/short_header_proteomes/
#
# Output:
#   OUTPUT_pipeline/3-output/
#     - orthohmm_orthogroups.txt (main orthogroup assignments)
#     - orthohmm_gene_count.txt (gene counts per orthogroup per species)
#     - orthohmm_single_copy_orthogroups.txt (single-copy orthogroups)
#     - orthohmm_orthogroups/ (FASTA files per orthogroup)
#
# Prerequisites:
#   - conda activate ai_gigantic_orthogroups
#   - Script 002 must have completed
#
# Usage:
#   bash 003_ai-bash-run_orthohmm.sh [--input-dir PATH] [--output-dir PATH] [--cpus N]
#
# =============================================================================

set -e  # Exit on error

# =============================================================================
# CONFIGURATION
# =============================================================================

# Default paths (can be overridden by command-line arguments)
INPUT_DIR="OUTPUT_pipeline/2-output/short_header_proteomes"
OUTPUT_DIR="OUTPUT_pipeline/3-output"
CPUS=8
EVALUE="0.0001"
SINGLE_COPY_THRESHOLD="0.5"

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --input-dir)
            INPUT_DIR="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --cpus)
            CPUS="$2"
            shift 2
            ;;
        --evalue)
            EVALUE="$2"
            shift 2
            ;;
        --single-copy-threshold)
            SINGLE_COPY_THRESHOLD="$2"
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
LOG_FILE="${LOG_DIR}/3_ai-log-run_orthohmm.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

# =============================================================================
# MAIN SCRIPT
# =============================================================================

log_message "========================================================================"
log_message "Script 003: Run OrthoHMM Clustering"
log_message "========================================================================"

# Validate input directory
if [ ! -d "${INPUT_DIR}" ]; then
    log_message "CRITICAL ERROR: Input directory not found!"
    log_message "Expected path: ${INPUT_DIR}"
    log_message "Run script 002 first to generate short-header proteomes."
    exit 1
fi

# Count input files
PROTEOME_COUNT=$(ls -1 "${INPUT_DIR}"/*.aa 2>/dev/null | wc -l)

if [ "${PROTEOME_COUNT}" -eq 0 ]; then
    log_message "CRITICAL ERROR: No proteome files (.aa) found in input directory!"
    log_message "Directory: ${INPUT_DIR}"
    exit 1
fi

log_message "Input directory: ${INPUT_DIR}"
log_message "Proteome count: ${PROTEOME_COUNT}"
log_message "Output directory: ${OUTPUT_DIR}"
log_message "CPUs: ${CPUS}"
log_message "E-value threshold: ${EVALUE}"
log_message "Single-copy threshold: ${SINGLE_COPY_THRESHOLD}"

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Check if orthohmm is available
if ! command -v orthohmm &> /dev/null; then
    log_message "CRITICAL ERROR: orthohmm command not found!"
    log_message "Ensure conda environment ai_gigantic_orthogroups is activated."
    log_message "Run: conda activate ai_gigantic_orthogroups"
    exit 1
fi

log_message "OrthoHMM version: $(orthohmm --version 2>&1 || echo 'version check failed')"

# =============================================================================
# RUN ORTHOHMM
# =============================================================================

log_message ""
log_message "Starting OrthoHMM clustering..."
log_message "This may take several hours depending on dataset size."
log_message ""

# Run orthohmm
# Note: orthohmm takes a directory of FASTA files as input
orthohmm "${INPUT_DIR}" \
    -o "${OUTPUT_DIR}" \
    -c "${CPUS}" \
    -e "${EVALUE}" \
    -s "${SINGLE_COPY_THRESHOLD}" \
    2>&1 | tee -a "${LOG_FILE}"

# =============================================================================
# VALIDATE OUTPUT
# =============================================================================

log_message ""
log_message "Validating OrthoHMM output..."

# Check critical output file
if [ ! -f "${OUTPUT_DIR}/orthohmm_orthogroups.txt" ]; then
    log_message "CRITICAL ERROR: orthohmm_orthogroups.txt not found!"
    log_message "OrthoHMM did not produce expected output."
    log_message "Check the OrthoHMM log above for errors."
    exit 1
fi

ORTHOGROUP_COUNT=$(wc -l < "${OUTPUT_DIR}/orthohmm_orthogroups.txt")
log_message "Orthogroups identified: ${ORTHOGROUP_COUNT}"

# Check for gene count file
if [ -f "${OUTPUT_DIR}/orthohmm_gene_count.txt" ]; then
    log_message "Gene count file: present"
else
    log_message "WARNING: orthohmm_gene_count.txt not produced by OrthoHMM"
fi

# Check for single-copy orthogroups
if [ -f "${OUTPUT_DIR}/orthohmm_single_copy_orthogroups.txt" ]; then
    SINGLE_COPY_COUNT=$(wc -l < "${OUTPUT_DIR}/orthohmm_single_copy_orthogroups.txt")
    log_message "Single-copy orthogroups: ${SINGLE_COPY_COUNT}"
else
    log_message "WARNING: orthohmm_single_copy_orthogroups.txt not produced by OrthoHMM"
fi

# =============================================================================
# COMPLETION
# =============================================================================

log_message ""
log_message "========================================================================"
log_message "Script 003 completed successfully"
log_message "========================================================================"
log_message "Output directory: ${OUTPUT_DIR}"
log_message "Log file: ${LOG_FILE}"
