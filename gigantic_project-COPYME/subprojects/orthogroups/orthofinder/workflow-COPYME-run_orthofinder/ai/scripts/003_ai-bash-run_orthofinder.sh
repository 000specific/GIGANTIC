#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: Run OrthoFinder on proteomes
# Human: Eric Edsinger

# =============================================================================
# 003_ai-bash-run_orthofinder.sh
# =============================================================================
#
# Runs OrthoFinder orthogroup detection on prepared proteomes from script 002.
# OrthoFinder uses Diamond for sequence similarity and MCL for clustering.
# The -X flag preserves original sequence identifiers in output files.
#
# Input:
#   Proteomes from OUTPUT_pipeline/2-output/orthofinder_input_proteomes/
#
# Output:
#   OUTPUT_pipeline/3-output/
#     - Orthogroups/ (orthogroup assignment files)
#     - Orthogroup_Sequences/ (FASTA files per orthogroup)
#     - Single_Copy_Orthologue_Sequences/ (single-copy orthologs)
#     - Comparative_Genomics_Statistics/ (statistics)
#     - Gene_Trees/ (gene trees per orthogroup)
#     - Species_Tree/ (species tree)
#     - Orthogroups.tsv (main orthogroup assignments)
#     - Orthogroups_UnassignedGenes.tsv (genes not in orthogroups)
#
# Prerequisites:
#   - conda activate ai_gigantic_orthogroups
#   - Script 002 must have completed
#
# Usage:
#   bash 003_ai-bash-run_orthofinder.sh [--input-dir PATH] [--output-dir PATH] [--cpus N]
#
# =============================================================================

set -e  # Exit on error

# =============================================================================
# CONFIGURATION
# =============================================================================

# Default paths (can be overridden by command-line arguments)
INPUT_DIR="OUTPUT_pipeline/2-output/orthofinder_input_proteomes"
OUTPUT_DIR="OUTPUT_pipeline/3-output"
CPUS=8
SEARCH_METHOD="diamond"  # diamond or blast
MCL_INFLATION="1.5"

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
        --search-method)
            SEARCH_METHOD="$2"
            shift 2
            ;;
        --mcl-inflation)
            MCL_INFLATION="$2"
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
LOG_FILE="${LOG_DIR}/3_ai-log-run_orthofinder.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

# =============================================================================
# MAIN SCRIPT
# =============================================================================

log_message "========================================================================"
log_message "Script 003: Run OrthoFinder"
log_message "========================================================================"

# Validate input directory
if [ ! -d "${INPUT_DIR}" ]; then
    log_message "CRITICAL ERROR: Input directory not found!"
    log_message "Expected path: ${INPUT_DIR}"
    log_message "Run script 002 first to prepare proteomes."
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
log_message "Search method: ${SEARCH_METHOD}"
log_message "MCL inflation: ${MCL_INFLATION}"

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Check if orthofinder is available
if ! command -v orthofinder &> /dev/null; then
    log_message "CRITICAL ERROR: orthofinder command not found!"
    log_message "Ensure conda environment ai_gigantic_orthogroups is activated."
    log_message "Run: conda activate ai_gigantic_orthogroups"
    exit 1
fi

log_message "OrthoFinder version: $(orthofinder --version 2>&1 || echo 'version check failed')"

# =============================================================================
# RUN ORTHOFINDER
# =============================================================================

log_message ""
log_message "Starting OrthoFinder..."
log_message "This may take several hours depending on dataset size."
log_message ""

# Run OrthoFinder with -X flag to preserve original sequence identifiers
# -f: directory containing proteome FASTA files
# -t: number of threads for sequence searches
# -a: number of threads for analyses
# -S: sequence search program (diamond or blast)
# -I: MCL inflation parameter
# -X: preserve original sequence identifiers in output
# -o: output directory

orthofinder \
    -f "${INPUT_DIR}" \
    -t "${CPUS}" \
    -a "${CPUS}" \
    -S "${SEARCH_METHOD}" \
    -I "${MCL_INFLATION}" \
    -X \
    -o "${OUTPUT_DIR}/orthofinder_results" \
    2>&1 | tee -a "${LOG_FILE}"

# =============================================================================
# LOCATE RESULTS
# =============================================================================

log_message ""
log_message "Locating OrthoFinder results..."

# OrthoFinder creates a Results_MONTHDD directory inside its output
# Find the most recent Results directory
RESULTS_DIR=$(find "${OUTPUT_DIR}/orthofinder_results" -maxdepth 2 -name "Results_*" -type d 2>/dev/null | sort | tail -1)

if [ -z "${RESULTS_DIR}" ]; then
    log_message "CRITICAL ERROR: No Results directory found in OrthoFinder output!"
    log_message "Expected in: ${OUTPUT_DIR}/orthofinder_results/"
    log_message "Check the OrthoFinder log above for errors."
    exit 1
fi

log_message "Results directory: ${RESULTS_DIR}"

# Copy key results to our standardized output location
log_message "Copying key results to: ${OUTPUT_DIR}/"

# Copy Orthogroups.tsv (main output)
if [ -f "${RESULTS_DIR}/Orthogroups/Orthogroups.tsv" ]; then
    cp "${RESULTS_DIR}/Orthogroups/Orthogroups.tsv" "${OUTPUT_DIR}/"
    log_message "Copied: Orthogroups.tsv"
else
    log_message "CRITICAL ERROR: Orthogroups.tsv not found!"
    exit 1
fi

# Copy unassigned genes
if [ -f "${RESULTS_DIR}/Orthogroups/Orthogroups_UnassignedGenes.tsv" ]; then
    cp "${RESULTS_DIR}/Orthogroups/Orthogroups_UnassignedGenes.tsv" "${OUTPUT_DIR}/"
    log_message "Copied: Orthogroups_UnassignedGenes.tsv"
fi

# Copy Orthogroups GeneCount
if [ -f "${RESULTS_DIR}/Orthogroups/Orthogroups.GeneCount.tsv" ]; then
    cp "${RESULTS_DIR}/Orthogroups/Orthogroups.GeneCount.tsv" "${OUTPUT_DIR}/"
    log_message "Copied: Orthogroups.GeneCount.tsv"
fi

# Copy single-copy orthologs
if [ -f "${RESULTS_DIR}/Orthogroups/Orthogroups_SingleCopyOrthologues.txt" ]; then
    cp "${RESULTS_DIR}/Orthogroups/Orthogroups_SingleCopyOrthologues.txt" "${OUTPUT_DIR}/"
    log_message "Copied: Orthogroups_SingleCopyOrthologues.txt"
fi

# Copy comparative genomics statistics
if [ -d "${RESULTS_DIR}/Comparative_Genomics_Statistics" ]; then
    cp -r "${RESULTS_DIR}/Comparative_Genomics_Statistics" "${OUTPUT_DIR}/"
    log_message "Copied: Comparative_Genomics_Statistics/"
fi

# =============================================================================
# VALIDATE OUTPUT
# =============================================================================

log_message ""
log_message "Validating OrthoFinder output..."

# Check critical output file
if [ ! -f "${OUTPUT_DIR}/Orthogroups.tsv" ]; then
    log_message "CRITICAL ERROR: Orthogroups.tsv not found in output!"
    exit 1
fi

ORTHOGROUP_COUNT=$(tail -n +2 "${OUTPUT_DIR}/Orthogroups.tsv" | wc -l)
log_message "Orthogroups identified: ${ORTHOGROUP_COUNT}"

if [ -f "${OUTPUT_DIR}/Orthogroups_UnassignedGenes.tsv" ]; then
    UNASSIGNED_COUNT=$(tail -n +2 "${OUTPUT_DIR}/Orthogroups_UnassignedGenes.tsv" | wc -l)
    log_message "Unassigned gene groups: ${UNASSIGNED_COUNT}"
fi

if [ -f "${OUTPUT_DIR}/Orthogroups_SingleCopyOrthologues.txt" ]; then
    SINGLE_COPY_COUNT=$(wc -l < "${OUTPUT_DIR}/Orthogroups_SingleCopyOrthologues.txt")
    log_message "Single-copy orthogroups: ${SINGLE_COPY_COUNT}"
fi

# =============================================================================
# COMPLETION
# =============================================================================

log_message ""
log_message "========================================================================"
log_message "Script 003 completed successfully"
log_message "========================================================================"
log_message "Output directory: ${OUTPUT_DIR}"
log_message "Full OrthoFinder results: ${RESULTS_DIR}"
log_message "Log file: ${LOG_FILE}"
