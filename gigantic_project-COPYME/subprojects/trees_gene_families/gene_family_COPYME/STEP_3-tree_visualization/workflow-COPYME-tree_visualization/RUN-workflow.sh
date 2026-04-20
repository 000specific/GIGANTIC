#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 April 19 | Purpose: Run STEP_3 tree_visualization workflow
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_gene_families - STEP_3 tree_visualization
################################################################################
#
# PURPOSE:
# Render gene family phylogenetic trees (produced by STEP_2) as PDF + SVG
# using toytree. This is decoupled from STEP_2 deliberately: the newick is
# the scientific artifact, the PDF is presentation. A render failure should
# never invalidate the science.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Edit START_HERE-user_config.yaml (set gene_family name to match STEP_2 output)
# 2. Verify STEP_2 has populated output_to_input:
#    ../../../output_to_input/<gene_family>/STEP_2-phylogenetic_analysis/
#
# WHAT THIS DOES:
# 1. Creates/activates the aiG-trees_gene_families-visualization conda env
#    (self-heals broken envs from prior failed installs)
# 2. Runs Script 001 which:
#    - Auto-discovers tree newicks in STEP_2 output
#    - Renders each to PDF + SVG with species color-coding and branch support
#    - Writes a summary report
# 3. Runs Script 002 to write the workflow run log
# 4. Creates symlinks in output_to_input/<gene_family>/STEP_3-tree_visualization/
#
# OUTPUT:
# OUTPUT_pipeline/1-output/
#   1_ai-visualization-<gene_family>-<method>.pdf    (one per tree method)
#   1_ai-visualization-<gene_family>-<method>.svg
#   1_ai-visualization_summary.md
#
# SOFT-FAIL:
# If toytree import fails or rendering breaks, the script writes a placeholder
# and exits 0. STEP_2 newicks remain valid. The placeholder file documents
# how to retry manually.
#
################################################################################

set -e

echo "========================================================================"
echo "GIGANTIC trees_gene_families - STEP_3 tree_visualization"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# Simple YAML reader for flat top-level keys (no Python dependency)
read_config() {
    local value=$(grep "^${1}:" START_HERE-user_config.yaml 2>/dev/null | head -1 | sed 's/^[^:]*: *//' | sed 's/^"//;s/"$//')
    echo "${value:-$2}"
}

# Read gene_family from the nested config structure
GENE_FAMILY=$(grep -A 5 "^gene_family:" START_HERE-user_config.yaml | grep "  name:" | head -1 | sed 's/.*: *"\([^"]*\)".*/\1/')

echo "Configuration:"
echo "  Gene family: ${GENE_FAMILY}"
echo ""

# ============================================================================
# Validate prerequisites
# ============================================================================

echo "Validating prerequisites..."

if [ ! -f "START_HERE-user_config.yaml" ]; then
    echo "ERROR: Configuration file not found: START_HERE-user_config.yaml"
    exit 1
fi
echo "  [OK] Configuration file found"

if [ -z "${GENE_FAMILY}" ]; then
    echo "ERROR: gene_family not set in START_HERE-user_config.yaml"
    exit 1
fi
echo "  [OK] Gene family configured: ${GENE_FAMILY}"

STEP2_DIR="../../../output_to_input/${GENE_FAMILY}/STEP_2-phylogenetic_analysis"
if [ ! -d "${STEP2_DIR}" ]; then
    echo "ERROR: STEP_2 output not found!"
    echo "  Expected: ${STEP2_DIR}"
    echo "  Run STEP_2 first for gene family '${GENE_FAMILY}'."
    exit 1
fi
echo "  [OK] STEP_2 output found"

echo ""

# ============================================================================
# Activate GIGANTIC Environment (on-demand creation + self-heal)
# ============================================================================
# This workflow needs: python, pyyaml, toytree, toyplot, reportlab
# All installed from ai/conda_environment.yml.

ENV_NAME="aiG-trees_gene_families-visualization"
ENV_YML="ai/conda_environment.yml"

# Load conda module on HPC systems
module load conda 2>/dev/null || true

if ! command -v conda &> /dev/null; then
    echo "ERROR: conda not found!"
    echo "On HPC (HiPerGator): module load conda"
    exit 1
fi

# Detect incomplete env (directory exists but missing Python) and rebuild.
# This addresses the "env dir created but install failed partway" failure mode
# we've seen bite ete3-based envs on conda-forge.
env_is_complete() {
    local env_prefix=$(conda env list 2>/dev/null | awk -v n="${ENV_NAME}" '$1==n {print $NF}')
    if [ -z "${env_prefix}" ]; then
        return 1  # not found at all
    fi
    if [ ! -x "${env_prefix}/bin/python" ]; then
        return 1  # env dir exists but broken/empty
    fi
    return 0
}

if ! env_is_complete; then
    # Make sure no broken husk remains
    if conda env list 2>/dev/null | awk '{print $1}' | grep -q "^${ENV_NAME}$"; then
        echo "Removing broken/incomplete env '${ENV_NAME}'..."
        conda env remove -n "${ENV_NAME}" -y 2>&1 | tail -3
    fi

    echo "Creating conda env '${ENV_NAME}' from ${ENV_YML}..."
    if [ ! -f "${ENV_YML}" ]; then
        echo "ERROR: Environment spec not found at: ${ENV_YML}"
        exit 1
    fi
    if command -v mamba &> /dev/null; then
        mamba env create -f "${ENV_YML}" -y
    else
        conda env create -f "${ENV_YML}" -y
    fi
    if ! env_is_complete; then
        echo "ERROR: Environment creation failed -- '${ENV_NAME}' still not complete."
        exit 1
    fi
    echo "Env '${ENV_NAME}' created successfully."
fi

# Activate the env
if conda activate "${ENV_NAME}" 2>/dev/null; then
    echo "Activated conda environment: ${ENV_NAME}"
else
    echo "WARNING: Could not activate '${ENV_NAME}'. Continuing with current environment."
fi
echo ""

# ============================================================================
# Run Script 001: render_trees (soft-fail on rendering issues)
# ============================================================================

echo "Running Script 001: render_trees (PDF + SVG)..."
echo ""

python3 ai/scripts/001_ai-python-render_trees.py \
    --config START_HERE-user_config.yaml

# Script 001 is soft-fail -- it always exits 0 unless there's a config error.
# STEP_2 newicks remain the valid artifact regardless of rendering outcome.

# ============================================================================
# Run Script 002: write_run_log
# ============================================================================

echo ""
echo "Running Script 002: write_run_log..."

python3 ai/scripts/002_ai-python-write_run_log.py \
    --workflow-name "tree_visualization" \
    --subproject-name "trees_gene_families" \
    --project-name "${GENE_FAMILY}" \
    --status success

# ============================================================================
# Create symlinks for output_to_input
# ============================================================================
# Expose the rendered PDFs/SVGs at output_to_input/<gene_family>/STEP_3-tree_visualization/
# for downstream consumption (upload_to_server publishing, browsing, etc.)

echo ""
echo "Creating symlinks for downstream..."

WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"
FAMILY_DIR_NAME="$(basename "$(dirname "$(dirname "${SCRIPT_DIR}")")")"
SYMLINK_DIR="../../../output_to_input/${GENE_FAMILY}/STEP_3-tree_visualization"
mkdir -p "${SYMLINK_DIR}"

# Remove stale symlinks from previous runs
for old_link in "${SYMLINK_DIR}"/*; do
    if [ -L "${old_link}" ]; then
        rm "${old_link}"
    fi
done

# Link each rendered file (PDF, SVG, summary)
for rendered_file in OUTPUT_pipeline/1-output/*; do
    if [ -f "${rendered_file}" ]; then
        filename=$(basename "${rendered_file}")
        # Target uses relative path from the symlink location to the real file
        ln -sf "../../../${FAMILY_DIR_NAME}/STEP_3-tree_visualization/${WORKFLOW_DIR_NAME}/${rendered_file}" \
            "${SYMLINK_DIR}/${filename}"
    fi
done

echo "  output_to_input/${GENE_FAMILY}/STEP_3-tree_visualization/ -> symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! STEP_3 tree visualization complete."
echo ""
echo "Rendered outputs:"
echo "  OUTPUT_pipeline/1-output/1_ai-visualization-*.pdf    (primary)"
echo "  OUTPUT_pipeline/1-output/1_ai-visualization-*.svg    (secondary)"
echo "  OUTPUT_pipeline/1-output/1_ai-visualization_summary.md"
echo ""
echo "Downstream symlinks:"
echo "  ../../../output_to_input/${GENE_FAMILY}/STEP_3-tree_visualization/"
echo "========================================================================"
echo "Completed: $(date)"
