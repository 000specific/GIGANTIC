#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Run MetaPredict Nextflow pipeline
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh
# =============================================================================
# Runs the MetaPredict annotation Nextflow pipeline.
#
# Usage:
#   bash RUN-workflow.sh
#
# FOR SLURM CLUSTERS:
#   sbatch RUN-workflow.sbatch
# =============================================================================

set -e

echo "========================================================================"
echo "Starting MetaPredict Annotation Pipeline"
echo "========================================================================"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Activate GIGANTIC Environment
# ============================================================================

module load conda 2>/dev/null || true

if conda activate ai_gigantic_metapredict 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_metapredict"
else
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: Environment 'ai_gigantic_metapredict' not found!"
        echo ""
        echo "Please run the environment setup script first:"
        echo ""
        echo "  cd ../../../../  # Go to project root"
        echo "  bash RUN-setup_environments.sh"
        echo ""
        echo "Or create this environment manually:"
        echo "  mamba env create -f ../../../../conda_environments/ai_gigantic_metapredict.yml"
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
# Create symlinks for output_to_input directories
# ============================================================================
# Real files live in OUTPUT_pipeline/N-output/ (created by NextFlow above).
# Symlinks are created in two locations:
#   1. BLOCK_metapredict/output_to_input/  (canonical, for downstream subprojects)
#   2. ai/output_to_input/                 (archival, with this workflow run)
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

# --- BLOCK-level output_to_input (canonical, for downstream subprojects) ---
BLOCK_SHARED_DIR="../output_to_input"
mkdir -p "${BLOCK_SHARED_DIR}"
find "${BLOCK_SHARED_DIR}" -type l -delete 2>/dev/null || true

# --- Workflow-level ai/output_to_input (archival, with this workflow run) ---
WORKFLOW_SHARED_DIR="ai/output_to_input"
mkdir -p "${WORKFLOW_SHARED_DIR}"
find "${WORKFLOW_SHARED_DIR}" -type l -delete 2>/dev/null || true

# --- Create relative symlinks for per-species MetaPredict result files ---
# Real files: OUTPUT_pipeline/2-output/{phyloname}_metapredict_idrs.tsv
#             OUTPUT_pipeline/2-output/{phyloname}_metapredict_disorder.tsv
RESULT_DIR="OUTPUT_pipeline/2-output"
SYMLINK_COUNT=0

for result_file in ${RESULT_DIR}/*_metapredict_idrs.tsv ${RESULT_DIR}/*_metapredict_disorder.tsv; do
    if [ -f "$result_file" ]; then
        filename="$(basename "$result_file")"
        # BLOCK-level: BLOCK_metapredict/output_to_input/ -> workflow/OUTPUT_pipeline/2-output/
        ln -sf "../${WORKFLOW_DIR_NAME}/${result_file}" "${BLOCK_SHARED_DIR}/${filename}"
        # Workflow archival: ai/output_to_input/ -> ../../OUTPUT_pipeline/2-output/
        ln -sf "../../${result_file}" "${WORKFLOW_SHARED_DIR}/${filename}"
        SYMLINK_COUNT=$((SYMLINK_COUNT + 1))
    fi
done

echo "  Created ${SYMLINK_COUNT} symlinks in ../output_to_input/"
echo "  Created ${SYMLINK_COUNT} symlinks in ai/output_to_input/"

if [ $SYMLINK_COUNT -eq 0 ]; then
    echo "  WARNING: No MetaPredict result files found in ${RESULT_DIR}/"
    echo "  The pipeline may have produced no outputs."
fi

echo ""
echo "========================================================================"
echo "SUCCESS! MetaPredict Annotation Pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/"
echo ""
echo "Downstream symlinks:"
echo "  ../output_to_input/  (for downstream subprojects)"
echo "  ai/output_to_input/  (archival with this run)"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
