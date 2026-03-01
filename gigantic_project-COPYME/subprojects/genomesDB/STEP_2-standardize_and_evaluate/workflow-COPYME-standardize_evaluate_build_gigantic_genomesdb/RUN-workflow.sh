#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: Run STEP_2 standardization workflow locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC genomesDB STEP_2 - Standardize and Evaluate (Local)
################################################################################
#
# PURPOSE:
# Run the STEP_2 standardization workflow on your local machine using NextFlow.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Edit standardize_evaluate_config.yaml with your project settings
# 2. Ensure STEP_1-sources is complete (provides proteomes, genomes, annotations)
# 3. Ensure phylonames subproject is complete (provides species naming)
# 4. Ensure INPUT_user/busco_lineages.txt exists for BUSCO evaluation
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN-workflow.sbatch
#
# WHAT THIS DOES:
# 1. Standardizes proteome filenames and FASTA headers with phylonames
# 2. Cleans proteome invalid residues (replaces '.' with 'X')
# 3. Creates phyloname-based symlinks for genomes and annotations
# 4. Calculates genome assembly statistics using gfastats
# 5. Runs BUSCO proteome completeness evaluation
# 6. Summarizes quality metrics and generates species manifest
#
# OUTPUT:
# Results in OUTPUT_pipeline/1-output through 6-output/
# Species manifest copied to ../../output_to_input/
#
################################################################################

echo "========================================================================"
echo "GIGANTIC genomesDB STEP_2 Pipeline (Local)"
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

# Activate the genomesdb environment
if conda activate ai_gigantic_genomesdb 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_genomesdb"
else
    # Check if nextflow is already available in PATH
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: Environment 'ai_gigantic_genomesdb' not found!"
        echo ""
        echo "Please run the environment setup script first:"
        echo ""
        echo "  cd ../../../  # Go to project root"
        echo "  bash RUN-setup_environments.sh"
        echo ""
        echo "Or create this environment manually:"
        echo "  mamba env create -f ../../../conda_environments/ai_gigantic_genomesdb.yml"
        echo ""
        exit 1
    fi
    echo "Using NextFlow from PATH (environment not activated)"
fi
echo ""

# ============================================================================
# Validate Prerequisites
# ============================================================================

echo "Validating prerequisites..."
echo ""

# Check config file exists
if [ ! -f "standardize_evaluate_config.yaml" ]; then
    echo "ERROR: Configuration file not found!"
    echo "Expected: standardize_evaluate_config.yaml"
    exit 1
fi
echo "  [OK] Configuration file found"

# Check BUSCO lineages manifest exists
if [ ! -f "INPUT_user/busco_lineages.txt" ]; then
    echo "WARNING: BUSCO lineage manifest not found"
    echo "Expected: INPUT_user/busco_lineages.txt"
    echo "BUSCO evaluation will be skipped."
fi

echo ""

# ============================================================================
# Run NextFlow Pipeline
# ============================================================================

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
echo "Completed: $(date)"

exit $EXIT_CODE
