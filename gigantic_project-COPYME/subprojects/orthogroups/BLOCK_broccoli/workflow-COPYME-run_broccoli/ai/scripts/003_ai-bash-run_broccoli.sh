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
PROTEOME_EXT=".aa"   # extension of input proteomes (matches script 002 output)
STEPS="1,2,3,4"      # broccoli steps to run; comma-separated, must be consecutive

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
        --proteome-ext)
            PROTEOME_EXT="$2"
            shift 2
            ;;
        --steps)
            STEPS="$2"
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
log_message "Tree method (broccoli flag: -phylogenies): ${TREE_METHOD}"
log_message "Proteome extension: ${PROTEOME_EXT}"
log_message "Steps: ${STEPS}"

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
#
# Canonical Broccoli flags (verified against broccoli.py source):
#   -dir          input directory of proteome files
#   -ext          file extension (default '.fasta'; we override to .aa)
#   -threads      number of threads
#   -phylogenies  tree method: nj | me | ml  (NOT '-tree_method'!)
#   -steps        comma-separated list of steps to run (default '1,2,3,4')
#   -e_value      e-value threshold for similarity search (default 0.001)
#   -kmer_size    kmer length (default 100)
#
# Output structure (from broccoli source):
#   dir_step1/   kmer clusters
#   dir_step2/   per-protein phylomes (DIAMOND + FastTree)
#   dir_step3/   orthologous_groups.txt, table_OGs_protein_counts.txt,
#                table_OGs_protein_names.txt, chimeric_proteins.txt,
#                statistics_per_OG.txt, statistics_per_species.txt, etc.
#   dir_step4/   orthologous_pairs.txt
# =============================================================================

log_message ""
log_message "Starting Broccoli orthogroup detection..."
log_message "Step 2 (DIAMOND + per-protein phylogenies) is the dominant cost."
log_message ""

# Try broccoli command first, fall back to python3 broccoli.py
if command -v broccoli &> /dev/null; then
    BROCCOLI_INVOCATION="broccoli"
else
    # Find broccoli.py in conda environment
    BROCCOLI_SCRIPT=$(find "$(conda info --base 2>/dev/null || echo /dev/null)" -name "broccoli.py" 2>/dev/null | head -1)

    if [ -z "${BROCCOLI_SCRIPT}" ]; then
        log_message "CRITICAL ERROR: Broccoli not found!"
        log_message "Ensure the broccoli env (e.g., ai_gigantic_orthogroups_broccoli) is activated."
        exit 1
    fi
    BROCCOLI_INVOCATION="python3 ${BROCCOLI_SCRIPT}"
fi

log_message "Running: ${BROCCOLI_INVOCATION} -dir ${INPUT_DIR} -ext ${PROTEOME_EXT} -threads ${CPUS} -phylogenies ${TREE_METHOD} -steps ${STEPS}"

${BROCCOLI_INVOCATION} \
    -dir "${INPUT_DIR}" \
    -ext "${PROTEOME_EXT}" \
    -threads "${CPUS}" \
    -phylogenies "${TREE_METHOD}" \
    -steps "${STEPS}" \
    2>&1 | tee -a "${LOG_FILE}"

# =============================================================================
# COPY OUTPUTS TO OUTPUT_DIR (fail-fast — every listed file must exist)
# =============================================================================
# Broccoli produces dir_step1 .. dir_step4 in the current working directory.
# Step 3 contains the main user-facing outputs; step 4 contains pairwise
# orthologs. Per the broccoli source (broccoli_step3.py / broccoli_step4.py),
# every file listed below is ALWAYS produced when the steps run successfully.
# Missing = real failure. We copy with the GIGANTIC `3_ai-` prefix so files
# trace cleanly back to broccoli's documented names.

if [ ! -d "dir_step3" ]; then
    log_message "CRITICAL ERROR: dir_step3/ not found — broccoli step 3 did not run."
    exit 1
fi

REQUIRED_STEP3_FILES=(
    orthologous_groups.txt
    table_OGs_protein_counts.txt
    table_OGs_protein_names.txt
    chimeric_proteins.txt
    unclassified_proteins.txt
    statistics_per_OG.txt
    statistics_per_species.txt
    statistics_nb_OGs_VS_nb_species.txt
)

log_message "Copying Broccoli step 3 outputs to ${OUTPUT_DIR}/ with 3_ai- prefix"
for f in "${REQUIRED_STEP3_FILES[@]}"; do
    if [ ! -f "dir_step3/$f" ]; then
        log_message "CRITICAL ERROR: required broccoli output missing: dir_step3/$f"
        log_message "Per broccoli's source, this file is always produced. Its absence indicates a real failure in step 3."
        exit 1
    fi
    cp "dir_step3/$f" "${OUTPUT_DIR}/3_ai-$f"
done

if [ ! -d "dir_step4" ]; then
    log_message "CRITICAL ERROR: dir_step4/ not found — broccoli step 4 did not run."
    exit 1
fi

if [ ! -f "dir_step4/orthologous_pairs.txt" ]; then
    log_message "CRITICAL ERROR: required broccoli output missing: dir_step4/orthologous_pairs.txt"
    exit 1
fi

cp "dir_step4/orthologous_pairs.txt" "${OUTPUT_DIR}/3_ai-orthologous_pairs.txt"
log_message "Copied dir_step4/orthologous_pairs.txt to ${OUTPUT_DIR}/3_ai-orthologous_pairs.txt"

# =============================================================================
# VALIDATE OUTPUT
# =============================================================================

log_message ""
log_message "Validating Broccoli output..."

ORTHOGROUP_COUNT=$(wc -l < "${OUTPUT_DIR}/3_ai-orthologous_groups.txt")
log_message "Orthogroups identified: ${ORTHOGROUP_COUNT}"

CHIMERIC_COUNT=$(wc -l < "${OUTPUT_DIR}/3_ai-chimeric_proteins.txt")
log_message "Chimeric proteins detected: ${CHIMERIC_COUNT}"

PAIRS_COUNT=$(wc -l < "${OUTPUT_DIR}/3_ai-orthologous_pairs.txt")
log_message "Orthologous pairs: ${PAIRS_COUNT}"

# =============================================================================
# COMPLETION
# =============================================================================

log_message ""
log_message "========================================================================"
log_message "Script 003 completed successfully"
log_message "========================================================================"
log_message "Output directory: ${OUTPUT_DIR}"
log_message "Log file: ${LOG_FILE}"
