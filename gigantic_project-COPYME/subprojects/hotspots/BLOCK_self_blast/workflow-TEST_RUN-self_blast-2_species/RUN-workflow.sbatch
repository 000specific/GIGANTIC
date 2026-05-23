#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 May 04 | Purpose: SLURM wrapper for hotspots self-BLAST workflow
# Human: Eric Edsinger

################################################################################
# GIGANTIC hotspots - BLOCK_self_blast (SLURM)
################################################################################
#
# PURPOSE:
# SLURM wrapper that submits RUN-workflow.sh as a driver job. The driver
# itself spawns the per-chunk blastp tasks as a SLURM array on burst QOS
# (configured via START_HERE-user_config.yaml).
#
# USAGE:
#   sbatch RUN-workflow.sbatch
#
# BEFORE RUNNING:
# 1. Edit --account and --qos below for your cluster
# 2. Edit START_HERE-user_config.yaml (especially execution_mode: "slurm",
#    slurm_account, slurm_qos, slurm_burst_account, slurm_burst_qos)
# 3. Provide INPUT_user/gigantic_species_list.txt
#
################################################################################

#SBATCH --job-name=gigantic_hotspots_self_blast
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --qos=YOUR_QOS
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=30gb
#SBATCH --time=10-00:00:00
#SBATCH --output=slurm_logs/self_blast-%j.log

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
