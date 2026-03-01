#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: Run OrthoFinder Nextflow pipeline
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh
# =============================================================================
# Runs the OrthoFinder orthogroup detection Nextflow pipeline.
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
echo "Starting OrthoFinder Orthogroup Detection Pipeline"
echo "========================================================================"

nextflow run ai/main.nf \
    -c ai/nextflow.config \
    -resume

echo "========================================================================"
echo "OrthoFinder pipeline complete"
echo "========================================================================"
