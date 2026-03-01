#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: Run Broccoli Nextflow pipeline
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh
# =============================================================================
# Runs the Broccoli orthogroup detection Nextflow pipeline.
#
# Prerequisites:
#   - module load conda
#   - conda activate ai_gigantic_orthogroups
#   - module load nextflow
#
# Usage:
#   bash RUN-workflow.sh
# =============================================================================

set -e

echo "========================================================================"
echo "Starting Broccoli Orthogroup Detection Pipeline"
echo "========================================================================"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

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
#   1. BLOCK_broccoli/output_to_input/  (canonical, for downstream subprojects)
#   2. ai/output_to_input/              (archival, with this workflow run)
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

# --- BLOCK-level output_to_input (canonical) ---
BLOCK_SHARED_DIR="../output_to_input"
mkdir -p "${BLOCK_SHARED_DIR}"

# Remove any stale symlinks from previous runs
find "${BLOCK_SHARED_DIR}" -type l -delete 2>/dev/null

ln -sf "../workflow-COPYME-run_broccoli/OUTPUT_pipeline/4-output/4_ai-orthogroups_gigantic_ids.tsv" \
    "${BLOCK_SHARED_DIR}/orthogroups_gigantic_ids.tsv"
ln -sf "../workflow-COPYME-run_broccoli/OUTPUT_pipeline/4-output/4_ai-gene_count_gigantic_ids.tsv" \
    "${BLOCK_SHARED_DIR}/gene_count_gigantic_ids.tsv"
ln -sf "../workflow-COPYME-run_broccoli/OUTPUT_pipeline/5-output/5_ai-summary_statistics.tsv" \
    "${BLOCK_SHARED_DIR}/summary_statistics.tsv"
ln -sf "../workflow-COPYME-run_broccoli/OUTPUT_pipeline/6-output/6_ai-per_species_summary.tsv" \
    "${BLOCK_SHARED_DIR}/per_species_summary.tsv"

echo "  BLOCK output_to_input/ -> symlinks created"

# --- Workflow-level ai/output_to_input (archival) ---
WORKFLOW_SHARED_DIR="ai/output_to_input"
mkdir -p "${WORKFLOW_SHARED_DIR}"

# Remove any stale symlinks from previous runs
find "${WORKFLOW_SHARED_DIR}" -type l -delete 2>/dev/null

ln -sf "../../OUTPUT_pipeline/4-output/4_ai-orthogroups_gigantic_ids.tsv" \
    "${WORKFLOW_SHARED_DIR}/orthogroups_gigantic_ids.tsv"
ln -sf "../../OUTPUT_pipeline/4-output/4_ai-gene_count_gigantic_ids.tsv" \
    "${WORKFLOW_SHARED_DIR}/gene_count_gigantic_ids.tsv"
ln -sf "../../OUTPUT_pipeline/5-output/5_ai-summary_statistics.tsv" \
    "${WORKFLOW_SHARED_DIR}/summary_statistics.tsv"
ln -sf "../../OUTPUT_pipeline/6-output/6_ai-per_species_summary.tsv" \
    "${WORKFLOW_SHARED_DIR}/per_species_summary.tsv"

echo "  Workflow ai/output_to_input/ -> symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! Broccoli pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/ through 6-output/"
echo ""
echo "Downstream symlinks:"
echo "  ../output_to_input/  (for downstream subprojects)"
echo "  ai/output_to_input/  (archival with this run)"
echo "========================================================================"
