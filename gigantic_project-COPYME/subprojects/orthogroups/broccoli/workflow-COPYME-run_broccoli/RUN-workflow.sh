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

nextflow run ai/main.nf \
    -c ai/nextflow.config \
    -resume

echo "========================================================================"
echo "Broccoli pipeline complete"
echo "========================================================================"
