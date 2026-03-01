#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: Run STEP_2 workflow on SLURM
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_gene_families STEP_2 - RBH/RBF Homolog Discovery (SLURM)
################################################################################
#
# PURPOSE:
# Run the STEP_2 homolog discovery workflow on a SLURM cluster.
#
# USAGE:
#   sbatch RUN-workflow.sbatch
#
# BEFORE RUNNING:
# 1. Edit the SBATCH directives below (account, qos) for your cluster
# 2. Edit rbh_rbf_homologs_config.yaml with your project settings
# 3. Ensure INPUT_user/ files are in place (rgs_manifest, species keeper list)
#
# FOR LOCAL MACHINES:
# Use the local version instead:
#   bash RUN-workflow.sh
#
################################################################################

#SBATCH --job-name=trees_step2
#SBATCH --account=YOUR_ACCOUNT        # <-- EDIT: Your cluster account
#SBATCH --qos=YOUR_QOS                # <-- EDIT: Your quality of service
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=100
#SBATCH --mem=700gb
#SBATCH --time=48:00:00
#SBATCH --output=slurm_logs/step2_workflow-%j.log

################################################################################
# SLURM JOB EXECUTION
################################################################################

echo "========================================================================"
echo "GIGANTIC trees_gene_families STEP_2 Workflow (SLURM)"
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
