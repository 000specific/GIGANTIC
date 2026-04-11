#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 April 10 | Purpose: Run gigantic_species_tree workflow locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_species - BLOCK_gigantic_species_tree (Local)
################################################################################
#
# PURPOSE:
# Run the gigantic_species_tree workflow to standardize and label a
# user-provided species tree for the GIGANTIC framework.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Place your species tree (Newick format) in INPUT_user/species_tree.newick
# 2. Edit START_HERE-user_config.yaml:
#    - Set species_set_name (e.g., "species70")
# 3. See INPUT_user/README.md for the required species tree format.
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN-workflow.sbatch
#
# WHAT THIS DOES:
# 1. Validates and standardizes your input species tree
# 2. Fills in ancestral_clade_NNN names for unlabeled internal nodes
# 3. Assigns CXXX_ clade identifiers to every node
# 4. Emits three Newick format variants (simple, full, ids-only)
# 5. Generates a clade name -> clade ID lookup TSV
# 6. Renders an SVG visualization (soft-fail if tooling unavailable)
# 7. Cross-validates all outputs for consistency
# 8. Writes a run log to ai/logs/
# 9. Creates output_to_input/ symlinks for downstream subprojects
#
# OUTPUT:
# Results in OUTPUT_pipeline/1-output through 6-output/
# Downstream symlinks in ../../output_to_input/BLOCK_gigantic_species_tree/
#
################################################################################

echo "========================================================================"
echo "GIGANTIC trees_species - BLOCK_gigantic_species_tree Pipeline (Local)"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Activate GIGANTIC Environment (on-demand creation)
# ============================================================================
# This workflow requires:
#   - conda environment: ai_gigantic_trees_species (Python, PyYAML, ete3, PyQt5)
#   - NextFlow: from conda env OR system module
#
# The environment is created automatically on first run from the yml spec
# in conda_environments/. You can also pre-create all environments at once:
#   cd ../../../../ && bash RUN-setup_environments.sh
#
# NextFlow availability:
#   - If installed in conda env: used automatically
#   - If not in conda env: falls back to "module load nextflow" (HPC systems)
#   - If neither available: exits with error and instructions
# ============================================================================

ENV_NAME="ai_gigantic_trees_species"
ENV_YML="../../../../conda_environments/${ENV_NAME}.yml"

# Load conda module (required on HPC systems like HiPerGator)
module load conda 2>/dev/null || true

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "ERROR: conda not found!"
    echo ""
    echo "On HPC (HiPerGator): module load conda"
    echo "Otherwise: install conda from https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Create environment on-demand if it does not exist
if ! conda env list 2>/dev/null | grep -q "^${ENV_NAME} "; then
    echo "Environment '${ENV_NAME}' not found. Creating on-demand..."
    echo ""
    if [ ! -f "${ENV_YML}" ]; then
        echo "ERROR: Environment spec not found at: ${ENV_YML}"
        echo "Make sure you are running from a valid GIGANTIC workflow directory."
        exit 1
    fi
    if command -v mamba &> /dev/null; then
        mamba env create -f "${ENV_YML}" -y
    else
        conda env create -f "${ENV_YML}" -y
    fi
    echo ""
    echo "Environment '${ENV_NAME}' created successfully."
    echo ""
fi

# Activate the environment
if conda activate "${ENV_NAME}" 2>/dev/null; then
    echo "Activated conda environment: ${ENV_NAME}"
else
    echo "WARNING: Could not activate '${ENV_NAME}'. Continuing with current environment."
fi

# Ensure NextFlow is available (conda env or system module)
if ! command -v nextflow &> /dev/null; then
    echo "NextFlow not found in conda env. Trying system module..."
    module load nextflow 2>/dev/null || true
    if ! command -v nextflow &> /dev/null; then
        echo ""
        echo "ERROR: NextFlow not available!"
        echo ""
        echo "Options to resolve:"
        echo "  1. Install nextflow in conda env: conda install -n ${ENV_NAME} -c bioconda nextflow"
        echo "  2. Load system module: module load nextflow"
        echo "  3. Install globally: https://www.nextflow.io/docs/latest/install.html"
        exit 1
    fi
    echo "Using NextFlow from system module"
else
    echo "NextFlow available"
fi
echo ""

# ============================================================================
# Validate Prerequisites
# ============================================================================

echo "Validating prerequisites..."
echo ""

# Check config file exists
if [ ! -f "START_HERE-user_config.yaml" ]; then
    echo "ERROR: Configuration file not found!"
    echo "Expected: START_HERE-user_config.yaml"
    exit 1
fi
echo "  [OK] Configuration file found"

# Check INPUT_user directory exists
if [ ! -d "INPUT_user" ]; then
    echo "ERROR: INPUT_user/ directory not found!"
    echo "  Create it and add your species tree Newick file."
    exit 1
fi
echo "  [OK] INPUT_user/ directory found"

# Check species tree file exists
if [ ! -f "INPUT_user/species_tree.newick" ]; then
    echo "ERROR: Species tree not found!"
    echo "  Expected: INPUT_user/species_tree.newick"
    echo "  Place your Newick-format species tree in INPUT_user/"
    echo "  See INPUT_user/README.md for the required format."
    exit 1
fi
echo "  [OK] Species tree found: INPUT_user/species_tree.newick"

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
# Create symlinks for output_to_input directory
# ============================================================================
# Real files live in OUTPUT_pipeline/N-output/ (created by NextFlow above).
# Symlinks are created in ONE location at the subproject root:
#   ../../output_to_input/BLOCK_gigantic_species_tree/
#
# Downstream subprojects (notably BLOCK_permutations_and_features) read from
# here. The canonical downstream-consumable files are:
#   - {species_set}-species_tree-with_clade_ids_and_names.newick (full format)
#   - {species_set}-species_tree-simple.newick                    (simple format)
#   - {species_set}-species_tree-clade_ids_only.newick            (ids-only format)
#   - {species_set}-clade_name_X_clade_id.tsv                     (lookup map)
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

# Determine the workflow directory name dynamically
# (supports both COPYME templates and RUN_XX instances)
WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

# --- Subproject-root output_to_input/BLOCK_gigantic_species_tree/ ---
SUBPROJECT_SHARED_DIR="../../output_to_input/BLOCK_gigantic_species_tree"
mkdir -p "${SUBPROJECT_SHARED_DIR}"

# Remove any stale symlinks from previous runs
for old_link in "${SUBPROJECT_SHARED_DIR}"/*species_tree*.newick "${SUBPROJECT_SHARED_DIR}"/*clade_name_X_clade_id.tsv; do
    if [ -L "$old_link" ]; then
        rm "$old_link"
    fi
done

# Create symlinks for each downstream-consumable output
# Three Newick variants from 3-output/
for newick_file in OUTPUT_pipeline/3-output/3_ai-*-species_tree-simple.newick \
                   OUTPUT_pipeline/3-output/3_ai-*-species_tree-with_clade_ids_and_names.newick \
                   OUTPUT_pipeline/3-output/3_ai-*-species_tree-clade_ids_only.newick; do
    if [ -f "$newick_file" ]; then
        filename="$(basename "$newick_file")"
        # Strip the "3_ai-" prefix for the symlink name
        symlink_name="${filename#3_ai-}"
        ln -sf "../../BLOCK_gigantic_species_tree/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/3-output/${filename}" \
            "${SUBPROJECT_SHARED_DIR}/${symlink_name}"
    fi
done

# Clade map TSV from 4-output/
for map_file in OUTPUT_pipeline/4-output/4_ai-*-clade_name_X_clade_id.tsv; do
    if [ -f "$map_file" ]; then
        filename="$(basename "$map_file")"
        symlink_name="${filename#4_ai-}"
        ln -sf "../../BLOCK_gigantic_species_tree/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/4-output/${filename}" \
            "${SUBPROJECT_SHARED_DIR}/${symlink_name}"
    fi
done

echo "  output_to_input/BLOCK_gigantic_species_tree/ -> symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! gigantic_species_tree pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/  Canonical input tree + name mapping + validation report"
echo "  OUTPUT_pipeline/2-output/  Fully labeled species tree (CXXX_Name everywhere)"
echo "  OUTPUT_pipeline/3-output/  Three Newick variants (simple, full, ids-only)"
echo "  OUTPUT_pipeline/4-output/  Clade name <-> clade ID lookup TSV"
echo "  OUTPUT_pipeline/5-output/  Species tree visualization (SVG or placeholder)"
echo "  OUTPUT_pipeline/6-output/  Cross-validation report"
echo ""
echo "Downstream symlinks:"
echo "  ../../output_to_input/BLOCK_gigantic_species_tree/ (for downstream subprojects)"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
