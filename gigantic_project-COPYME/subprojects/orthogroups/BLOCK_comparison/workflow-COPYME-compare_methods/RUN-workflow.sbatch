#!/bin/bash
#SBATCH --job-name=compare_orthogroups
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --qos=YOUR_QOS
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8gb
#SBATCH --time=2:00:00
#SBATCH --output=slurm_logs/comparison-%j.log

# AI: Claude Code | Opus 4.6 | 2026 March 02 | Purpose: SLURM wrapper for comparison pipeline
# Human: Eric Edsinger

################################################################################
# GIGANTIC Cross-Method Orthogroup Comparison - SLURM Execution
################################################################################
#
# PURPOSE:
# Submit the cross-method comparison workflow as a SLURM job.
# This is a thin wrapper - all workflow logic is in RUN-workflow.sh.
#
# USAGE:
#   sbatch RUN-workflow.sbatch
#
# BEFORE RUNNING:
# 1. Edit the SBATCH directives above (account, qos) for your cluster
# 2. Ensure at least 2 of: orthofinder, orthohmm, broccoli have results
#
# FOR LOCAL MACHINES:
#   bash RUN-workflow.sh
#
################################################################################

mkdir -p slurm_logs
bash RUN-workflow.sh
