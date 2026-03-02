#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Run gene_sizes analysis workflow locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC gene_sizes - Analyze Gene Sizes (Local)
################################################################################
#
# PURPOSE:
# Compute gene structure metrics from user-provided CDS interval data and
# produce genome-wide statistics, relative size ranks, and cross-species summaries.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Provide per-species gene structure TSV files in INPUT_user/
#    (see gene_sizes_config.yaml for format details)
# 2. Copy or symlink the GIGANTIC species list to INPUT_user/gigantic_species_list.txt
# 3. Edit gene_sizes_config.yaml to verify paths
# 4. (Optional) Set proteome_dir in config for GIGANTIC ID linkage
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN-workflow.sbatch
#
# WHAT THIS DOES:
# 1. Validates user-provided gene structure files against the GIGANTIC species set
#    - Species with valid data: PROCESSED
#    - Species without files: SKIPPED_NO_DATA (graceful)
#    - Species with incomplete data: SKIPPED_INCOMPLETE (graceful)
# 2. Extracts per-gene metrics: gene length, exonic/intronic length, exon count, protein size
# 3. Computes genome-wide statistics and relative rank (quantile) per species
# 4. Compiles cross-species summary tables with processing status
# 5. Creates output_to_input/ symlinks for downstream subprojects
#
# OUTPUT:
# Results in OUTPUT_pipeline/1-output through 4-output/
# Downstream symlinks in ../../output_to_input/ and ../output_to_input/
#
################################################################################

echo "========================================================================"
echo "GIGANTIC gene_sizes Pipeline (Local)"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Activate GIGANTIC Environment
# ============================================================================

# Load conda module (required on HPC systems like HiPerGator)
module load conda 2>/dev/null || true

# Activate the gene_sizes environment
if conda activate ai_gigantic_gene_sizes 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_gene_sizes"
else
    # Check if nextflow is already available in PATH
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: Environment 'ai_gigantic_gene_sizes' not found!"
        echo ""
        echo "Please run the environment setup script first:"
        echo ""
        echo "  cd ../../../../  # Go to project root"
        echo "  bash RUN-setup_environments.sh"
        echo ""
        exit 1
    fi
    echo "Using NextFlow from PATH (environment not activated)"
fi
echo ""

# ============================================================================
# Validate Prerequisites
# ============================================================================

echo "Validating prerequisites..."
echo ""

# Check config file exists
if [ ! -f "gene_sizes_config.yaml" ]; then
    echo "ERROR: Configuration file not found!"
    echo "Expected: gene_sizes_config.yaml"
    exit 1
fi
echo "  [OK] Configuration file found"

# Check INPUT_user directory exists
if [ ! -d "INPUT_user" ]; then
    echo "ERROR: INPUT_user/ directory not found!"
    echo "  Create it and add per-species gene structure TSV files."
    echo "  See gene_sizes_config.yaml for format details."
    exit 1
fi
echo "  [OK] INPUT_user/ directory found"

echo ""

# ============================================================================
# Run NextFlow Pipeline
# ============================================================================

echo "Running NextFlow pipeline..."
echo ""

nextflow run ai/main.nf

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "========================================================================"
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "Check the logs above for error details."
    echo "========================================================================"
    exit $EXIT_CODE
fi

# ============================================================================
# Create symlinks for output_to_input directories
# ============================================================================
# Real files live in OUTPUT_pipeline/4-output/ (created by NextFlow above).
# Symlinks are created in two locations:
#   1. ../output_to_input/     (BLOCK-level canonical, for downstream subprojects)
#   2. ai/output_to_input/     (archival, with this workflow run)
#
# gene_sizes creates per-species directories (speciesN_gigantic_gene_metrics,
# speciesN_gigantic_gene_sizes_summary) which are discovered dynamically.
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

# --- BLOCK-level output_to_input (canonical) ---
BLOCK_SHARED_DIR="../output_to_input"
mkdir -p "${BLOCK_SHARED_DIR}"

# Remove any stale symlinks from previous runs
for old_link in "${BLOCK_SHARED_DIR}"/species*_gigantic_gene_*; do
    if [ -L "$old_link" ]; then
        rm "$old_link"
    fi
done

# Create symlinks for each species directory in 4-output/
for species_dir in OUTPUT_pipeline/4-output/species*_gigantic_*; do
    if [ -d "$species_dir" ] || [ -L "$species_dir" ]; then
        dir_name=$(basename "$species_dir")
        ln -sf "../workflow-COPYME-analyze_gene_sizes/OUTPUT_pipeline/4-output/${dir_name}" \
            "${BLOCK_SHARED_DIR}/${dir_name}"
    fi
done

echo "  BLOCK output_to_input/ -> symlinks created"

# --- Workflow-level ai/output_to_input (archival) ---
WORKFLOW_SHARED_DIR="ai/output_to_input"
mkdir -p "${WORKFLOW_SHARED_DIR}"

# Remove any stale symlinks from previous runs
find "${WORKFLOW_SHARED_DIR}" -type l -delete 2>/dev/null

# Create symlinks for each species directory
for species_dir in OUTPUT_pipeline/4-output/species*_gigantic_*; do
    if [ -d "$species_dir" ] || [ -L "$species_dir" ]; then
        dir_name=$(basename "$species_dir")
        ln -sf "../../OUTPUT_pipeline/4-output/${dir_name}" \
            "${WORKFLOW_SHARED_DIR}/${dir_name}"
    fi
done

echo "  Workflow ai/output_to_input/ -> symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! gene_sizes pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/  Species processing status"
echo "  OUTPUT_pipeline/2-output/  Per-species gene metrics"
echo "  OUTPUT_pipeline/3-output/  Ranked metrics and genome summaries"
echo "  OUTPUT_pipeline/4-output/  Cross-species summary and downstream dirs"
echo ""
echo "Downstream symlinks:"
echo "  ../output_to_input/  (BLOCK-level, for downstream subprojects)"
echo "  ai/output_to_input/  (archival with this run)"
echo ""
echo "Published directories:"
echo "  speciesN_gigantic_gene_metrics/         Per-species ranked gene metrics"
echo "  speciesN_gigantic_gene_sizes_summary/   Cross-species summary statistics"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
