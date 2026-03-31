#!/bin/bash
#SBATCH --job-name=compare_orthogroups
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --qos=YOUR_QOS
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=32gb
#SBATCH --time=4:00:00
#SBATCH --output=slurm_logs/comparison-%j.log

# AI: Claude Code | Opus 4.6 | 2026 March 30 | Purpose: SLURM wrapper for clustering comparison pipeline
# Human: Eric Edsinger

################################################################################
# GIGANTIC Orthogroup Clustering Comparison - SLURM Execution
################################################################################
#
# PURPOSE:
# Submit the clustering comparison workflow as a SLURM job.
# This is a thin wrapper - all workflow logic is in RUN-workflow.sh.
#
# USAGE:
#   sbatch SLURM_workflow.sbatch
#
# BEFORE RUNNING:
# 1. Edit the SBATCH directives above (account, qos) for your cluster
# 2. Create and edit INPUT_user/clustering_manifest.tsv
#
# FOR LOCAL MACHINES:
#   bash RUN-workflow.sh
#
################################################################################

mkdir -p slurm_logs
bash RUN-workflow.sh
