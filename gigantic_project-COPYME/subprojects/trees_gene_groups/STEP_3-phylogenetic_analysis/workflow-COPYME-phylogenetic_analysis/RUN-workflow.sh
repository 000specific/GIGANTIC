#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: Run STEP_3 phylogenetic analysis workflow locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_gene_families STEP_3 - Phylogenetic Analysis (Local)
################################################################################
#
# PURPOSE:
# Run the STEP_3 phylogenetic analysis workflow on your local machine using NextFlow.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Ensure STEP_2 has completed (AGS files in output_to_input/)
# 2. Edit phylogenetic_analysis_config.yaml with your settings
# 3. Place your RGS manifest in INPUT_user/rgs_manifest.tsv
# 4. Choose tree-building methods in config (tree_methods section)
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN-workflow.sbatch
#
# WHAT THIS DOES:
# 1. Stages AGS sequences from STEP_2
# 2. Cleans sequences for alignment
# 3. Runs MAFFT multiple sequence alignment
# 4. Trims alignment with ClipKit
# 5. Builds phylogenetic trees (configurable: FastTree, IQ-TREE, etc.)
# 6. Generates human-friendly tree visualizations
# 7. Generates computer-vision tree visualizations
# 8. Exports results to output_to_input/
#
# OUTPUT:
# Results in OUTPUT_pipeline/<gene_family>/1-output through 7-output/
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
if conda activate ai_gigantic_genomesdb 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_genomesdb"
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

# Check RGS manifest exists
if [ ! -f "INPUT_user/rgs_manifest.tsv" ]; then
    echo "ERROR: RGS manifest not found!"
    echo "Expected: INPUT_user/rgs_manifest.tsv"
    echo ""
    echo "Create a TSV file with gene family names (same as used in STEP_2)."
    exit 1
fi
echo "  [OK] RGS manifest found"

# Check STEP_2 output exists
STEP2_DIR=$(grep "step2_homolog_sequences_dir" phylogenetic_analysis_config.yaml | head -1 | sed 's/.*: *"\(.*\)"/\1/')
if [ -n "${STEP2_DIR}" ] && [ -d "${STEP2_DIR}" ]; then
    echo "  [OK] STEP_2 output directory found: ${STEP2_DIR}"
elif [ -d "../../STEP_2-homolog_discovery/output_to_input/homolog_sequences" ]; then
    echo "  [OK] STEP_2 output directory found (default location)"
else
    echo "  [WARNING] STEP_2 output directory not found. Ensure STEP_2 has completed."
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
