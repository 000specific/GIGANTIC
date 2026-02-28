#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 27 | Purpose: Run OrthoHMM workflow locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC Orthogroups - OrthoHMM Workflow (Local)
################################################################################
#
# PURPOSE:
# Run the complete OrthoHMM clustering workflow to identify orthogroups
# across species proteomes.
#
# USAGE:
#   bash RUN-orthohmm.sh
#
# BEFORE RUNNING:
# 1. Complete genomesDB STEP_2 (provides proteomes in output_to_input/)
# 2. Edit orthohmm_config.yaml:
#    - Set correct path to proteomes (speciesN_gigantic_T1_proteomes)
#    - Adjust OrthoHMM parameters if needed
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN-orthohmm.sbatch
#
# WHAT THIS DOES:
# 1. Validates proteomes from genomesDB
# 2. Converts FASTA headers to short IDs for OrthoHMM
# 3. Runs OrthoHMM clustering (computationally intensive)
# 4. Generates summary statistics
# 5. Performs per-species QC analysis
# 6. Restores full GIGANTIC identifiers
#
# OUTPUT:
# Results in OUTPUT_pipeline/1-output through 6-output/
# Key files copied to ../../output_to_input/
#
################################################################################

echo "========================================================================"
echo "GIGANTIC Orthogroups OrthoHMM Workflow (Local)"
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

# Activate the orthogroups environment
if conda activate ai_gigantic_orthogroups 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_orthogroups"
else
    # Check if nextflow and orthohmm are already available in PATH
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: Environment 'ai_gigantic_orthogroups' not found!"
        echo ""
        echo "Please ensure the environment is set up with:"
        echo "  - nextflow"
        echo "  - orthohmm"
        echo "  - python3"
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
if [ ! -f "orthohmm_config.yaml" ]; then
    echo "ERROR: Configuration file not found!"
    echo "Expected: orthohmm_config.yaml"
    exit 1
fi
echo "  [OK] Configuration file found"

# Check that orthohmm is available
if ! command -v orthohmm &> /dev/null; then
    echo "WARNING: orthohmm command not found in current environment"
    echo "Process 003 will fail unless OrthoHMM is installed."
    echo ""
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
