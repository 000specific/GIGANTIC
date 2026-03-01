#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 01 | Purpose: Run DIAMOND NCBI nr search pipeline on SLURM
# Human: Eric Edsinger

################################################################################
# GIGANTIC One-Direction Homologs Pipeline - SLURM Execution
################################################################################
#
# PURPOSE:
# Run the DIAMOND NCBI nr search workflow on a SLURM cluster using NextFlow.
# This is the head job only - NextFlow will submit DIAMOND search jobs separately.
#
# USAGE:
#   sbatch RUN-workflow.sbatch
#
# BEFORE RUNNING:
# 1. Edit the SBATCH directives below (account, qos) for your cluster
# 2. Edit diamond_ncbi_nr_config.yaml with your DIAMOND database path
# 3. Create INPUT_user/proteome_manifest.tsv with your species and proteome paths
#
# FOR LOCAL MACHINES:
# Use the local version instead:
#   bash RUN-workflow.sh
#
# NOTE:
# This head job uses minimal resources. The compute-intensive DIAMOND searches
# are submitted by NextFlow as separate SLURM array jobs with their own resource
# allocation (configured in ai/nextflow.config).
#
################################################################################

#SBATCH --job-name=one_direction_homologs
#SBATCH --account=YOUR_ACCOUNT        # <-- EDIT: Your cluster account
#SBATCH --qos=YOUR_QOS                # <-- EDIT: Your quality of service
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8gb
#SBATCH --time=4:00:00
#SBATCH --output=slurm_logs/one_direction_homologs-%j.log

################################################################################
# SLURM JOB EXECUTION
################################################################################

echo "========================================================================"
echo "GIGANTIC One-Direction Homologs Pipeline (SLURM)"
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

# Path to project-level INPUT_gigantic (relative to this workflow)
INPUT_GIGANTIC="../../../INPUT_gigantic"

# Copy proteome manifest from INPUT_gigantic if it exists
if [ -f "${INPUT_GIGANTIC}/proteome_manifest.tsv" ]; then
    MANIFEST_LINES=$(grep -v "^#" "${INPUT_GIGANTIC}/proteome_manifest.tsv" | grep -v "^$" | wc -l)
    if [ "$MANIFEST_LINES" -gt 0 ]; then
        echo "Copying proteome manifest from INPUT_gigantic/ (project-wide source)..."
        cp "${INPUT_GIGANTIC}/proteome_manifest.tsv" "INPUT_user/proteome_manifest.tsv"
        echo "  Copied manifest with ${MANIFEST_LINES} entries to INPUT_user/ for archival"
        echo ""
    fi
fi

# ============================================================================
# Activate GIGANTIC Environment
# ============================================================================
module load conda 2>/dev/null || true

if conda activate ai_gigantic_one_direction_homologs 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_one_direction_homologs"
else
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: Environment 'ai_gigantic_one_direction_homologs' not found!"
        echo ""
        echo "Please run the environment setup script first:"
        echo ""
        echo "  cd ../../../  # Go to project root"
        echo "  bash RUN-setup_environments.sh"
        echo ""
        echo "Or create this environment manually:"
        echo "  mamba env create -f ../../../conda_environments/ai_gigantic_one_direction_homologs.yml"
        echo ""
        exit 1
    fi
    echo "Using NextFlow from PATH (environment not activated)"
fi
echo ""

# Check for proteome manifest
if [ ! -f "INPUT_user/proteome_manifest.tsv" ]; then
    echo "ERROR: Proteome manifest not found!"
    echo ""
    echo "Please create INPUT_user/proteome_manifest.tsv"
    echo "See INPUT_user/proteome_manifest_example.tsv for format."
    exit 1
fi

# Show manifest summary
SPECIES_COUNT=$(grep -v "^#" INPUT_user/proteome_manifest.tsv | grep -v "^$" | tail -n +2 | wc -l)
echo "Species in manifest: ${SPECIES_COUNT}"
echo ""

# Run NextFlow pipeline
echo "Running NextFlow pipeline..."
echo ""

nextflow run ai/main.nf

EXIT_CODE=$?

echo ""
echo "========================================================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "SUCCESS! Pipeline completed."
else
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "Check the logs above for error details."
fi
echo "========================================================================"
echo "Job completed: $(date)"

exit $EXIT_CODE
