#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: Run Broccoli orthogroup detection on proteomes
# Human: Eric Edsinger

# =============================================================================
# 003_ai-bash-run_broccoli.sh
# =============================================================================
#
# Runs Broccoli orthogroup detection on short-header proteomes from script 002.
# Broccoli uses phylogenetic analysis with network-based label propagation.
#
# Broccoli executes a four-step internal pipeline:
#   Step 1: Kmer clustering
#   Step 2: Diamond similarity search and phylogenetic tree construction
#   Step 3: Network analysis and orthogroup identification
#   Step 4: Pairwise ortholog extraction
#
# Input:
#   Short-header proteomes from OUTPUT_pipeline/2-output/short_header_proteomes/
#
# Output:
#   OUTPUT_pipeline/3-output/
#     - orthologous_groups.txt (main orthogroup assignments)
#     - table_OGs_protein_counts.txt (species-by-orthogroup count matrix)
#     - table_OGs_protein_names.txt (species-by-orthogroup name matrix)
#     - chimeric_proteins.txt (detected chimeric/gene-fusion proteins)
#     - orthologous_pairs.txt (pairwise ortholog relationships)
#
# Prerequisites:
#   - conda activate ai_gigantic_orthogroups
#   - Script 002 must have completed
#
# Usage:
#   bash 003_ai-bash-run_broccoli.sh [--input-dir PATH] [--output-dir PATH] [--cpus N]
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
TREE_METHOD="nj"  # nj (neighbor joining), me (minimum evolution), or ml (maximum likelihood)

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
        --tree-method)
            TREE_METHOD="$2"
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
LOG_FILE="${LOG_DIR}/3_ai-log-run_broccoli.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

# =============================================================================
# MAIN SCRIPT
# =============================================================================

log_message "========================================================================"
log_message "Script 003: Run Broccoli Orthogroup Detection"
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
log_message "Tree method: ${TREE_METHOD}"

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Check if broccoli (python3 broccoli.py) is available
if ! command -v python3 &> /dev/null; then
    log_message "CRITICAL ERROR: python3 not found!"
    exit 1
fi

# =============================================================================
# RUN BROCCOLI
# =============================================================================

log_message ""
log_message "Starting Broccoli orthogroup detection..."
log_message "This may take several hours depending on dataset size."
log_message ""

# Broccoli takes a directory of FASTA files as input
# The exact command depends on the Broccoli installation method
# Common invocations:
#   python3 broccoli.py -dir INPUT_DIR -threads CPUS
#   broccoli -dir INPUT_DIR -threads CPUS

# Try broccoli command first, fall back to python3 broccoli.py
if command -v broccoli &> /dev/null; then
    log_message "Running: broccoli -dir ${INPUT_DIR} -threads ${CPUS} -tree_method ${TREE_METHOD}"

    broccoli \
        -dir "${INPUT_DIR}" \
        -threads "${CPUS}" \
        -tree_method "${TREE_METHOD}" \
        2>&1 | tee -a "${LOG_FILE}"
else
    # Look for broccoli.py in conda environment
    BROCCOLI_SCRIPT=$(find "$(conda info --base 2>/dev/null || echo /dev/null)" -name "broccoli.py" 2>/dev/null | head -1)

    if [ -z "${BROCCOLI_SCRIPT}" ]; then
        log_message "CRITICAL ERROR: Broccoli not found!"
        log_message "Ensure conda environment ai_gigantic_orthogroups is activated."
        log_message "Run: conda activate ai_gigantic_orthogroups"
        exit 1
    fi

    log_message "Running: python3 ${BROCCOLI_SCRIPT} -dir ${INPUT_DIR} -threads ${CPUS} -tree_method ${TREE_METHOD}"

    python3 "${BROCCOLI_SCRIPT}" \
        -dir "${INPUT_DIR}" \
        -threads "${CPUS}" \
        -tree_method "${TREE_METHOD}" \
        2>&1 | tee -a "${LOG_FILE}"
fi

# Broccoli outputs to dir_step4 by default - move results to our output directory
if [ -d "dir_step4" ]; then
    log_message "Moving Broccoli results from dir_step4/ to ${OUTPUT_DIR}/"
    cp -r dir_step4/* "${OUTPUT_DIR}/" 2>/dev/null || true
fi

# =============================================================================
# VALIDATE OUTPUT
# =============================================================================

log_message ""
log_message "Validating Broccoli output..."

# Check critical output file
if [ ! -f "${OUTPUT_DIR}/orthologous_groups.txt" ]; then
    log_message "CRITICAL ERROR: orthologous_groups.txt not found!"
    log_message "Broccoli did not produce expected output."
    log_message "Check the Broccoli log above for errors."
    exit 1
fi

ORTHOGROUP_COUNT=$(wc -l < "${OUTPUT_DIR}/orthologous_groups.txt")
log_message "Orthogroups identified: ${ORTHOGROUP_COUNT}"

# Check for other output files
if [ -f "${OUTPUT_DIR}/table_OGs_protein_counts.txt" ]; then
    log_message "Protein counts table: present"
fi

if [ -f "${OUTPUT_DIR}/chimeric_proteins.txt" ]; then
    CHIMERIC_COUNT=$(wc -l < "${OUTPUT_DIR}/chimeric_proteins.txt")
    log_message "Chimeric proteins detected: ${CHIMERIC_COUNT}"
fi

if [ -f "${OUTPUT_DIR}/orthologous_pairs.txt" ]; then
    PAIRS_COUNT=$(wc -l < "${OUTPUT_DIR}/orthologous_pairs.txt")
    log_message "Orthologous pairs: ${PAIRS_COUNT}"
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
