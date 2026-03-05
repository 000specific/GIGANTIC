#!/bin/bash
#SBATCH --job-name=one_direction_homologs
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --qos=YOUR_QOS
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=15gb
#SBATCH --time=4:00:00
#SBATCH --output=slurm_logs/one_direction_homologs-%j.log

# AI: Claude Code | Opus 4.6 | 2026 March 02 | Purpose: SLURM wrapper for DIAMOND NCBI nr search pipeline
# Human: Eric Edsinger

################################################################################
# GIGANTIC One-Direction Homologs Pipeline - SLURM Execution
################################################################################
#
# PURPOSE:
# Submit the DIAMOND NCBI nr search workflow as a SLURM job.
# This is a thin wrapper - all workflow logic is in RUN-workflow.sh.
#
# NOTE:
# This head job uses minimal resources. The compute-intensive DIAMOND searches
# are submitted by NextFlow as separate SLURM array jobs with their own resource
# allocation (configured in ai/nextflow.config).
#
# USAGE:
#   sbatch RUN-workflow.sbatch
#
# BEFORE RUNNING:
# 1. Edit the SBATCH directives above (account, qos) for your cluster
# 2. Edit diamond_ncbi_nr_config.yaml with your DIAMOND database path
# 3. Create INPUT_user/proteome_manifest.tsv with your species and proteome paths
#
# FOR LOCAL MACHINES:
#   bash RUN-workflow.sh
#
################################################################################

mkdir -p slurm_logs
bash RUN-workflow.sh
