#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: Run STEP_2 RBH/RBF homolog discovery workflow locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_gene_families STEP_2 - RBH/RBF Homolog Discovery (Local)
################################################################################
#
# PURPOSE:
# Run the STEP_2 homolog discovery workflow for ONE gene family.
# Each workflow copy processes a single gene family.
#
# USAGE:
#   1. Copy the template:
#      cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_01-rbh_rbf_homologs
#   2. Edit rbh_rbf_homologs_config.yaml (set gene_family name and rgs_file)
#   3. Place your RGS file and species keeper list in INPUT_user/
#   4. Run: bash RUN-workflow.sh
#
# FOR SLURM CLUSTERS:
#   sbatch RUN-workflow.sbatch
#
# OUTPUT:
# Results in OUTPUT_pipeline/1-output/ through 16-output/
# AGS files symlinked to output_to_input/ (by RUN-workflow.sh)
#
################################################################################

echo "========================================================================"
echo "GIGANTIC trees_gene_families STEP_2 - RBH/RBF Homolog Discovery (Local)"
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

# Load conda module (required on HPC systems like HiPerGator)
module load conda 2>/dev/null || true

# Activate the environment with NextFlow
if conda activate ai_gigantic_trees_gene_families 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_trees_gene_families"
else
    # Check if nextflow is already available in PATH
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: NextFlow not found!"
        echo ""
        echo "Please ensure NextFlow is installed and available in your PATH."
        echo "Or activate a conda environment that includes NextFlow."
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
if [ ! -f "rbh_rbf_homologs_config.yaml" ]; then
    echo "ERROR: Configuration file not found!"
    echo "Expected: rbh_rbf_homologs_config.yaml"
    exit 1
fi
echo "  [OK] Configuration file found"

# Check species keeper list exists
if [ ! -f "INPUT_user/species_keeper_list.tsv" ]; then
    echo "ERROR: Species keeper list not found!"
    echo "Expected: INPUT_user/species_keeper_list.tsv"
    exit 1
fi
echo "  [OK] Species keeper list found"

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
# Real files live in OUTPUT_pipeline/1-output/ through 16-output/ (created by
# NextFlow above). Symlinks are created in two locations:
#   1. ../output_to_input/  (STEP-level, for downstream STEP_3)
#   2. ai/output_to_input/  (archival, with this workflow run)
#
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
# ============================================================================

echo ""
echo "Creating symlinks for downstream workflows..."

# Extract gene family name from config
GENE_FAMILY=$(grep -A1 "^gene_family:" rbh_rbf_homologs_config.yaml | grep "name:" | sed 's/.*: *"\([^"]*\)".*/\1/')
WORKFLOW_NAME=$(basename "${SCRIPT_DIR}")

# --- STEP-level output_to_input ---
STEP_SHARED_DIR="../output_to_input"
mkdir -p "${STEP_SHARED_DIR}/ags_fastas/${GENE_FAMILY}"
find "${STEP_SHARED_DIR}/ags_fastas/${GENE_FAMILY}" -type l -delete 2>/dev/null

for ags_file in OUTPUT_pipeline/16-output/16_ai-AGS-*.aa; do
    if [ -f "$ags_file" ]; then
        filename=$(basename "$ags_file")
        ln -sf "../../../${WORKFLOW_NAME}/${ags_file}" \
            "${STEP_SHARED_DIR}/ags_fastas/${GENE_FAMILY}/${filename}"
    fi
done

echo "  STEP output_to_input/ -> symlinks created"

# --- Workflow-level ai/output_to_input (archival) ---
WORKFLOW_SHARED_DIR="ai/output_to_input"
mkdir -p "${WORKFLOW_SHARED_DIR}"
find "${WORKFLOW_SHARED_DIR}" -type l -delete 2>/dev/null

for ags_file in OUTPUT_pipeline/16-output/16_ai-AGS-*.aa; do
    if [ -f "$ags_file" ]; then
        filename=$(basename "$ags_file")
        ln -sf "../../${ags_file}" \
            "${WORKFLOW_SHARED_DIR}/${filename}"
    fi
done

echo "  Workflow ai/output_to_input/ -> symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! STEP_2 pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/ through 16-output/"
echo ""
echo "Downstream symlinks:"
echo "  ../output_to_input/ags_fastas/${GENE_FAMILY}/  (for downstream STEP_3)"
echo "  ai/output_to_input/                             (archival with this run)"
echo ""
echo "Next: Run STEP_3 phylogenetic analysis with AGS files"
echo "========================================================================"
echo "Completed: $(date)"
