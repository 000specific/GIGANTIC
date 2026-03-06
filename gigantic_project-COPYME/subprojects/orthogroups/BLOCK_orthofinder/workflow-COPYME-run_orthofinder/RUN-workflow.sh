#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: Run OrthoFinder Nextflow pipeline
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh
# =============================================================================
# Runs the OrthoFinder orthogroup detection Nextflow pipeline.
#
# Usage:
#   bash RUN-workflow.sh
#
# FOR SLURM CLUSTERS:
#   sbatch RUN-workflow.sbatch
# =============================================================================

set -e

echo "========================================================================"
echo "Starting OrthoFinder Orthogroup Detection Pipeline"
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
    -c ai/nextflow.config

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
#   ../../output_to_input/BLOCK_orthofinder/
#
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

# --- Subproject-root output_to_input (single canonical location) ---
SUBPROJECT_SHARED_DIR="../../output_to_input/BLOCK_orthofinder"
mkdir -p "${SUBPROJECT_SHARED_DIR}"

# Remove any stale symlinks from previous runs
find "${SUBPROJECT_SHARED_DIR}" -type l -delete 2>/dev/null

ln -sf "../../BLOCK_orthofinder/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/4-output/4_ai-orthogroups_gigantic_ids.tsv" \
    "${SUBPROJECT_SHARED_DIR}/orthogroups_gigantic_ids.tsv"
ln -sf "../../BLOCK_orthofinder/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/4-output/4_ai-gene_count_gigantic_ids.tsv" \
    "${SUBPROJECT_SHARED_DIR}/gene_count_gigantic_ids.tsv"
ln -sf "../../BLOCK_orthofinder/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/5-output/5_ai-summary_statistics.tsv" \
    "${SUBPROJECT_SHARED_DIR}/summary_statistics.tsv"
ln -sf "../../BLOCK_orthofinder/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/6-output/6_ai-per_species_summary.tsv" \
    "${SUBPROJECT_SHARED_DIR}/per_species_summary.tsv"

echo "  Created symlinks in output_to_input/BLOCK_orthofinder/"

echo ""
echo "========================================================================"
echo "SUCCESS! OrthoFinder pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/ through 6-output/"
echo ""
echo "Downstream symlinks:"
echo "  output_to_input/BLOCK_orthofinder/  (subproject root)"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
