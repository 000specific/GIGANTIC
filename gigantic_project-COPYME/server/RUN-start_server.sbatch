#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 April 02 | Purpose: Start GIGANTIC data server via SLURM
# Human: Eric Edsinger

################################################################################
# GIGANTIC Data Server - SLURM Submission
################################################################################
#
# PURPOSE:
# Submit the GIGANTIC data server as a long-running SLURM job.
# Serves files directly from subproject upload_to_server/ directories.
#
# USAGE:
#   sbatch RUN-start_server.sbatch
#
# AFTER SUBMITTING:
#   1. Check job status:  squeue -u $USER | grep gigantic
#   2. Find the node:     Check the SLURM log in logs/
#   3. SSH tunnel:        ssh -L PORT:NODE:PORT user@hpc.server
#   4. Open browser:      http://localhost:PORT/
#
# TO STOP:
#   scancel JOB_ID
#
################################################################################

# ---------------------------------------------------------------------------
# SLURM SETTINGS
# ---------------------------------------------------------------------------
# Edit these to match your HPC account.

#SBATCH --job-name=gigantic_server
#SBATCH --partition=hpg-default
#SBATCH --time=720:00:00
#SBATCH --mem=4gb
#SBATCH --cpus-per-task=1
#SBATCH --account=moroz
#SBATCH --qos=moroz
#SBATCH --output=logs/slurm_server_%j.log

# ---------------------------------------------------------------------------
# SETUP
# ---------------------------------------------------------------------------

# Script directory (server/)
# Use SLURM_SUBMIT_DIR (where sbatch was called from) since BASH_SOURCE
# does not resolve correctly inside SLURM jobs
SCRIPT_DIR="${SLURM_SUBMIT_DIR}"

# Create logs directory
mkdir -p "${SCRIPT_DIR}/logs"

echo "========================================================================"
echo "GIGANTIC Data Server - SLURM Job"
echo "========================================================================"
echo ""
echo "Job ID:    ${SLURM_JOB_ID}"
echo "Node:      $(hostname)"
echo "Started:   $(date)"
echo ""

# ---------------------------------------------------------------------------
# START SERVER
# ---------------------------------------------------------------------------

exec python3 "${SCRIPT_DIR}/ai/gigantic_server.py" \
    --config "${SCRIPT_DIR}/START_HERE-server_config.yaml" \
    --subprojects-dir "${SCRIPT_DIR}/../subprojects"
