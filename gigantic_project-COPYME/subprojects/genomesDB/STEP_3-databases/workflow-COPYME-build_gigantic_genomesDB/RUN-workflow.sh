#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 26 | Purpose: Run STEP_3 database building workflow
# Human: Eric Edsinger

################################################################################
# GIGANTIC genomesDB STEP_3 - Build BLAST Databases (Local)
################################################################################
#
# PURPOSE:
# Build per-genome BLAST databases from standardized proteomes.
# Each species gets its own individual BLAST database.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Ensure STEP_2-standardize_and_evaluate is complete
# 2. User should have edited the species_selection_manifest.tsv (Include=YES/NO)
# 3. BLAST+ tools must be available (module load blast or conda environment)
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN-workflow.sbatch
#
# OUTPUTS:
# - Per-genome BLAST databases in OUTPUT_pipeline/2-output/gigantic-T1-blastp/
# - Databases also copied to output_to_input/gigantic-T1-blastp/ for downstream use
#
################################################################################

set -e

echo "========================================================================"
echo "GIGANTIC genomesDB STEP_3 - Build BLAST Databases"
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
module load conda 2>/dev/null || true

if conda activate ai_gigantic_genomesdb 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_genomesdb"
else
    # Check if makeblastdb is available
    if ! command -v makeblastdb &> /dev/null; then
        echo "WARNING: makeblastdb not found in PATH."
        echo "Attempting to load BLAST+ module..."
        module load blast 2>/dev/null || true

        if ! command -v makeblastdb &> /dev/null; then
            echo "ERROR: makeblastdb still not found!"
            echo "Please ensure BLAST+ tools are available."
            echo ""
            echo "Options:"
            echo "  1. module load blast"
            echo "  2. conda activate ai_gigantic_genomesdb"
            echo "  3. Install BLAST+ and add to PATH"
            exit 1
        fi
    fi
    echo "Using makeblastdb from PATH"
fi

echo ""

# ============================================================================
# Check for species selection manifest
# ============================================================================
MANIFEST_PATH="../STEP_2-standardize_and_evaluate/output_to_input/species_selection_manifest.tsv"

if [ ! -f "${MANIFEST_PATH}" ]; then
    echo "ERROR: Species selection manifest not found!"
    echo ""
    echo "Expected location:"
    echo "  ${MANIFEST_PATH}"
    echo ""
    echo "Please ensure STEP_2 is complete and species_selection_manifest.tsv exists."
    exit 1
fi

TOTAL_SPECIES=$(tail -n +2 "${MANIFEST_PATH}" | grep -v "^#" | wc -l)
INCLUDE_YES=$(tail -n +2 "${MANIFEST_PATH}" | grep -v "^#" | grep -i "YES" | wc -l || echo 0)

echo "Species selection manifest found: ${MANIFEST_PATH}"
echo "  Total species: ${TOTAL_SPECIES}"
echo "  Include=YES: ${INCLUDE_YES}"
echo ""

if [ "${INCLUDE_YES}" -eq 0 ]; then
    echo "ERROR: No species have Include=YES in the manifest!"
    echo "Please edit the manifest and set Include=YES for species to include."
    exit 1
fi

# ============================================================================
# Run Script 001: Filter species manifest
# ============================================================================
echo "========================================================================"
echo "Step 1: Filter species manifest (Include=YES only)"
echo "========================================================================"
echo ""

python3 ai/scripts/001_ai-python-filter_species_manifest.py \
    --input-manifest "${MANIFEST_PATH}" \
    --output-dir OUTPUT_pipeline/1-output

echo ""

# ============================================================================
# Run Script 002: Build per-genome BLAST databases
# ============================================================================
echo "========================================================================"
echo "Step 2: Build per-genome BLAST databases"
echo "========================================================================"
echo ""

python3 ai/scripts/002_ai-python-build_per_genome_blastdbs.py \
    --filtered-manifest OUTPUT_pipeline/1-output/1_ai-filtered_species_manifest.tsv \
    --proteomes-dir ../STEP_2-standardize_and_evaluate/output_to_input/gigantic_proteomes \
    --output-dir OUTPUT_pipeline/2-output \
    --output-to-input-dir ../../output_to_input \
    --database-name gigantic-T1-blastp \
    --parallel 4

echo ""

# ============================================================================
# Complete
# ============================================================================
echo "========================================================================"
echo "COMPLETE"
echo "========================================================================"
echo "Finished: $(date)"
echo ""
echo "BLAST databases created:"
echo "  OUTPUT_pipeline/2-output/gigantic-T1-blastp/"
echo ""
echo "Also available for downstream subprojects at:"
echo "  output_to_input/gigantic-T1-blastp/"
echo ""
echo "To use with blastp:"
echo "  blastp -db OUTPUT_pipeline/2-output/gigantic-T1-blastp/PHYLONAME-proteome.aa -query sequences.fasta"
echo ""
