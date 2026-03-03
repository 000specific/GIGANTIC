#!/bin/bash
#SBATCH --job-name=interproscan_annotations
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --qos=YOUR_QOS
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128gb
#SBATCH --time=96:00:00
#SBATCH --output=slurm_logs/interproscan_annotations-%j.log

# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: SLURM wrapper for InterProScan pipeline
# Human: Eric Edsinger

################################################################################
# GIGANTIC InterProScan Annotation - SLURM Execution
################################################################################
#
# PURPOSE:
# Submit the InterProScan workflow as a SLURM job.
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
