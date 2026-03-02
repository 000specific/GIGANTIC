#!/bin/bash
#SBATCH --job-name=genomesDB_step3
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --qos=YOUR_QOS
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16gb
#SBATCH --time=2:00:00
#SBATCH --output=slurm_logs/step3_workflow-%j.log

# AI: Claude Code | Opus 4.6 | 2026 March 02 | Purpose: SLURM wrapper for STEP_3 database building
# Human: Eric Edsinger

################################################################################
# GIGANTIC genomesDB STEP_3 - Build BLAST Databases (SLURM)
################################################################################
#
# PURPOSE:
# Submit the STEP_3 database building workflow as a SLURM job.
# This is a thin wrapper - all workflow logic is in RUN-workflow.sh.
#
# USAGE:
#   sbatch RUN-workflow.sbatch
#
# BEFORE RUNNING:
# 1. Edit the SBATCH directives above (account, qos) for your cluster
# 2. Ensure STEP_2 is complete (provides standardized proteomes)
# 3. User should have edited species_selection_manifest.tsv (Include=YES/NO)
#
# FOR LOCAL MACHINES:
#   bash RUN-workflow.sh
#
################################################################################

mkdir -p slurm_logs
bash RUN-workflow.sh
