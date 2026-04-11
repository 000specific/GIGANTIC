#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 April 10 | Purpose: Run gigantic_species_tree workflow on SLURM
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_species - BLOCK_gigantic_species_tree (SLURM)
################################################################################
#
# PURPOSE:
# Run the gigantic_species_tree workflow on a SLURM cluster.
# This is a lightweight job — the pipeline is just Newick parsing,
# clade-ID assignment, and file writing. Default SLURM resources are set
# modestly; tree visualization (ete3) may briefly spike memory on very
# large trees.
#
# USAGE:
#   sbatch RUN-workflow.sbatch
#
# BEFORE RUNNING:
# 1. Edit the SBATCH directives below (account, qos) for your cluster
# 2. Place your species tree in INPUT_user/species_tree.newick
# 3. Edit START_HERE-user_config.yaml (species_set_name)
# 4. See INPUT_user/README.md for the required species tree format
#
# FOR LOCAL MACHINES:
# Use the local version instead:
#   bash RUN-workflow.sh
#
################################################################################

#SBATCH --job-name=gigantic_species_tree
#SBATCH --account=YOUR_ACCOUNT        # <-- EDIT: Your cluster account
#SBATCH --qos=YOUR_QOS                # <-- EDIT: Your quality of service
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=16gb
#SBATCH --time=1:00:00
#SBATCH --output=slurm_logs/gigantic_species_tree-%j.log

################################################################################
# SLURM JOB EXECUTION
################################################################################

echo "========================================================================"
echo "GIGANTIC trees_species - BLOCK_gigantic_species_tree Workflow (SLURM)"
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
