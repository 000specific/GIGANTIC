#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 26 | Purpose: Run STEP_3 workflow on SLURM
# Human: Eric Edsinger

################################################################################
# GIGANTIC genomesDB - STEP_3 Build BLAST Databases (SLURM)
################################################################################
#
# PURPOSE:
# Run the STEP_3 database building workflow on a SLURM cluster.
# Builds per-genome BLAST databases from standardized proteomes.
#
# USAGE:
#   sbatch RUN-workflow.sbatch
#
# BEFORE RUNNING:
# 1. Edit the SBATCH directives below (account, qos) for your cluster
# 2. Ensure STEP_2 is complete (provides standardized proteomes)
# 3. User should have edited species_selection_manifest.tsv (Include=YES/NO)
#
# FOR LOCAL MACHINES:
# Use the local version instead:
#   bash RUN-workflow.sh
#
################################################################################

#SBATCH --job-name=genomesDB_step3
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --qos=YOUR_QOS
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16gb
#SBATCH --time=2:00:00
#SBATCH --output=slurm_logs/step3_workflow-%j.log

################################################################################
# SLURM JOB EXECUTION
################################################################################

echo "========================================================================"
echo "GIGANTIC genomesDB STEP_3 Workflow (SLURM)"
echo "========================================================================"
echo ""
echo "Job ID: ${SLURM_JOB_ID}"
echo "Node: ${SLURM_NODELIST}"
echo "CPUs: ${SLURM_CPUS_PER_TASK}"
echo "Started: $(date)"
echo ""

# Create slurm_logs directory if it doesn't exist
mkdir -p slurm_logs

# Change to the directory where sbatch was invoked
cd "${SLURM_SUBMIT_DIR}"

# Load conda and activate environment
module load conda
conda activate ai_gigantic_genomesdb

# Verify tools are available
echo "Checking tools..."
echo "NextFlow version: $(nextflow -version 2>&1 | head -1 || echo 'version check failed')"
echo "makeblastdb version: $(makeblastdb -version 2>&1 | head -1 || echo 'version check failed')"
echo ""

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
