#!/bin/bash
#SBATCH --job-name=phylonames
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --qos=YOUR_QOS
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8gb
#SBATCH --time=2:00:00
#SBATCH --output=slurm_logs/phylonames-%j.log

# AI: Claude Code | Opus 4.6 | 2026 March 02 | Purpose: SLURM wrapper for phylonames pipeline
# Human: Eric Edsinger

################################################################################
# GIGANTIC Phylonames Pipeline - SLURM Execution
################################################################################
#
# PURPOSE:
# Submit the phylonames workflow as a SLURM job.
# This is a thin wrapper - all workflow logic is in RUN-workflow.sh.
#
# USAGE:
#   sbatch RUN-workflow.sbatch
#
# BEFORE RUNNING:
# 1. Edit the SBATCH directives above (account, qos) for your cluster
# 2. Edit phylonames_config.yaml with your project settings
# 3. Edit INPUT_gigantic/species_list.txt (at project root) with your species
#    OR edit INPUT_user/species_list.txt directly (workflow-specific)
#
# FOR LOCAL MACHINES:
#   bash RUN-workflow.sh
#
################################################################################

mkdir -p slurm_logs
bash RUN-workflow.sh
