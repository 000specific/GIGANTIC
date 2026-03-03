#!/bin/bash
#SBATCH --job-name=metapredict_annotations
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --qos=YOUR_QOS
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8gb
#SBATCH --time=24:00:00
#SBATCH --output=slurm_logs/metapredict_annotations-%j.log

# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: SLURM wrapper for MetaPredict pipeline
# Human: Eric Edsinger

################################################################################
# GIGANTIC MetaPredict Annotation - SLURM Execution
################################################################################
#
# PURPOSE:
# Submit the MetaPredict workflow as a SLURM job.
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
