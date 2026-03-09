#!/bin/bash
#SBATCH --job-name=ncbi_nr_diamond
#SBATCH --account=moroz
#SBATCH --qos=moroz
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=15
#SBATCH --mem=100gb
#SBATCH --time=48:00:00
#SBATCH --output=slurm_logs/ncbi_nr_diamond-%j.log

# AI: Claude Code | Opus 4.6 | 2026 March 09 | Purpose: SLURM wrapper for NCBI nr DIAMOND database build
# Human: Eric Edsinger

################################################################################
# GIGANTIC Public Databases - NCBI nr DIAMOND Database - SLURM Execution
################################################################################
#
# PURPOSE:
# Submit the NCBI nr DIAMOND database workflow as a SLURM job.
# This is a thin wrapper - all workflow logic is in RUN-workflow.sh.
#
# USAGE:
#   sbatch RUN-workflow.sbatch
#
# BEFORE RUNNING:
# 1. Edit the SBATCH directives above (account, qos) for your cluster
# 2. Edit START_HERE-user_config.yaml with your project settings
# 3. Ensure ~300 GB free disk space
#
# FOR LOCAL MACHINES:
#   bash RUN-workflow.sh
#
################################################################################

mkdir -p slurm_logs
bash RUN-workflow.sh
