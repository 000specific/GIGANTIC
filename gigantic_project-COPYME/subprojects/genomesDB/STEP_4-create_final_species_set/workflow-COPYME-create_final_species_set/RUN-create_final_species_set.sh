#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: Run STEP_4 final species set workflow locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC genomesDB STEP_4 - Create Final Species Set (Local)
################################################################################
#
# PURPOSE:
# Create the final species set for downstream subprojects by copying
# user-selected species from STEP_2 and STEP_3 to output_to_input/.
#
# USAGE:
#   bash RUN-create_final_species_set.sh
#
# BEFORE RUNNING:
# 1. Complete STEP_2 (standardize and evaluate all species)
# 2. Complete STEP_3 (create BLAST databases for all species)
# 3. Review STEP_2 quality metrics and decide which species to keep
# 4. Edit INPUT_user/selected_species.txt (or use all species by default)
# 5. Edit final_species_set_config.yaml with paths to STEP_2 and STEP_3 outputs
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN-create_final_species_set.sbatch
#
# WHAT THIS DOES:
# 1. Validates species selection against STEP_2 and STEP_3 outputs
# 2. Copies selected proteomes from STEP_2 with speciesN naming
# 3. Copies selected BLAST databases from STEP_3 with speciesN naming
# 4. Creates output_to_input/speciesN_gigantic_T1_proteomes/
# 5. Creates output_to_input/speciesN_gigantic_T1_blastp/
#
# OUTPUT:
# Results in OUTPUT_pipeline/1-output and 2-output/
# Final species set copied to ../../output_to_input/
#
################################################################################

echo "========================================================================"
echo "GIGANTIC genomesDB STEP_4 Pipeline (Local)"
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
if [ ! -f "final_species_set_config.yaml" ]; then
    echo "ERROR: Configuration file not found!"
    echo "Expected: final_species_set_config.yaml"
    exit 1
fi
echo "  [OK] Configuration file found"

# Check if selected_species.txt exists - if not, create default from STEP_2
if [ ! -f "INPUT_user/selected_species.txt" ]; then
    echo "  [INFO] No selected_species.txt found - will use all species from STEP_2"
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
