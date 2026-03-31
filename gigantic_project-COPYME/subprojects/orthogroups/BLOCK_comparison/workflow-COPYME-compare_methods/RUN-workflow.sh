#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 30 | Purpose: Run orthogroup clustering comparison Nextflow pipeline
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh
# =============================================================================
# Runs the orthogroup clustering comparison pipeline.
#
# Prerequisites:
#   1. Edit START_HERE-user_config.yaml (or use defaults)
#   2. Create INPUT_user/clustering_manifest.tsv from the example:
#        cp INPUT_user/clustering_manifest_example.tsv INPUT_user/clustering_manifest.tsv
#   3. Edit the manifest with paths to your clustering run OUTPUT_pipeline directories
#   4. At least 2 clustering runs must be listed in the manifest
#
# Usage:
#   bash RUN-workflow.sh
#
# FOR SLURM CLUSTERS:
#   sbatch SLURM_workflow.sbatch
# =============================================================================

set -e

echo "========================================================================"
echo "Starting Orthogroup Clustering Comparison Pipeline"
echo "========================================================================"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Validate manifest exists
# ============================================================================

MANIFEST="INPUT_user/clustering_manifest.tsv"

if [ ! -f "${MANIFEST}" ]; then
    echo "ERROR: Manifest not found: ${MANIFEST}"
    echo ""
    echo "Create it from the example:"
    echo "  cp INPUT_user/clustering_manifest_example.tsv INPUT_user/clustering_manifest.tsv"
    echo ""
    echo "Then edit it with your clustering run paths."
    exit 1
fi

echo "Manifest: ${MANIFEST}"
echo ""

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

# ============================================================================
# Run Nextflow pipeline
# ============================================================================

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

echo ""
echo "Creating symlinks for downstream subprojects..."

WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

SUBPROJECT_SHARED_DIR="../../output_to_input/BLOCK_comparison"
mkdir -p "${SUBPROJECT_SHARED_DIR}"

# Remove stale symlinks from previous runs
find "${SUBPROJECT_SHARED_DIR}" -type l -delete 2>/dev/null

ln -sf "../../BLOCK_comparison/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/1-output/1_ai-compare_clustering_runs.tsv" \
    "${SUBPROJECT_SHARED_DIR}/compare_clustering_runs.tsv"
ln -sf "../../BLOCK_comparison/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/1-output/1_ai-per_species_copy_number_profiles.tsv" \
    "${SUBPROJECT_SHARED_DIR}/per_species_copy_number_profiles.tsv"
ln -sf "../../BLOCK_comparison/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/1-output/1_ai-pairwise_run_overlap.tsv" \
    "${SUBPROJECT_SHARED_DIR}/pairwise_run_overlap.tsv"

echo "  Created symlinks in output_to_input/BLOCK_comparison/"

echo ""
echo "========================================================================"
echo "SUCCESS! Clustering comparison pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/  (comparison tables)"
echo "  OUTPUT_pipeline/2-output/  (visualization plots)"
echo ""
echo "Downstream symlinks:"
echo "  output_to_input/BLOCK_comparison/  (subproject root)"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
