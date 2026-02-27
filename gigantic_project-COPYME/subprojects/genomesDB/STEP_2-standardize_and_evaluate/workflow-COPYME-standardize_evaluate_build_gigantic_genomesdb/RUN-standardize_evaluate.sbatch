#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: Run STEP_2 workflow on SLURM
# Human: Eric Edsinger

################################################################################
# GIGANTIC genomesDB - STEP_2 Standardize and Evaluate (SLURM)
################################################################################
#
# PURPOSE:
# Run the STEP_2 standardization workflow on a SLURM cluster.
# This runs Scripts 001-006 (full standardization and evaluation pipeline).
#
# USAGE:
#   sbatch RUN-standardize_evaluate.sbatch
#
# BEFORE RUNNING:
# 1. Edit the SBATCH directives below (account, qos) for your cluster
# 2. Ensure STEP_1-sources is complete (provides source data)
# 3. Ensure phylonames subproject is complete (provides species naming)
# 4. Ensure INPUT_user/busco_lineages.txt exists for BUSCO evaluation
#
# FOR LOCAL MACHINES:
# Use the local version instead:
#   bash RUN-standardize_evaluate.sh
#
################################################################################

#SBATCH --job-name=genomesDB_step2
#SBATCH --account=YOUR_ACCOUNT        # <-- EDIT: Your cluster account
#SBATCH --qos=YOUR_QOS                # <-- EDIT: Your quality of service
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=100
#SBATCH --mem=700gb
#SBATCH --time=6:00:00
#SBATCH --output=slurm_logs/step2_workflow-%j.log

################################################################################
# SLURM JOB EXECUTION
################################################################################

echo "========================================================================"
echo "GIGANTIC genomesDB STEP_2 Workflow (SLURM)"
echo "========================================================================"
echo ""
echo "Job ID: ${SLURM_JOB_ID}"
echo "Node: ${SLURM_NODELIST}"
echo "Started: $(date)"
echo ""

# Create slurm_logs directory if it doesn't exist
mkdir -p slurm_logs

# Change to the directory where sbatch was invoked
cd "${SLURM_SUBMIT_DIR}"

# ============================================================================
# Run the main workflow script
# ============================================================================

bash RUN-standardize_evaluate.sh
EXIT_CODE=$?

echo ""
echo "========================================================================"
echo "Job completed: $(date)"
echo "Exit code: ${EXIT_CODE}"
echo "========================================================================"

exit $EXIT_CODE
