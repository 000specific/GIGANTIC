#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: Run STEP_1 RGS validation workflow locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_gene_families STEP_1 - RGS Validation (Local)
################################################################################
#
# PURPOSE:
# Validate a single RGS (Reference Gene Set) FASTA file before running STEP_2
# homolog discovery. Each workflow copy processes ONE gene family.
#
# USAGE:
#   1. Copy the template:
#      cp -r workflow-COPYME-validate_rgs workflow-RUN_01-validate_rgs
#   2. Edit rgs_config.yaml (set gene_family name and rgs_file)
#   3. Place your RGS FASTA file in INPUT_user/
#   4. Run: bash RUN-workflow.sh
#
# FOR SLURM CLUSTERS:
#   sbatch RUN-workflow.sbatch
#
# OUTPUT:
# Validated RGS file in OUTPUT_pipeline/1-output/
# Validated RGS symlinked to output_to_input/ (by RUN-workflow.sh)
#
################################################################################

echo "========================================================================"
echo "GIGANTIC trees_gene_families STEP_1 - RGS Validation (Local)"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Activate Environment
# ============================================================================

module load conda 2>/dev/null || true

if conda activate ai_gigantic_trees_gene_families 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_trees_gene_families"
else
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: NextFlow not found!"
        echo ""
        echo "Please ensure NextFlow is installed and available in your PATH."
        exit 1
    fi
    echo "Using NextFlow from PATH"
fi
echo ""

# ============================================================================
# Validate Prerequisites
# ============================================================================

echo "Validating prerequisites..."
echo ""

if [ ! -f "rgs_config.yaml" ]; then
    echo "ERROR: Configuration file not found!"
    echo "Expected: rgs_config.yaml"
    exit 1
fi
echo "  [OK] Configuration file found"

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
# Real files live in OUTPUT_pipeline/1-output/ (created by NextFlow above).
# Symlinks are created in two locations:
#   1. ../output_to_input/  (STEP-level, for downstream STEPs)
#   2. ai/output_to_input/  (archival, with this workflow run)
#
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
# ============================================================================

echo ""
echo "Creating symlinks for downstream workflows..."

# Extract gene family name from config
GENE_FAMILY=$(grep -A1 "^gene_family:" rgs_config.yaml | grep "name:" | sed 's/.*: *"\([^"]*\)".*/\1/')
WORKFLOW_NAME=$(basename "${SCRIPT_DIR}")

# --- STEP-level output_to_input ---
STEP_SHARED_DIR="../output_to_input"
mkdir -p "${STEP_SHARED_DIR}/rgs_fastas/${GENE_FAMILY}"
find "${STEP_SHARED_DIR}/rgs_fastas/${GENE_FAMILY}" -type l -delete 2>/dev/null

ln -sf "../../../${WORKFLOW_NAME}/OUTPUT_pipeline/1-output/1_ai-rgs-${GENE_FAMILY}-validated.aa" \
    "${STEP_SHARED_DIR}/rgs_fastas/${GENE_FAMILY}/1_ai-rgs-${GENE_FAMILY}-validated.aa"

echo "  STEP output_to_input/ -> symlinks created"

# --- Workflow-level ai/output_to_input (archival) ---
WORKFLOW_SHARED_DIR="ai/output_to_input"
mkdir -p "${WORKFLOW_SHARED_DIR}"
find "${WORKFLOW_SHARED_DIR}" -type l -delete 2>/dev/null

ln -sf "../../OUTPUT_pipeline/1-output/1_ai-rgs-${GENE_FAMILY}-validated.aa" \
    "${WORKFLOW_SHARED_DIR}/1_ai-rgs-${GENE_FAMILY}-validated.aa"

echo "  Workflow ai/output_to_input/ -> symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! STEP_1 pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/"
echo ""
echo "Downstream symlinks:"
echo "  ../output_to_input/rgs_fastas/${GENE_FAMILY}/  (for downstream STEPs)"
echo "  ai/output_to_input/                             (archival with this run)"
echo "========================================================================"
echo "Completed: $(date)"
