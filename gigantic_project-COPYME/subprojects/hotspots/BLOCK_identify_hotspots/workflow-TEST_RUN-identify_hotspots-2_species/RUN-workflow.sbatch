#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 May 04 | Purpose: SLURM wrapper for hotspots BLOCK_identify_hotspots
# Human: Eric Edsinger

################################################################################
# GIGANTIC hotspots - BLOCK_identify_hotspots (SLURM)
################################################################################
#
# PURPOSE:
# SLURM wrapper that submits RUN-workflow.sh as a driver job. The per-species
# hotspot calls are typically light enough to run with execution_mode: "local"
# inside a single driver job; this SBATCH wrapper just packages the run as a
# cluster job for unattended execution.
#
# USAGE:
#   sbatch RUN-workflow.sbatch
#
# BEFORE RUNNING:
# 1. Edit --account and --qos for your cluster
# 2. Confirm START_HERE-user_config.yaml is configured
# 3. BLOCK_self_blast must have completed
# 4. User-provided gene-coordinate TSVs in inputs.gene_coordinates_dir
#
################################################################################

#SBATCH --job-name=gigantic_hotspots_identify
#SBATCH --account=moroz
#SBATCH --qos=moroz
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=30gb
#SBATCH --time=8:00:00
#SBATCH --output=slurm_logs/identify_hotspots-%j.log

mkdir -p slurm_logs

echo "SLURM Job ID: ${SLURM_JOB_ID}"
echo "Running on: $(hostname)"
echo "Started: $(date)"
echo ""

bash RUN-workflow.sh

EXIT_CODE=$?

echo ""
echo "SLURM job completed with exit code: ${EXIT_CODE}"
echo "Finished: $(date)"

exit $EXIT_CODE
