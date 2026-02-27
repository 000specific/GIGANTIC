#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 26 | Purpose: Run STEP_2 standardization workflow
# Human: Eric Edsinger

# =============================================================================
# GIGANTIC genomesDB - STEP_2 Standardize and Evaluate Workflow
# =============================================================================
#
# This script runs all STEP_2 analysis scripts in sequence:
#   001: Standardize proteome filenames and FASTA headers with phylonames
#   002: Create phyloname-based symlinks for genomes and gene annotations
#   003: Calculate genome assembly statistics using gfastats
#
# Prerequisites:
#   - STEP_1-sources must be complete (provides proteomes, genomes, annotations)
#   - phylonames subproject must be complete (provides species naming)
#   - Conda environment: ai_gigantic_genomesdb (for script 003)
#
# Usage:
#   cd workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/
#   bash RUN-workflow.sh
#
# =============================================================================

set -e  # Exit on any error

echo "========================================================================"
echo "GIGANTIC genomesDB - STEP_2 Standardize and Evaluate"
echo "========================================================================"
echo "Start time: $(date)"
echo ""

# =============================================================================
# CONFIGURATION
# =============================================================================

# Script directory (where this script is located)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Input paths (relative to workflow directory)
# These point to output_to_input directories from prerequisite subprojects
PHYLONAMES_MAPPING="../../phylonames/output_to_input/maps/species71_map-genus_species_X_phylonames.tsv"
INPUT_PROTEOMES="../../STEP_1-sources/output_to_input/T1_proteomes"
INPUT_GENOMES="../../STEP_1-sources/output_to_input/genomes"
INPUT_GENE_ANNOTATIONS="../../STEP_1-sources/output_to_input/gene_annotations"

# Output base directory
OUTPUT_DIR="${SCRIPT_DIR}/OUTPUT_pipeline"

# Scripts location
SCRIPTS_DIR="${SCRIPT_DIR}/ai/scripts"

# =============================================================================
# VALIDATE PREREQUISITES
# =============================================================================

echo "Validating prerequisites..."
echo ""

# Check phylonames mapping exists
if [ ! -f "${SCRIPT_DIR}/${PHYLONAMES_MAPPING}" ]; then
    echo "ERROR: Phylonames mapping not found!"
    echo "Expected: ${SCRIPT_DIR}/${PHYLONAMES_MAPPING}"
    echo "Run the phylonames subproject first."
    exit 1
fi
echo "  [OK] Phylonames mapping found"

# Check proteomes directory exists
if [ ! -d "${SCRIPT_DIR}/${INPUT_PROTEOMES}" ]; then
    echo "ERROR: Input proteomes directory not found!"
    echo "Expected: ${SCRIPT_DIR}/${INPUT_PROTEOMES}"
    echo "Run STEP_1-sources first."
    exit 1
fi
echo "  [OK] Input proteomes directory found"

# Check genomes directory exists (optional - may have fewer genomes than proteomes)
if [ ! -d "${SCRIPT_DIR}/${INPUT_GENOMES}" ]; then
    echo "WARNING: Input genomes directory not found"
    echo "Expected: ${SCRIPT_DIR}/${INPUT_GENOMES}"
    echo "Script 002 and 003 will be skipped."
    SKIP_GENOMES=true
else
    echo "  [OK] Input genomes directory found"
    SKIP_GENOMES=false
fi

# Check gene annotations directory exists
if [ ! -d "${SCRIPT_DIR}/${INPUT_GENE_ANNOTATIONS}" ]; then
    echo "WARNING: Input gene annotations directory not found"
    echo "Expected: ${SCRIPT_DIR}/${INPUT_GENE_ANNOTATIONS}"
    SKIP_ANNOTATIONS=true
else
    echo "  [OK] Input gene annotations directory found"
    SKIP_ANNOTATIONS=false
fi

echo ""

# =============================================================================
# SCRIPT 001: Standardize Proteome Phylonames
# =============================================================================

echo "========================================================================"
echo "SCRIPT 001: Standardize Proteome Phylonames"
echo "========================================================================"

python3 "${SCRIPTS_DIR}/001_ai-python-standardize_proteome_phylonames.py" \
    --phylonames-mapping "${SCRIPT_DIR}/${PHYLONAMES_MAPPING}" \
    --input-proteomes "${SCRIPT_DIR}/${INPUT_PROTEOMES}" \
    --output-dir "${OUTPUT_DIR}/1-output"

echo ""
echo "Script 001 complete."
echo ""

# =============================================================================
# SCRIPT 002: Standardize Genome and Annotation Phylonames
# =============================================================================

if [ "$SKIP_GENOMES" = true ] && [ "$SKIP_ANNOTATIONS" = true ]; then
    echo "========================================================================"
    echo "SCRIPT 002: SKIPPED (no genomes or annotations available)"
    echo "========================================================================"
else
    echo "========================================================================"
    echo "SCRIPT 002: Standardize Genome and Annotation Phylonames"
    echo "========================================================================"

    # Build command with available inputs
    CMD="python3 ${SCRIPTS_DIR}/002_ai-python-standardize_genome_and_annotation_phylonames.py"
    CMD="${CMD} --phylonames-mapping ${SCRIPT_DIR}/${PHYLONAMES_MAPPING}"
    CMD="${CMD} --output-dir ${OUTPUT_DIR}/2-output"

    if [ "$SKIP_GENOMES" = false ]; then
        CMD="${CMD} --input-genomes ${SCRIPT_DIR}/${INPUT_GENOMES}"
    fi

    if [ "$SKIP_ANNOTATIONS" = false ]; then
        CMD="${CMD} --input-gene-annotations ${SCRIPT_DIR}/${INPUT_GENE_ANNOTATIONS}"
    fi

    eval $CMD

    echo ""
    echo "Script 002 complete."
fi
echo ""

# =============================================================================
# SCRIPT 003: Calculate Genome Assembly Statistics
# =============================================================================

if [ "$SKIP_GENOMES" = true ]; then
    echo "========================================================================"
    echo "SCRIPT 003: SKIPPED (no genomes available)"
    echo "========================================================================"
else
    echo "========================================================================"
    echo "SCRIPT 003: Calculate Genome Assembly Statistics"
    echo "========================================================================"

    # Note: This script requires gfastats from the ai_gigantic_genomesdb conda environment
    # If running outside SLURM, ensure the environment is activated

    python3 "${SCRIPTS_DIR}/003_ai-python-calculate_genome_assembly_statistics.py" \
        --input-genomes "${OUTPUT_DIR}/2-output/gigantic_genomes" \
        --phylonames-mapping "${SCRIPT_DIR}/${PHYLONAMES_MAPPING}" \
        --output-dir "${OUTPUT_DIR}/3-output"

    echo ""
    echo "Script 003 complete."
fi
echo ""

# =============================================================================
# SUMMARY
# =============================================================================

echo "========================================================================"
echo "WORKFLOW COMPLETE"
echo "========================================================================"
echo "End time: $(date)"
echo ""
echo "Outputs:"
echo "  1-output/: Standardized proteomes with phylonames"
if [ "$SKIP_GENOMES" = false ]; then
    echo "  2-output/: Standardized genomes and annotations (symlinks)"
    echo "  3-output/: Genome assembly statistics"
fi
echo ""
echo "See OUTPUT_pipeline/ for all results."
echo "========================================================================"
