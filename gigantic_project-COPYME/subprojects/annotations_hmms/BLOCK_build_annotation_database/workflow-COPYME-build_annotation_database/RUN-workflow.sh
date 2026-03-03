#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Run Annotation Database Builder Nextflow pipeline
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh
# =============================================================================
# Runs the Annotation Database Builder Nextflow pipeline.
#
# Usage:
#   bash RUN-workflow.sh
#
# FOR SLURM CLUSTERS:
#   sbatch RUN-workflow.sbatch
# =============================================================================

set -e

echo "========================================================================"
echo "Starting Annotation Database Builder Pipeline"
echo "========================================================================"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Activate GIGANTIC Environment
# ============================================================================

module load conda 2>/dev/null || true

if conda activate ai_gigantic_annotations_hmms 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_annotations_hmms"
else
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: Environment 'ai_gigantic_annotations_hmms' not found!"
        echo ""
        echo "Please run the environment setup script first:"
        echo ""
        echo "  cd ../../../../  # Go to project root"
        echo "  bash RUN-setup_environments.sh"
        echo ""
        echo "Or create this environment manually:"
        echo "  mamba env create -f ../../../../conda_environments/ai_gigantic_annotations_hmms.yml"
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
#   1. BLOCK_build_annotation_database/output_to_input/  (canonical, for downstream subprojects)
#   2. ai/output_to_input/                               (archival, with this workflow run)
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

SYMLINK_COUNT=0

# --- Symlink the annotation_databases directory (all 24 database subdirectories) ---
if [ -d "OUTPUT_pipeline/annotation_databases" ]; then
    # BLOCK-level: BLOCK_build_annotation_database/output_to_input/annotation_databases
    ln -sf "../${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/annotation_databases" "${BLOCK_SHARED_DIR}/annotation_databases"
    # Workflow archival: ai/output_to_input/annotation_databases
    ln -sf "../../OUTPUT_pipeline/annotation_databases" "${WORKFLOW_SHARED_DIR}/annotation_databases"
    SYMLINK_COUNT=$((SYMLINK_COUNT + 1))
    echo "  Linked annotation_databases/ (24 database subdirectories)"
else
    echo "  WARNING: OUTPUT_pipeline/annotation_databases/ not found"
fi

# --- Symlink statistics and analysis output TSVs (scripts 008-016) ---
for output_dir in OUTPUT_pipeline/8-output OUTPUT_pipeline/9-output OUTPUT_pipeline/10-output \
                  OUTPUT_pipeline/11-output OUTPUT_pipeline/12-output OUTPUT_pipeline/13-output \
                  OUTPUT_pipeline/14-output OUTPUT_pipeline/15-output OUTPUT_pipeline/16-output; do
    if [ -d "$output_dir" ]; then
        for tsv_file in ${output_dir}/*_ai-*.tsv; do
            if [ -f "$tsv_file" ]; then
                filename="$(basename "$tsv_file")"
                # BLOCK-level
                ln -sf "../${WORKFLOW_DIR_NAME}/${tsv_file}" "${BLOCK_SHARED_DIR}/${filename}"
                # Workflow archival
                ln -sf "../../${tsv_file}" "${WORKFLOW_SHARED_DIR}/${filename}"
                SYMLINK_COUNT=$((SYMLINK_COUNT + 1))
            fi
        done
    fi
done

echo "  Created ${SYMLINK_COUNT} symlinks in ../output_to_input/"
echo "  Created ${SYMLINK_COUNT} symlinks in ai/output_to_input/"

if [ $SYMLINK_COUNT -eq 0 ]; then
    echo "  WARNING: No output files found in OUTPUT_pipeline/"
    echo "  The pipeline may have produced no outputs."
fi

echo ""
echo "========================================================================"
echo "SUCCESS! Annotation Database Builder Pipeline complete."
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
