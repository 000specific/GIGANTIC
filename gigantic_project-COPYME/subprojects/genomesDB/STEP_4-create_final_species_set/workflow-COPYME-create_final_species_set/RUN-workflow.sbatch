#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: Run STEP_4 workflow on SLURM
# Human: Eric Edsinger

################################################################################
# GIGANTIC genomesDB - STEP_4 Create Final Species Set (SLURM)
################################################################################
#
# PURPOSE:
# Run the STEP_4 workflow on a SLURM cluster.
# This is a lightweight job - just copying files based on user selection.
#
# USAGE:
#   sbatch RUN-workflow.sbatch
#
# BEFORE RUNNING:
# 1. Edit the SBATCH directives below (account, qos) for your cluster
# 2. Ensure STEP_2 and STEP_3 are complete
# 3. Edit INPUT_user/selected_species.txt with your species selection
#
# FOR LOCAL MACHINES:
# Use the local version instead:
#   bash RUN-workflow.sh
#
################################################################################

#SBATCH --job-name=genomesDB_step4
#SBATCH --account=YOUR_ACCOUNT        # <-- EDIT: Your cluster account
#SBATCH --qos=YOUR_QOS                # <-- EDIT: Your quality of service
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16gb
#SBATCH --time=1:00:00
#SBATCH --output=slurm_logs/step4_workflow-%j.log

################################################################################
# SLURM JOB EXECUTION
################################################################################

echo "========================================================================"
echo "GIGANTIC genomesDB STEP_4 Workflow (SLURM)"
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

bash RUN-workflow.sh
EXIT_CODE=$?

echo ""
echo "========================================================================"
echo "Job completed: $(date)"
echo "Exit code: ${EXIT_CODE}"
echo "========================================================================"

exit $EXIT_CODE
