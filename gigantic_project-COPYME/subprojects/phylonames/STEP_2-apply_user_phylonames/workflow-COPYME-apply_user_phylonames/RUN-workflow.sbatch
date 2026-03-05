#!/bin/bash
#SBATCH --job-name=phylonames_step2
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --qos=YOUR_QOS
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=15gb
#SBATCH --time=0:30:00
#SBATCH --output=slurm_logs/phylonames_step2-%j.log

# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: SLURM wrapper for phylonames STEP 2
# Human: Eric Edsinger

################################################################################
# GIGANTIC Phylonames STEP 2 - SLURM Execution
################################################################################
#
# PURPOSE:
# Submit the STEP 2 phylonames workflow as a SLURM job.
# This is a thin wrapper - all workflow logic is in RUN-workflow.sh.
#
# USAGE:
#   sbatch RUN-workflow.sbatch
#
# PREREQUISITES:
# 1. STEP 1 must have been run successfully
# 2. Edit the SBATCH directives above (account, qos) for your cluster
# 3. Create INPUT_user/user_phylonames.tsv with your custom phylonames
#
# FOR LOCAL MACHINES:
#   bash RUN-workflow.sh
#
################################################################################

mkdir -p slurm_logs
bash RUN-workflow.sh
