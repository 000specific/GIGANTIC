#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: Run cross-method comparison Nextflow pipeline
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh
# =============================================================================
# Runs the cross-method orthogroup comparison Nextflow pipeline.
# Requires that at least 2 tool projects have completed and populated
# the subproject-root output_to_input/BLOCK_*/ directories.
#
# Prerequisites:
#   - At least 2 of: orthofinder, orthohmm, broccoli must have results
#
# Usage:
#   bash RUN-workflow.sh
#
# FOR SLURM CLUSTERS:
#   sbatch RUN-workflow.sbatch
# =============================================================================

set -e

echo "========================================================================"
echo "Starting Cross-Method Orthogroup Comparison Pipeline"
echo "========================================================================"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Activate GIGANTIC Environment
# ============================================================================

module load conda 2>/dev/null || true

if conda activate ai_gigantic_orthogroups 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_orthogroups"
else
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: Environment 'ai_gigantic_orthogroups' not found!"
        echo ""
        echo "Please run the environment setup script first:"
        echo ""
        echo "  cd ../../../../  # Go to project root"
        echo "  bash RUN-setup_environments.sh"
        echo ""
        echo "Or create this environment manually:"
        echo "  mamba env create -f ../../../../conda_environments/ai_gigantic_orthogroups.yml"
        echo ""
        exit 1
    fi
    echo "Using NextFlow from PATH (environment not activated)"
fi
echo ""

# Run Nextflow pipeline
nextflow run ai/main.nf \
    -c ai/nextflow.config \
    -resume

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "========================================================================"
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "========================================================================"
    exit $EXIT_CODE
fi

# ============================================================================
# Create symlinks for output_to_input directory
# ============================================================================
# Real files live in OUTPUT_pipeline/N-output/ (created by NextFlow above).
# Symlinks are created in ONE location at the subproject root:
#   ../../output_to_input/BLOCK_comparison/
#
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

# --- Subproject-root output_to_input (single canonical location) ---
SUBPROJECT_SHARED_DIR="../../output_to_input/BLOCK_comparison"
mkdir -p "${SUBPROJECT_SHARED_DIR}"

# Remove any stale symlinks from previous runs
find "${SUBPROJECT_SHARED_DIR}" -type l -delete 2>/dev/null

ln -sf "../../BLOCK_comparison/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/2-output/2_ai-method_comparison_summary.tsv" \
    "${SUBPROJECT_SHARED_DIR}/method_comparison_summary.tsv"
ln -sf "../../BLOCK_comparison/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/2-output/2_ai-gene_overlap_between_methods.tsv" \
    "${SUBPROJECT_SHARED_DIR}/gene_overlap_between_methods.tsv"
ln -sf "../../BLOCK_comparison/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/2-output/2_ai-orthogroup_size_comparison.tsv" \
    "${SUBPROJECT_SHARED_DIR}/orthogroup_size_comparison.tsv"

echo "  Created symlinks in output_to_input/BLOCK_comparison/"

echo ""
echo "========================================================================"
echo "SUCCESS! Comparison pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/ through 2-output/"
echo ""
echo "Downstream symlinks:"
echo "  output_to_input/BLOCK_comparison/  (subproject root)"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
