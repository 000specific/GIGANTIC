#!/bin/bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Run NCBI genomes pipeline locally with NextFlow
# Human: Eric Edsinger

################################################################################
# NCBI Genomes Pipeline - Local Execution
################################################################################
#
# PURPOSE:
# Download genomes, GFF3 annotations, and protein sequences from NCBI,
# organize with GIGANTIC naming conventions, and extract T1 proteomes.
#
# USAGE:
#   bash RUN_ncbi_genomes.sh
#
# FOR SLURM CLUSTERS:
#   sbatch RUN_ncbi_genomes.sbatch
#
# WHAT THIS DOES:
# 1. Downloads genome + GFF3 + protein data from NCBI (34 species, ~5-8 GB)
# 2. Unzips, organizes, and renames to Genus_species-ncbi_genomes convention
# 3. Extracts T1 (longest transcript per gene) proteomes using GFF3 mappings
# 4. Creates symlinks in output_to_input/ for downstream subprojects
#
# OUTPUT:
# T1 proteomes at: OUTPUT_pipeline/3-output/T1_proteomes/
#
# REQUIRES:
# - NextFlow (module load conda && conda activate ai_nextflow)
# - NCBI datasets CLI (conda activate ncbi_datasets -- loaded within pipeline)
# - Python 3
#
################################################################################

echo "========================================================================"
echo "NCBI Genomes Pipeline (Local)"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# Load required modules
module load conda 2>/dev/null || true

# Activate NextFlow environment
if conda activate ai_nextflow 2>/dev/null; then
    echo "Activated conda environment: ai_nextflow"
elif conda activate nextflow 2>/dev/null; then
    echo "Activated conda environment: nextflow"
else
    echo "WARNING: Could not activate NextFlow conda environment"
fi

# The download script needs the ncbi_datasets conda env.
# NextFlow runs scripts in subshells, so we need datasets CLI available.
# Check if datasets is available in the nextflow env or PATH.
if ! command -v datasets &> /dev/null; then
    echo ""
    echo "NOTE: NCBI datasets CLI not found in current environment."
    echo "The download step will activate ncbi_datasets conda env internally."
    echo "If downloads fail, ensure ncbi_datasets env exists:"
    echo "  conda activate ncbi_datasets && datasets --version"
    echo ""
fi

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

echo "NextFlow: $(which nextflow)"
echo "python3:  $(which python3)"
echo ""

# Ensure NextFlow can initialize (needed on network filesystems after clean wipe)
mkdir -p .nextflow

# Run NextFlow pipeline
echo "Running NextFlow pipeline..."
echo ""

nextflow run ai/main.nf

EXIT_CODE=$?

echo ""

echo "========================================================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "SUCCESS! Pipeline completed."
    echo ""
    echo "T1 proteomes: OUTPUT_pipeline/3-output/T1_proteomes/"
    echo ""
    echo "Species processed:"
    ls OUTPUT_pipeline/3-output/T1_proteomes/*.aa 2>/dev/null | while read f; do
        echo "  $(basename $f): $(grep -c '^>' $f) proteins"
    done
else
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "Check the logs above for error details."
fi
echo "========================================================================"
echo "Completed: $(date)"

exit $EXIT_CODE
