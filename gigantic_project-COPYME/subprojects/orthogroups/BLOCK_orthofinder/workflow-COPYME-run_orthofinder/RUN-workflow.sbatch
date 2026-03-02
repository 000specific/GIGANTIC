#!/bin/bash
#SBATCH --job-name=orthofinder_orthogroups
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --qos=YOUR_QOS
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8gb
#SBATCH --time=96:00:00
#SBATCH --output=slurm_logs/orthofinder-%j.log

# AI: Claude Code | Opus 4.6 | 2026 March 02 | Purpose: SLURM wrapper for OrthoFinder pipeline
# Human: Eric Edsinger

################################################################################
# GIGANTIC OrthoFinder Orthogroup Detection - SLURM Execution
################################################################################
#
# PURPOSE:
# Submit the OrthoFinder workflow as a SLURM job.
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
