#!/bin/bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Run repository genomes pipeline locally with NextFlow
# Human: Eric Edsinger

################################################################################
# Repository Genomes Pipeline - Local Execution
################################################################################
#
# PURPOSE:
# Download genomes, annotations, and protein sequences from various external
# repositories, organize with GIGANTIC naming conventions, and extract T1
# proteomes.
#
# USAGE:
#   bash RUN_repository_genomes.sh
#
# FOR SLURM CLUSTERS:
#   sbatch RUN_repository_genomes.sbatch
#
# WHAT THIS DOES:
# 1. Downloads genome data from various repositories (per-species scripts)
# 2. Organizes and renames to Genus_species-repository_genomes convention
# 3. Extracts T1 (longest transcript per gene) proteomes (flexible approach)
# 4. Creates symlinks in output_to_input/ for downstream subprojects
#
# OUTPUT:
# T1 proteomes at: OUTPUT_pipeline/3-output/T1_proteomes/
#
# REQUIRES:
# - NextFlow (module load conda && conda activate ai_nextflow)
# - Python 3
# - gffread (only for species that need genome+annotation translation)
# - wget/curl (for downloading from repositories)
#
################################################################################

echo "========================================================================"
echo "Repository Genomes Pipeline (Local)"
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

# Check for gffread (needed for Path C species)
if command -v gffread &> /dev/null; then
    echo "gffread: $(which gffread)"
else
    echo "NOTE: gffread not found - species requiring genome+annotation translation will fail"
    echo "  To fix: module load gffread"
fi
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
