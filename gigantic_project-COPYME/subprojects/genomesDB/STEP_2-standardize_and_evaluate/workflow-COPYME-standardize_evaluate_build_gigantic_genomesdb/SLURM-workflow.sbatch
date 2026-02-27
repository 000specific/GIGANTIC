#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 26 | Purpose: SLURM wrapper for STEP_2 workflow
# Human: Eric Edsinger

#SBATCH --job-name=genomesDB_STEP2
#SBATCH --account=YOUR_ACCOUNT       # <-- USER: Edit this
#SBATCH --qos=YOUR_QOS               # <-- USER: Edit this
#SBATCH --mem=16gb
#SBATCH --time=4:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --output=slurm_logs/STEP2_workflow-%j.log

# =============================================================================
# GIGANTIC genomesDB - STEP_2 SLURM Wrapper
# =============================================================================
#
# This is a thin SLURM wrapper around RUN-workflow.sh
# It handles SLURM configuration and environment setup
#
# Usage:
#   cd workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/
#   sbatch SLURM-workflow.sbatch
#
# =============================================================================

# Create slurm_logs directory
mkdir -p slurm_logs

echo "SLURM Job ID: ${SLURM_JOB_ID}"
echo "Running on: $(hostname)"
echo "Start time: $(date)"
echo ""

# Load required modules
module load conda

# Activate the GIGANTIC genomesDB conda environment
# (Required for gfastats in script 003)
conda activate ai_gigantic_genomesdb

# Run the main workflow
bash RUN-workflow.sh

echo ""
echo "End time: $(date)"
echo "SLURM Job ID: ${SLURM_JOB_ID} completed"
