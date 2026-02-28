#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: Run STEP_1 RGS validation workflow locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_gene_families STEP_1 - RGS Validation (Local)
################################################################################
#
# PURPOSE:
# Validate a single RGS (Reference Gene Set) FASTA file before running STEP_2
# homolog discovery. Each workflow copy processes ONE gene family.
#
# USAGE:
#   1. Copy the template:
#      cp -r workflow-COPYME-validate_rgs workflow-RUN_01-validate_rgs
#   2. Edit rgs_config.yaml (set gene_family name and rgs_file)
#   3. Place your RGS FASTA file in INPUT_user/
#   4. Run: bash RUN-validate_rgs.sh
#
# FOR SLURM CLUSTERS:
#   sbatch RUN-validate_rgs.sbatch
#
# OUTPUT:
# Validated RGS file in OUTPUT_pipeline/1-output/
# Validated RGS copied to output_to_input/rgs_fastas/<gene_family>/
#
################################################################################

echo "========================================================================"
echo "GIGANTIC trees_gene_families STEP_1 - RGS Validation (Local)"
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

module load conda 2>/dev/null || true

if conda activate ai_gigantic_trees 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_trees"
else
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: NextFlow not found!"
        echo ""
        echo "Please ensure NextFlow is installed and available in your PATH."
        exit 1
    fi
    echo "Using NextFlow from PATH"
fi
echo ""

# ============================================================================
# Validate Prerequisites
# ============================================================================

echo "Validating prerequisites..."
echo ""

if [ ! -f "rgs_config.yaml" ]; then
    echo "ERROR: Configuration file not found!"
    echo "Expected: rgs_config.yaml"
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
    echo "Validated RGS file in OUTPUT_pipeline/1-output/"
else
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "Check the logs above for error details."
fi
echo "========================================================================"
echo "Completed: $(date)"

exit $EXIT_CODE
