#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 05 | Purpose: SLURM submission wrapper for phylonames workflow
# Human: Eric Edsinger

################################################################################
# GIGANTIC Phylonames Workflow - SLURM Submission Script
################################################################################
#
# PURPOSE:
# This script submits the phylonames workflow to a SLURM cluster.
# It is a thin wrapper around RUN_phylonames.sh.
#
# USAGE:
#   sbatch SLURM_phylonames.sbatch
#
# BEFORE RUNNING:
# 1. Edit the SBATCH directives below for your cluster (account, qos, resources)
# 2. Edit INPUT_user/species_list.txt with your species
# 3. Optionally edit PROJECT_NAME in RUN_phylonames.sh
#
# LOCAL USERS:
# If you're running on a local machine (not a cluster), use:
#   bash RUN_phylonames.sh
#
################################################################################

#SBATCH --job-name=phylonames
#SBATCH --account=YOUR_ACCOUNT        # <-- EDIT: Your cluster account
#SBATCH --qos=YOUR_QOS                # <-- EDIT: Your quality of service
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8gb
#SBATCH --time=2:00:00
#SBATCH --output=slurm_logs/phylonames-%j.log

################################################################################
# SLURM JOB EXECUTION
################################################################################

echo "========================================================================"
echo "SLURM Job Information"
echo "========================================================================"
echo "Job ID: ${SLURM_JOB_ID}"
echo "Node: ${SLURM_NODELIST}"
echo "Started: $(date)"
echo ""

# Create slurm_logs directory if it doesn't exist
mkdir -p slurm_logs

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# Run the phylonames workflow
bash RUN_phylonames.sh
EXIT_CODE=$?

echo ""
echo "========================================================================"
echo "SLURM Job Complete"
echo "========================================================================"
echo "Exit code: ${EXIT_CODE}"
echo "Completed: $(date)"

exit ${EXIT_CODE}
