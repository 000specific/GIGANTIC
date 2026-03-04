#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: SLURM wrapper for annotations OCL analysis workflow
# Human: Eric Edsinger

#SBATCH --job-name=gigantic_annotations_ocl
#SBATCH --account=moroz
#SBATCH --qos=moroz-b
#SBATCH --mem=8gb
#SBATCH --time=48:00:00
#SBATCH --cpus-per-task=1
#SBATCH --output=slurm_logs/annotations_ocl_workflow-%j.log
#SBATCH --error=slurm_logs/annotations_ocl_workflow-%j.log

################################################################################
# GIGANTIC annotations_X_ocl - SLURM Wrapper
################################################################################
#
# PURPOSE:
# Thin SLURM wrapper that submits RUN-workflow.sh as a cluster job.
# The actual workflow logic lives in RUN-workflow.sh.
#
# USAGE:
#   sbatch RUN-workflow.sbatch
#
# NOTES:
# - Edit --account and --qos above for your SLURM allocation
# - This job acts as the NextFlow driver; NextFlow submits individual
#   structure jobs to SLURM as separate tasks
# - 48 hour time limit accommodates large structure sets
# - 8GB memory for the NextFlow driver process itself
#
################################################################################

# Create slurm_logs directory
mkdir -p slurm_logs

echo "SLURM Job ID: ${SLURM_JOB_ID}"
echo "Started: $(date)"
echo ""

# Run the workflow
bash RUN-workflow.sh

echo ""
echo "SLURM job completed: $(date)"
