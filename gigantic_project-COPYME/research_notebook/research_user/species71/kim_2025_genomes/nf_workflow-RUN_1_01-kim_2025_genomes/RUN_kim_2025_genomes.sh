#!/bin/bash
# AI: Claude Code | Opus 4 | 2026 February 11 | Purpose: Run Kim et al. 2025 genome pipeline locally with NextFlow
# Human: Eric Edsinger

################################################################################
# Kim et al. 2025 Genome Pipeline - Local Execution
################################################################################
#
# PURPOSE:
# Download genomes + gene annotations from Kim et al. 2025, decompress,
# rename to Genus_species convention, and extract T1 proteomes.
#
# USAGE:
#   bash RUN_kim_2025_genomes.sh
#
# FOR SLURM CLUSTERS:
#   sbatch RUN_kim_2025_genomes.sbatch
#
# WHAT THIS DOES:
# 1. Downloads genome + gene annotation data from GitHub (~250 MB compressed)
# 2. Decompresses and renames to Genus_species-kim_2025 convention
# 3. Extracts T1 (longest transcript per gene) proteomes using gffread
#
# OUTPUT:
# T1 proteomes at: OUTPUT_pipeline/3-output/T1_proteomes/
#
# REQUIRES:
# - NextFlow (module load conda && conda activate ai_nextflow)
# - gffread (module load gffread)
# - git (for GitHub download)
#
################################################################################

echo "========================================================================"
echo "Kim et al. 2025 Genome Pipeline (Local)"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# Load required modules
module load gffread 2>/dev/null || true

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

# Check for gffread
if ! command -v gffread &> /dev/null; then
    echo "ERROR: gffread not found!"
    echo ""
    echo "Please load gffread:"
    echo "  module load gffread"
    echo ""
    exit 1
fi

echo "NextFlow: $(which nextflow)"
echo "gffread:  $(which gffread)"
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
