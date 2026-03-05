#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: Run STEP_3 phylogenetic analysis workflow locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_gene_families STEP_3 - Phylogenetic Analysis (Local)
################################################################################
#
# PURPOSE:
# Run the STEP_3 phylogenetic analysis workflow for ONE gene family.
# Each workflow copy processes a single gene family.
#
# USAGE:
#   1. Copy the template:
#      cp -r workflow-COPYME-phylogenetic_analysis workflow-RUN_01-phylogenetic_analysis
#   2. Edit START_HERE-user_config.yaml (set gene_family name, choose tree methods)
#   3. Ensure STEP_2 has completed for this gene family
#   4. Run: bash RUN-workflow.sh
#
# FOR SLURM CLUSTERS:
#   sbatch RUN-workflow.sbatch
#
# OUTPUT:
# Results in OUTPUT_pipeline/1-output/ through 7-output/
# Trees and alignments symlinked to ../../output_to_input/STEP_3-phylogenetic_analysis/ (by RUN-workflow.sh)
#
################################################################################

echo "========================================================================"
echo "GIGANTIC trees_gene_families STEP_3 - Phylogenetic Analysis (Local)"
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
if [ ! -f "START_HERE-user_config.yaml" ]; then
    echo "ERROR: Configuration file not found!"
    echo "Expected: START_HERE-user_config.yaml"
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
# Create symlinks for output_to_input (subproject root)
# ============================================================================
# Real files live in OUTPUT_pipeline/N-output/ (created by NextFlow above).
# Symlinks are created at the subproject-root output_to_input/:
#   ../../output_to_input/STEP_3-phylogenetic_analysis/trees/<gene_family>/
#
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
# ============================================================================

echo ""
echo "Creating symlinks for downstream workflows..."

# Extract gene family name from config
GENE_FAMILY=$(grep -A1 "^gene_family:" START_HERE-user_config.yaml | grep "name:" | sed 's/.*: *"\([^"]*\)".*/\1/')
WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

# --- Subproject-root output_to_input ---
SUBPROJECT_SHARED_DIR="../../output_to_input/STEP_3-phylogenetic_analysis"
mkdir -p "${SUBPROJECT_SHARED_DIR}/trees/${GENE_FAMILY}"
find "${SUBPROJECT_SHARED_DIR}/trees/${GENE_FAMILY}" -type l -delete 2>/dev/null

# Symlink alignment files
for mafft_file in OUTPUT_pipeline/3-output/*.mafft; do
    if [ -f "$mafft_file" ]; then
        filename=$(basename "$mafft_file")
        ln -sf "../../../STEP_3-phylogenetic_analysis/${WORKFLOW_DIR_NAME}/${mafft_file}" \
            "${SUBPROJECT_SHARED_DIR}/trees/${GENE_FAMILY}/${filename}"
    fi
done

# Symlink trimmed alignment files
for trimmed_file in OUTPUT_pipeline/4-output/*.clipkit-smartgap; do
    if [ -f "$trimmed_file" ]; then
        filename=$(basename "$trimmed_file")
        ln -sf "../../../STEP_3-phylogenetic_analysis/${WORKFLOW_DIR_NAME}/${trimmed_file}" \
            "${SUBPROJECT_SHARED_DIR}/trees/${GENE_FAMILY}/${filename}"
    fi
done

# Symlink tree files (fasttree and/or iqtree)
for tree_file in OUTPUT_pipeline/5-output/*.fasttree OUTPUT_pipeline/5-output/*.treefile; do
    if [ -f "$tree_file" ]; then
        filename=$(basename "$tree_file")
        ln -sf "../../../STEP_3-phylogenetic_analysis/${WORKFLOW_DIR_NAME}/${tree_file}" \
            "${SUBPROJECT_SHARED_DIR}/trees/${GENE_FAMILY}/${filename}"
    fi
done

echo "  output_to_input/STEP_3-phylogenetic_analysis/ -> symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! STEP_3 pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/ through 7-output/"
echo ""
echo "Downstream symlinks:"
echo "  ../../output_to_input/STEP_3-phylogenetic_analysis/trees/${GENE_FAMILY}/"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
