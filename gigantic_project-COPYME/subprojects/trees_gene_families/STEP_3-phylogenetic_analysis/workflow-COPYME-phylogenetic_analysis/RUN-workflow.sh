#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: Run STEP_3 phylogenetic analysis workflow locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_gene_families STEP_3 - Phylogenetic Analysis (Local)
################################################################################
#
# PURPOSE:
# Run the STEP_3 phylogenetic analysis workflow for ONE gene family.
# Each workflow copy processes a single gene family.
#
# USAGE:
#   1. Copy the template:
#      cp -r workflow-COPYME-phylogenetic_analysis workflow-RUN_01-phylogenetic_analysis
#   2. Edit phylogenetic_analysis_config.yaml (set gene_family name, choose tree methods)
#   3. Ensure STEP_2 has completed for this gene family
#   4. Run: bash RUN-workflow.sh
#
# FOR SLURM CLUSTERS:
#   sbatch RUN-workflow.sbatch
#
# OUTPUT:
# Results in OUTPUT_pipeline/1-output/ through 7-output/
# Trees and alignments copied to output_to_input/trees/<gene_family>/
#
################################################################################

echo "========================================================================"
echo "GIGANTIC trees_gene_families STEP_3 - Phylogenetic Analysis (Local)"
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
if [ ! -f "phylogenetic_analysis_config.yaml" ]; then
    echo "ERROR: Configuration file not found!"
    echo "Expected: phylogenetic_analysis_config.yaml"
    exit 1
fi
echo "  [OK] Configuration file found"

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
    echo "Results in OUTPUT_pipeline/1-output/ through 7-output/"
else
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "Check the logs above for error details."
fi
echo "========================================================================"
echo "Completed: $(date)"

exit $EXIT_CODE
