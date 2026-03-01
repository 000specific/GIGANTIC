#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: Run cross-method comparison Nextflow pipeline
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh
# =============================================================================
# Runs the cross-method orthogroup comparison Nextflow pipeline.
# Requires that at least 2 tool projects have completed and populated
# their output_to_input/ directories.
#
# Prerequisites:
#   - module load conda
#   - conda activate ai_gigantic_orthogroups
#   - module load nextflow
#   - At least 2 of: orthofinder, orthohmm, broccoli must have results
#
# Usage:
#   bash RUN-workflow.sh
# =============================================================================

set -e

echo "========================================================================"
echo "Starting Cross-Method Orthogroup Comparison Pipeline"
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
#   1. BLOCK_comparison/output_to_input/  (canonical, for downstream subprojects)
#   2. ai/output_to_input/               (archival, with this workflow run)
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

# --- BLOCK-level output_to_input (canonical) ---
BLOCK_SHARED_DIR="../output_to_input"
mkdir -p "${BLOCK_SHARED_DIR}"

# Remove any stale symlinks from previous runs
find "${BLOCK_SHARED_DIR}" -type l -delete 2>/dev/null

ln -sf "../workflow-COPYME-compare_methods/OUTPUT_pipeline/2-output/2_ai-method_comparison_summary.tsv" \
    "${BLOCK_SHARED_DIR}/method_comparison_summary.tsv"
ln -sf "../workflow-COPYME-compare_methods/OUTPUT_pipeline/2-output/2_ai-gene_overlap_between_methods.tsv" \
    "${BLOCK_SHARED_DIR}/gene_overlap_between_methods.tsv"
ln -sf "../workflow-COPYME-compare_methods/OUTPUT_pipeline/2-output/2_ai-orthogroup_size_comparison.tsv" \
    "${BLOCK_SHARED_DIR}/orthogroup_size_comparison.tsv"

echo "  BLOCK output_to_input/ -> symlinks created"

# --- Workflow-level ai/output_to_input (archival) ---
WORKFLOW_SHARED_DIR="ai/output_to_input"
mkdir -p "${WORKFLOW_SHARED_DIR}"

# Remove any stale symlinks from previous runs
find "${WORKFLOW_SHARED_DIR}" -type l -delete 2>/dev/null

ln -sf "../../OUTPUT_pipeline/2-output/2_ai-method_comparison_summary.tsv" \
    "${WORKFLOW_SHARED_DIR}/method_comparison_summary.tsv"
ln -sf "../../OUTPUT_pipeline/2-output/2_ai-gene_overlap_between_methods.tsv" \
    "${WORKFLOW_SHARED_DIR}/gene_overlap_between_methods.tsv"
ln -sf "../../OUTPUT_pipeline/2-output/2_ai-orthogroup_size_comparison.tsv" \
    "${WORKFLOW_SHARED_DIR}/orthogroup_size_comparison.tsv"

echo "  Workflow ai/output_to_input/ -> symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! Comparison pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/ through 2-output/"
echo ""
echo "Downstream symlinks:"
echo "  ../output_to_input/  (for downstream subprojects)"
echo "  ai/output_to_input/  (archival with this run)"
echo "========================================================================"
