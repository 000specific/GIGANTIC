#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: Run STEP_1 RGS validation workflow locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_gene_families STEP_1 - RGS Validation (Local)
################################################################################
#
# PURPOSE:
# Validate RGS (Reference Gene Set) FASTA files before running STEP_2
# homolog discovery. Checks filename format, header format, duplicates,
# and sequence count consistency.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Place RGS FASTA files in INPUT_user/
# 2. Create INPUT_user/rgs_manifest.tsv:
#    gene_family_name<TAB>rgs_fasta_filename
# 3. Edit rgs_config.yaml if needed
#
# OUTPUT:
# Validated RGS files in OUTPUT_pipeline/<gene_family>/1-output/
# Validated RGS copied to output_to_input/rgs_sequences/<gene_family>/
#
################################################################################

echo "========================================================================"
echo "GIGANTIC trees_gene_families STEP_1 - RGS Validation (Local)"
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

module load conda 2>/dev/null || true

if conda activate ai_gigantic_genomesdb 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_genomesdb"
else
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: NextFlow not found!"
        echo ""
        echo "Please ensure NextFlow is installed and available in your PATH."
        exit 1
    fi
    echo "Using NextFlow from PATH"
fi
echo ""

# ============================================================================
# Validate Prerequisites
# ============================================================================

echo "Validating prerequisites..."
echo ""

if [ ! -f "rgs_config.yaml" ]; then
    echo "ERROR: Configuration file not found!"
    echo "Expected: rgs_config.yaml"
    exit 1
fi
echo "  [OK] Configuration file found"

if [ ! -f "INPUT_user/rgs_manifest.tsv" ]; then
    echo "ERROR: RGS manifest not found!"
    echo "Expected: INPUT_user/rgs_manifest.tsv"
    echo ""
    echo "Create a TSV file with columns: gene_family_name<TAB>rgs_fasta_filename"
    exit 1
fi
echo "  [OK] RGS manifest found"

# Check that RGS files referenced in manifest exist
MISSING=0
while IFS=$'\t' read -r family filename; do
    [[ "$family" =~ ^#.*$ || -z "$family" ]] && continue
    if [ ! -f "INPUT_user/${filename}" ]; then
        echo "  [MISSING] INPUT_user/${filename} (for ${family})"
        MISSING=$((MISSING + 1))
    fi
done < INPUT_user/rgs_manifest.tsv

if [ $MISSING -gt 0 ]; then
    echo ""
    echo "ERROR: ${MISSING} RGS file(s) missing from INPUT_user/. See above."
    exit 1
fi
echo "  [OK] All RGS files from manifest found"

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
    echo ""
    echo "Validated RGS files are in:"
    echo "  OUTPUT_pipeline/<gene_family>/1-output/"
    echo "  output_to_input/rgs_sequences/<gene_family>/"
else
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "Check the logs above for error details."
fi
echo "========================================================================"
echo "Completed: $(date)"

exit $EXIT_CODE
