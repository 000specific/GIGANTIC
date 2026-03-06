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
#   ../../output_to_input/BLOCK_build_annotation_database/
#
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

# --- Subproject-root output_to_input (single canonical location) ---
SUBPROJECT_SHARED_DIR="../../output_to_input/BLOCK_build_annotation_database"
mkdir -p "${SUBPROJECT_SHARED_DIR}"
find "${SUBPROJECT_SHARED_DIR}" -type l -delete 2>/dev/null || true

SYMLINK_COUNT=0

# --- Symlink the annotation_databases directory (all 24 database subdirectories) ---
if [ -d "OUTPUT_pipeline/annotation_databases" ]; then
    # Symlink from subproject output_to_input to real file
    ln -sf "../../BLOCK_build_annotation_database/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/annotation_databases" \
        "${SUBPROJECT_SHARED_DIR}/annotation_databases"
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
                # Symlink from subproject output_to_input to real file
                ln -sf "../../BLOCK_build_annotation_database/${WORKFLOW_DIR_NAME}/${tsv_file}" \
                    "${SUBPROJECT_SHARED_DIR}/${filename}"
                SYMLINK_COUNT=$((SYMLINK_COUNT + 1))
            fi
        done
    fi
done

echo "  Created ${SYMLINK_COUNT} symlinks in output_to_input/BLOCK_build_annotation_database/"

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
echo "  output_to_input/BLOCK_build_annotation_database/  (subproject root)"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
