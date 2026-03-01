#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 13 | Purpose: Run source data ingestion NextFlow pipeline on SLURM
# Human: Eric Edsinger

################################################################################
# GIGANTIC Source Data Ingestion Pipeline - SLURM Execution
################################################################################
#
# PURPOSE:
# Ingest user-provided source data files (proteomes, genomes, GFFs)
# into GIGANTIC on a SLURM cluster.
#
# USAGE:
#   sbatch RUN-workflow.sbatch
#
# BEFORE RUNNING:
# 1. Edit the SBATCH directives below (account, qos) for your cluster
# 2. Create INPUT_user/source_manifest.tsv listing your source data paths
# 3. Edit ingest_sources_config.yaml with your project settings
#
# FOR LOCAL MACHINES:
# Use the local version instead:
#   bash RUN-workflow.sh
#
################################################################################

#SBATCH --job-name=ingest_sources
#SBATCH --account=YOUR_ACCOUNT        # <-- EDIT: Your cluster account
#SBATCH --qos=YOUR_QOS                # <-- EDIT: Your quality of service
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4gb
#SBATCH --time=1:00:00
#SBATCH --output=slurm_logs/ingest_sources-%j.log

################################################################################
# SLURM JOB EXECUTION
################################################################################

echo "========================================================================"
echo "GIGANTIC Source Data Ingestion Pipeline (SLURM)"
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
# Run the main workflow script (handles environment, validation, execution)
# ============================================================================

bash RUN-workflow.sh
EXIT_CODE=$?

echo ""
echo "========================================================================"
echo "Job completed: $(date)"
echo "Exit code: ${EXIT_CODE}"
echo "========================================================================"

exit $EXIT_CODE
