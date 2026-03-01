#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 06 | Purpose: Run phylonames NextFlow pipeline locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC Phylonames Pipeline - Local Execution
################################################################################
#
# PURPOSE:
# Run the phylonames workflow on your local machine using NextFlow.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Edit phylonames_config.yaml with your project settings
# 2. Edit INPUT_gigantic/species_list.txt (at project root) with your species
#    OR edit INPUT_user/species_list.txt directly (workflow-specific)
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN-workflow.sbatch
#
# WHAT THIS DOES:
# 1. Downloads NCBI taxonomy database (~2GB, skipped if already exists)
# 2. Generates phylonames for all NCBI species (~5-10 minutes)
# 3. Creates your project-specific mapping file
#
# OUTPUT:
# Your mapping file will be at:
#   output_to_input/maps/[project_name]_map-genus_species_X_phylonames.tsv
#
################################################################################

echo "========================================================================"
echo "GIGANTIC Phylonames Pipeline (Local)"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# Path to project-level INPUT_gigantic (relative to this workflow)
INPUT_GIGANTIC="../../../INPUT_gigantic"

# Copy species list from INPUT_gigantic if it exists and has content
# This provides a single source of truth at project level while archiving
# a copy in INPUT_user/ for each workflow run
if [ -f "${INPUT_GIGANTIC}/species_list.txt" ]; then
    # Check if INPUT_gigantic species list has actual species (not just comments)
    GIGANTIC_SPECIES_COUNT=$(grep -v "^#" "${INPUT_GIGANTIC}/species_list.txt" | grep -v "^$" | wc -l)
    if [ "$GIGANTIC_SPECIES_COUNT" -gt 0 ]; then
        echo "Copying species list from INPUT_gigantic/ (project-wide source)..."
        cp "${INPUT_GIGANTIC}/species_list.txt" "INPUT_user/species_list.txt"
        echo "  Copied ${GIGANTIC_SPECIES_COUNT} species to INPUT_user/ for archival"
        echo ""
    fi
fi

# ============================================================================
# Activate GIGANTIC Environment
# ============================================================================
# Load conda module (required on HPC systems like HiPerGator)
module load conda 2>/dev/null || true

# Activate the phylonames environment
# This environment is created by: bash RUN-setup_environments.sh (at project root)
if conda activate ai_gigantic_phylonames 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_phylonames"
else
    # Check if nextflow is already available in PATH
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: Environment 'ai_gigantic_phylonames' not found!"
        echo ""
        echo "Please run the environment setup script first:"
        echo ""
        echo "  cd ../../../  # Go to project root"
        echo "  bash RUN-setup_environments.sh"
        echo ""
        echo "Or create this environment manually:"
        echo "  mamba env create -f ../../../conda_environments/ai_gigantic_phylonames.yml"
        echo ""
        exit 1
    fi
    echo "Using NextFlow from PATH (environment not activated)"
fi
echo ""

# Check for species list
if [ ! -f "INPUT_user/species_list.txt" ]; then
    echo "ERROR: Species list not found!"
    echo ""
    echo "Please add your species to one of these locations:"
    echo ""
    echo "  RECOMMENDED (project-wide):"
    echo "    INPUT_gigantic/species_list.txt  (at project root)"
    echo ""
    echo "  OR workflow-specific:"
    echo "    INPUT_user/species_list.txt  (in this workflow directory)"
    echo ""
    echo "Format: one species per line, Genus_species (e.g., Homo_sapiens)"
    echo ""
    exit 1
fi

# Show species count
SPECIES_COUNT=$(grep -v "^#" INPUT_user/species_list.txt | grep -v "^$" | wc -l)
echo "Species in your list: ${SPECIES_COUNT}"
echo ""

# Run NextFlow pipeline
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
