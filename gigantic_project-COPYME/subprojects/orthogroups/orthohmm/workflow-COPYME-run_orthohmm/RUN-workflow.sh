#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: Run OrthoHMM Nextflow pipeline
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh
# =============================================================================
# Runs the OrthoHMM orthogroup detection Nextflow pipeline.
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
echo "Starting OrthoHMM Orthogroup Detection Pipeline"
echo "========================================================================"

# Run Nextflow pipeline
nextflow run ai/main.nf \
    -c ai/nextflow.config \
    -resume

echo "========================================================================"
echo "OrthoHMM pipeline complete"
echo "========================================================================"
