#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: Run STEP_2 RBH/RBF homolog discovery workflow locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_gene_families STEP_2 - RBH/RBF Homolog Discovery (Local)
################################################################################
#
# PURPOSE:
# Run the STEP_2 homolog discovery workflow on your local machine using NextFlow.
#
# USAGE:
#   bash RUN-rbh_rbf_homologs.sh
#
# BEFORE RUNNING:
# 1. Edit rbh_rbf_homologs_config.yaml with your project settings
# 2. Place your RGS manifest in INPUT_user/rgs_manifest.tsv
# 3. Place your species keeper list in INPUT_user/species_keeper_list.tsv
# 4. Place your RGS species map in INPUT_user/rgs_species_map.tsv (if needed)
# 5. Ensure BLAST databases are available (from genomesDB subproject)
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN-rbh_rbf_homologs.sbatch
#
# WHAT THIS DOES:
# 1.  Lists available BLAST databases
# 2.  BLASTs RGS against project database
# 3.  Extracts candidate gene sequences (CGS)
# 4.  BLASTs RGS against RGS source genomes
# 5.  Prepares reciprocal BLAST databases
# 6.  Runs reciprocal BLAST
# 7.  Extracts reciprocal best hits (RBH/RBF)
# 8.  Filters by species keeper list
# 9.  Remaps identifiers to GIGANTIC phylonames
# 10. Concatenates RGS + CGS into final AGS
#
# OUTPUT:
# Results in OUTPUT_pipeline/<gene_family>/1-output through 16-output/
# AGS files copied to output_to_input/homolog_sequences/<gene_family>/
#
################################################################################

echo "========================================================================"
echo "GIGANTIC trees_gene_families STEP_2 - RBH/RBF Homolog Discovery (Local)"
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
if [ ! -f "rbh_rbf_homologs_config.yaml" ]; then
    echo "ERROR: Configuration file not found!"
    echo "Expected: rbh_rbf_homologs_config.yaml"
    exit 1
fi
echo "  [OK] Configuration file found"

# Check RGS manifest exists
if [ ! -f "INPUT_user/rgs_manifest.tsv" ]; then
    echo "ERROR: RGS manifest not found!"
    echo "Expected: INPUT_user/rgs_manifest.tsv"
    echo ""
    echo "Create a TSV file with columns: gene_family_name<TAB>rgs_fasta_filename"
    exit 1
fi
echo "  [OK] RGS manifest found"

# Check species keeper list exists
if [ ! -f "INPUT_user/species_keeper_list.tsv" ]; then
    echo "ERROR: Species keeper list not found!"
    echo "Expected: INPUT_user/species_keeper_list.tsv"
    exit 1
fi
echo "  [OK] Species keeper list found"

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
