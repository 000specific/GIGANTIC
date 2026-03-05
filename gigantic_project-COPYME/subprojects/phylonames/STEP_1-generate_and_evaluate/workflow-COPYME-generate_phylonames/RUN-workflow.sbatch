#!/bin/bash
#SBATCH --job-name=phylonames_step1
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --qos=YOUR_QOS
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=10
#SBATCH --mem=75gb
#SBATCH --time=2:00:00
#SBATCH --output=slurm_logs/phylonames_step1-%j.log

# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: SLURM wrapper for phylonames STEP 1
# Human: Eric Edsinger

################################################################################
# GIGANTIC Phylonames STEP 1 - SLURM Execution
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
# 3. Species list is loaded from (in priority order):
#    a. INPUT_user/species_list.txt  (workflow-level override, if present)
#    b. ../../../../INPUT_user/species_set/species_list.txt  (project-level default)
#
# FOR LOCAL MACHINES:
#   bash RUN-workflow.sh
#
################################################################################

mkdir -p slurm_logs
bash RUN-workflow.sh
