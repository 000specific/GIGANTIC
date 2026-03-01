#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: Run STEP_2 RBH/RBF homolog discovery workflow locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_gene_families STEP_2 - RBH/RBF Homolog Discovery (Local)
################################################################################
#
# PURPOSE:
# Run the STEP_2 homolog discovery workflow for ONE gene family.
# Each workflow copy processes a single gene family.
#
# USAGE:
#   1. Copy the template:
#      cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_01-rbh_rbf_homologs
#   2. Edit rbh_rbf_homologs_config.yaml (set gene_family name and rgs_file)
#   3. Place your RGS file and species keeper list in INPUT_user/
#   4. Run: bash RUN-workflow.sh
#
# FOR SLURM CLUSTERS:
#   sbatch RUN-workflow.sbatch
#
# OUTPUT:
# Results in OUTPUT_pipeline/1-output/ through 16-output/
# AGS files copied to output_to_input/ags_fastas/<gene_family>/
#
################################################################################

echo "========================================================================"
echo "GIGANTIC trees_gene_families STEP_2 - RBH/RBF Homolog Discovery (Local)"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Activate Environment
# ============================================================================

# Load conda module (required on HPC systems like HiPerGator)
module load conda 2>/dev/null || true

# Activate the environment with NextFlow
if conda activate ai_gigantic_trees_gene_families 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_trees_gene_families"
else
    # Check if nextflow is already available in PATH
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: NextFlow not found!"
        echo ""
        echo "Please ensure NextFlow is installed and available in your PATH."
        echo "Or activate a conda environment that includes NextFlow."
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
if [ ! -f "rbh_rbf_homologs_config.yaml" ]; then
    echo "ERROR: Configuration file not found!"
    echo "Expected: rbh_rbf_homologs_config.yaml"
    exit 1
fi
echo "  [OK] Configuration file found"

# Check species keeper list exists
if [ ! -f "INPUT_user/species_keeper_list.tsv" ]; then
    echo "ERROR: Species keeper list not found!"
    echo "Expected: INPUT_user/species_keeper_list.tsv"
    exit 1
fi
echo "  [OK] Species keeper list found"

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
    echo ""
    echo "Results in OUTPUT_pipeline/1-output/ through 16-output/"
else
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "Check the logs above for error details."
fi
echo "========================================================================"
echo "Completed: $(date)"

exit $EXIT_CODE
