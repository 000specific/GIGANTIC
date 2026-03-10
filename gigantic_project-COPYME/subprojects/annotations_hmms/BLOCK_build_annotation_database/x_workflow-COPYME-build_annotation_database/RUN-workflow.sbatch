#!/bin/bash
#SBATCH --job-name=build_annotation_database
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --qos=YOUR_QOS
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32gb
#SBATCH --time=12:00:00
#SBATCH --output=slurm_logs/build_annotation_database-%j.log

# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: SLURM wrapper for annotation database builder pipeline
# Human: Eric Edsinger

################################################################################
# GIGANTIC Annotation Database Builder - SLURM Execution
################################################################################
#
# PURPOSE:
# Submit the annotation database builder workflow as a SLURM job.
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
