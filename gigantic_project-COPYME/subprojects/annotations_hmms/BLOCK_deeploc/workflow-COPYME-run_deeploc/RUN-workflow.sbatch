#!/bin/bash
#SBATCH --job-name=deeploc_annotations
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --qos=YOUR_QOS
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32gb
#SBATCH --time=96:00:00
#SBATCH --partition=hpg-turin
#SBATCH --gres=gpu:l4:1
#SBATCH --output=slurm_logs/deeploc_annotations-%j.log

# AI: Claude Code | Opus 4.6 | 2026 March 14 | Purpose: SLURM wrapper for DeepLoc pipeline
# Human: Eric Edsinger

################################################################################
# GIGANTIC DeepLoc Annotation - SLURM Execution
################################################################################
#
# PURPOSE:
# Submit the DeepLoc workflow as a SLURM job.
# This is a thin wrapper - all workflow logic is in RUN-workflow.sh.
#
# USAGE:
#   sbatch RUN-workflow.sbatch
#
# BEFORE RUNNING:
# 1. Edit the SBATCH directives above (account, qos) for your cluster
#
# FOR LOCAL MACHINES:
#   bash RUN-workflow.sh
#
################################################################################

mkdir -p slurm_logs
bash RUN-workflow.sh
