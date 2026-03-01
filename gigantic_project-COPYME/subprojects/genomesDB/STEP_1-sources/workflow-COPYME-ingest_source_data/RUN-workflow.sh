#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 13 | Purpose: Run source data ingestion NextFlow pipeline
# Human: Eric Edsinger

################################################################################
# GIGANTIC Source Data Ingestion Pipeline - Local Execution
################################################################################
#
# PURPOSE:
# Ingest user-provided source data files (proteomes, genomes, GFFs)
# into GIGANTIC structure.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Place your source files somewhere accessible (e.g., user_research/)
# 2. Create INPUT_user/source_manifest.tsv listing your source data paths
#    (see INPUT_user/source_manifest_example.tsv for format)
# 3. Edit ingest_sources_config.yaml with your project settings
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN-workflow.sbatch
#
# WHAT THE WORKFLOW DOES (3 steps, each with visible output):
#   Step 1 -> OUTPUT_pipeline/1-output/  Validate manifest (check files exist)
#   Step 2 -> OUTPUT_pipeline/2-output/  Ingest data (hard copy files)
#   Step 3 -> OUTPUT_pipeline/3-output/  Create symlinks (for STEP_2)
#
################################################################################

echo "========================================================================"
echo "GIGANTIC Source Data Ingestion Pipeline"
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
module load conda 2>/dev/null || true

if conda activate ai_gigantic_genomesdb 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_genomesdb"
else
    if ! command -v nextflow &> /dev/null; then
        echo "WARNING: Environment 'ai_gigantic_genomesdb' not found!"
        echo ""
        module load nextflow 2>/dev/null || true
        if ! command -v nextflow &> /dev/null; then
            echo "ERROR: NextFlow not found!"
            echo ""
            echo "Please run the environment setup script first:"
            echo "  cd ../../../../  # Go to project root"
            echo "  bash RUN-setup_environments.sh"
            exit 1
        fi
    fi
    echo "Using NextFlow from PATH"
fi
echo ""

# ============================================================================
# Check for source manifest
# ============================================================================
if [ ! -f "INPUT_user/source_manifest.tsv" ]; then
    echo "ERROR: Source manifest not found!"
    echo ""
    echo "Please create INPUT_user/source_manifest.tsv with your source data paths."
    echo "See INPUT_user/source_manifest_example.tsv for format."
    exit 1
fi

SPECIES_COUNT=$(grep -v "^#" INPUT_user/source_manifest.tsv | grep -v "^$" | grep -v "^genus_species" | wc -l)
echo "Species in manifest: ${SPECIES_COUNT}"
echo ""

if [ "$SPECIES_COUNT" -eq 0 ]; then
    echo "ERROR: No species found in manifest!"
    exit 1
fi

# ============================================================================
# Run NextFlow pipeline (all 3 steps)
# ============================================================================
echo "Running NextFlow pipeline..."
echo ""

nextflow run ai/main.nf

NF_EXIT_CODE=$?

echo ""
if [ $NF_EXIT_CODE -ne 0 ]; then
    echo "========================================================================"
    echo "FAILED! NextFlow exited with code ${NF_EXIT_CODE}"
    echo "Check logs above for details."
    echo "========================================================================"
    exit $NF_EXIT_CODE
fi

echo "========================================================================"
echo "SUCCESS!"
echo ""
echo "Output:"
echo "  OUTPUT_pipeline/1-output/  Validation report"
echo "  OUTPUT_pipeline/2-output/  Ingested data"
echo "  OUTPUT_pipeline/3-output/  Symlink manifest"
echo ""
echo "Symlinks for STEP_2:"
echo "  ../../output_to_input/T1_proteomes/"
echo "  ../../output_to_input/genomes/"
echo "  ../../output_to_input/gene_annotations/"
echo ""
echo "Next step: Run STEP_2-standardize_and_evaluate workflow"
echo "========================================================================"
echo "Completed: $(date)"

exit 0
