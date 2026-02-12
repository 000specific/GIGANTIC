#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 12 | Purpose: Run source proteome ingestion NextFlow pipeline on SLURM
# Human: Eric Edsinger

################################################################################
# GIGANTIC Source Proteome Ingestion Pipeline - SLURM Execution
################################################################################
#
# PURPOSE:
# Ingest user-provided proteome files into GIGANTIC on a SLURM cluster.
#
# USAGE:
#   sbatch RUN-ingest_sources.sbatch
#
# BEFORE RUNNING:
# 1. Edit the SBATCH directives below (account, qos) for your cluster
# 2. Create INPUT_user/source_manifest.tsv listing your proteome paths
# 3. Edit ingest_sources_config.yaml with your project settings
#
# FOR LOCAL MACHINES:
# Use the local version instead:
#   bash RUN-ingest_sources.sh
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
echo "GIGANTIC Source Proteome Ingestion Pipeline (SLURM)"
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
# Activate GIGANTIC Environment
# ============================================================================
# Load conda module (required on HPC systems like HiPerGator)
module load conda 2>/dev/null || true

# Activate the genomesDB environment
if conda activate ai_gigantic_genomesdb 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_genomesdb"
else
    # Check if nextflow is already available in PATH
    if ! command -v nextflow &> /dev/null; then
        echo "WARNING: Environment 'ai_gigantic_genomesdb' not found!"
        echo ""
        # Try loading nextflow module (HiPerGator)
        module load nextflow 2>/dev/null || true
        if ! command -v nextflow &> /dev/null; then
            echo "ERROR: NextFlow not found!"
            echo ""
            echo "Please run the environment setup script first:"
            echo ""
            echo "  cd ../../../../  # Go to project root"
            echo "  bash RUN-setup_environments.sh"
            echo ""
            exit 1
        fi
    fi
    echo "Using NextFlow from PATH (environment not activated)"
fi
echo ""

# Check for source manifest
if [ ! -f "INPUT_user/source_manifest.tsv" ]; then
    echo "ERROR: Source manifest not found!"
    echo ""
    echo "Please create INPUT_user/source_manifest.tsv with your proteome paths."
    echo "See INPUT_user/source_manifest_example.tsv for format."
    exit 1
fi

# Count proteomes in manifest
PROTEOME_COUNT=$(grep -v "^#" INPUT_user/source_manifest.tsv | grep -v "^$" | wc -l)
echo "Proteomes in manifest: ${PROTEOME_COUNT}"
echo ""

if [ "$PROTEOME_COUNT" -eq 0 ]; then
    echo "ERROR: No proteomes found in manifest!"
    exit 1
fi

# Run NextFlow pipeline
echo "Running NextFlow pipeline..."
echo ""

nextflow run ai/main.nf

EXIT_CODE=$?

echo ""
echo "========================================================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "SUCCESS! Pipeline completed."
    echo ""
    echo "Proteomes are now available at:"
    echo "  - ../../output_to_input/proteomes/  (symlinks for STEP_2)"
    echo "  - OUTPUT_pipeline/1-output/proteomes/  (archived copies)"
else
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "Check the logs above for error details."
fi
echo "========================================================================"
echo "Job completed: $(date)"

exit $EXIT_CODE
