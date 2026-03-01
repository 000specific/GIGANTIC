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
# Validated RGS symlinked to output_to_input/ (by RUN-workflow.sh)
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

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "========================================================================"
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "Check the logs above for error details."
    echo "========================================================================"
    exit $EXIT_CODE
fi

# ============================================================================
# Create symlinks for output_to_input directories
# ============================================================================
# Real files live in OUTPUT_pipeline/<gene_family>/1-output/ (created by
# NextFlow above). Symlinks are created in two locations:
#   1. ../output_to_input/  (STEP-level, for downstream STEPs)
#   2. ai/output_to_input/  (archival, with this workflow run)
#
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
# ============================================================================

echo ""
echo "Creating symlinks for downstream workflows..."

WORKFLOW_NAME=$(basename "${SCRIPT_DIR}")

# --- STEP-level output_to_input ---
STEP_SHARED_DIR="../output_to_input"

# --- Workflow-level ai/output_to_input (archival) ---
WORKFLOW_SHARED_DIR="ai/output_to_input"

# Iterate over gene families discovered in OUTPUT_pipeline/
for gene_family_dir in OUTPUT_pipeline/*/; do
    GENE_FAMILY=$(basename "$gene_family_dir")
    [ "$GENE_FAMILY" = "*" ] && continue

    # STEP-level symlinks
    mkdir -p "${STEP_SHARED_DIR}/rgs_sequences/${GENE_FAMILY}"
    find "${STEP_SHARED_DIR}/rgs_sequences/${GENE_FAMILY}" -type l -delete 2>/dev/null

    for rgs_file in "OUTPUT_pipeline/${GENE_FAMILY}/1-output/1_ai-RGS-${GENE_FAMILY}-validated.aa"; do
        if [ -f "$rgs_file" ]; then
            filename=$(basename "$rgs_file")
            ln -sf "../../../${WORKFLOW_NAME}/${rgs_file}" \
                "${STEP_SHARED_DIR}/rgs_sequences/${GENE_FAMILY}/${filename}"
        fi
    done

    # Workflow-level archival symlinks
    mkdir -p "${WORKFLOW_SHARED_DIR}/rgs_sequences/${GENE_FAMILY}"
    find "${WORKFLOW_SHARED_DIR}/rgs_sequences/${GENE_FAMILY}" -type l -delete 2>/dev/null

    for rgs_file in "OUTPUT_pipeline/${GENE_FAMILY}/1-output/1_ai-RGS-${GENE_FAMILY}-validated.aa"; do
        if [ -f "$rgs_file" ]; then
            filename=$(basename "$rgs_file")
            ln -sf "../../../../${rgs_file}" \
                "${WORKFLOW_SHARED_DIR}/rgs_sequences/${GENE_FAMILY}/${filename}"
        fi
    done

    echo "  ${GENE_FAMILY}: symlinks created"
done

echo "  STEP output_to_input/ -> symlinks created"
echo "  Workflow ai/output_to_input/ -> symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! STEP_1 pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/<gene_family>/1-output/"
echo ""
echo "Downstream symlinks:"
echo "  ../output_to_input/rgs_sequences/<gene_family>/  (for downstream STEPs)"
echo "  ai/output_to_input/rgs_sequences/<gene_family>/  (archival with this run)"
echo "========================================================================"
echo "Completed: $(date)"
