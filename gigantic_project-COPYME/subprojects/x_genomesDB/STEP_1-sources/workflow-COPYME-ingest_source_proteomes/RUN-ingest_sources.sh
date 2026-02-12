#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 12 | Purpose: Run source proteome ingestion NextFlow pipeline locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC Source Proteome Ingestion Pipeline - Local Execution
################################################################################
#
# PURPOSE:
# Ingest user-provided proteome files into GIGANTIC by reading a manifest
# and copying/symlinking proteomes into the GIGANTIC structure.
#
# USAGE:
#   bash RUN-ingest_sources.sh
#
# BEFORE RUNNING:
# 1. Place your proteome files somewhere accessible (e.g., user_research/)
# 2. Create INPUT_user/source_manifest.tsv listing your proteome paths
#    (see INPUT_user/source_manifest_example.tsv for format)
# 3. Edit ingest_sources_config.yaml with your project settings
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN-ingest_sources.sbatch
#
# WHAT THIS DOES:
# 1. Validates that all source proteome files exist
# 2. Hard copies proteomes to OUTPUT_pipeline/1-output/proteomes/
# 3. Creates symlinks in STEP_1-sources/output_to_input/proteomes/
# 4. Writes an ingestion log for reproducibility
#
# OUTPUT:
# Proteomes will be available at:
#   ../../output_to_input/proteomes/  (symlinks for STEP_2)
#   OUTPUT_pipeline/1-output/proteomes/  (archived hard copies)
#
################################################################################

echo "========================================================================"
echo "GIGANTIC Source Proteome Ingestion Pipeline (Local)"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Activate GIGANTIC Environment
# ============================================================================
# Load conda module (required on HPC systems like HiPerGator)
module load conda 2>/dev/null || true

# Activate the genomesDB environment
# This environment is created by: bash RUN-setup_environments.sh (at project root)
if conda activate ai_gigantic_genomesdb 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_genomesdb"
else
    # Check if nextflow is already available in PATH
    if ! command -v nextflow &> /dev/null; then
        echo "WARNING: Environment 'ai_gigantic_genomesdb' not found!"
        echo ""
        echo "Checking if NextFlow is available in PATH..."
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
    echo ""
    echo "See INPUT_user/source_manifest_example.tsv for format:"
    echo "  species_name<TAB>proteome_path"
    echo ""
    echo "Example:"
    echo "  Homo_sapiens    /path/to/Homo_sapiens.fasta"
    echo "  Aplysia_californica    ../user_research/proteomes/Aplysia.aa"
    echo ""
    exit 1
fi

# Count proteomes in manifest (excluding comments and empty lines)
PROTEOME_COUNT=$(grep -v "^#" INPUT_user/source_manifest.tsv | grep -v "^$" | wc -l)
echo "Proteomes in manifest: ${PROTEOME_COUNT}"
echo ""

if [ "$PROTEOME_COUNT" -eq 0 ]; then
    echo "ERROR: No proteomes found in manifest!"
    echo "Please add proteome entries to INPUT_user/source_manifest.tsv"
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
    echo ""
    echo "Next step: Run STEP_2-standardize_and_evaluate workflow"
else
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "Check the logs above for error details."
fi
echo "========================================================================"
echo "Completed: $(date)"

exit $EXIT_CODE
