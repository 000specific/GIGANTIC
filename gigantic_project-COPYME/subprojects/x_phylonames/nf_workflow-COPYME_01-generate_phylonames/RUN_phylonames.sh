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
#   bash RUN_phylonames.sh
#
# BEFORE RUNNING:
# 1. Edit phylonames_config.yaml with your project settings
# 2. Edit INPUT_user/species_list.txt with your species
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN_phylonames.sbatch
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

# Check for NextFlow
if ! command -v nextflow &> /dev/null; then
    echo "ERROR: NextFlow not found!"
    echo ""
    echo "Please install NextFlow or load it via module:"
    echo "  module load conda"
    echo "  conda activate ai_nextflow"
    echo ""
    exit 1
fi

# Check for species list
if [ ! -f "INPUT_user/species_list.txt" ]; then
    echo "ERROR: Species list not found at INPUT_user/species_list.txt"
    echo ""
    echo "Please create this file with your species, one per line:"
    echo "  Homo_sapiens"
    echo "  Aplysia_californica"
    echo "  Octopus_bimaculoides"
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
