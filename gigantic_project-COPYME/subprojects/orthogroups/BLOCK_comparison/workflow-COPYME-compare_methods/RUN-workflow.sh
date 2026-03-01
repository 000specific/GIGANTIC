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

nextflow run ai/main.nf \
    -c ai/nextflow.config \
    -resume

echo "========================================================================"
echo "Comparison pipeline complete"
echo "========================================================================"
