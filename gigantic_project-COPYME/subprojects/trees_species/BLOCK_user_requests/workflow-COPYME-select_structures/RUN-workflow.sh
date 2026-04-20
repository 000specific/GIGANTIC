#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 April 18 | Purpose: Run select_structures workflow
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_species - BLOCK_user_requests - Select Structures
################################################################################
#
# PURPOSE:
# Query the 105 species tree structures produced by trees_species and return
# the ones that match user-specified topological features (e.g., Leonid's
# 4 trees for Ctenophora vs Porifera basal x ParaHoxozoa arrangements).
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Edit INPUT_user/query_manifest.yaml to describe your queries
#    (a template with Leonid's 4 trees example ships with the COPYME)
# 2. (Optional) Edit START_HERE-user_config.yaml to set run_label
# 3. Verify trees_species has populated output_to_input:
#    ../../output_to_input/BLOCK_permutations_and_features/
#
# WHAT THIS DOES:
# Runs Script 001 which:
#   1. Loads the query manifest
#   2. Scans phylogenetic blocks from trees_species for every structure
#   3. Evaluates each query against each structure
#   4. Outputs matching structures as TSV + newick copies + ASCII previews
#
# OUTPUT:
# OUTPUT_pipeline/1-output/
#   1_ai-matching_structures.tsv    -- query x structure matches
#   1_ai-query_summary.md           -- human-readable summary
#   1_ai-selected_structures/       -- newick copies of matched structures
#   1_ai-ascii_previews/            -- ASCII tree previews
#
################################################################################

echo "========================================================================"
echo "GIGANTIC trees_species - BLOCK_user_requests - Select Structures"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# Simple YAML reader for flat top-level keys (no Python dependency required)
read_config() {
    local value=$(grep "^${1}:" START_HERE-user_config.yaml 2>/dev/null | head -1 | sed 's/^[^:]*: *//' | sed 's/^"//;s/"$//')
    echo "${value:-$2}"
}

RUN_LABEL=$(read_config "run_label" "user_request")

echo "Configuration:"
echo "  Run Label: ${RUN_LABEL}"
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

if [ ! -f "INPUT_user/query_manifest.yaml" ]; then
    echo "ERROR: Query manifest not found: INPUT_user/query_manifest.yaml"
    echo "  Edit this file to describe your topological queries."
    exit 1
fi
echo "  [OK] Query manifest found"

if [ ! -d "../../output_to_input/BLOCK_permutations_and_features" ]; then
    echo "ERROR: trees_species output not found!"
    echo "  Expected: ../../output_to_input/BLOCK_permutations_and_features/"
    echo "  Run trees_species pipeline first."
    exit 1
fi
echo "  [OK] trees_species output found"

echo ""

# ============================================================================
# Activate GIGANTIC Environment (on-demand creation)
# ============================================================================
# This workflow needs:
#   - python, pyyaml -- Script 001 (select_structures)
#   - toytree, toyplot, reportlab -- Script 002 (visualize_structures)
# All installed from ai/conda_environment.yml.

ENV_NAME="aiG-trees_species-user_requests"
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
# we've seen bite trees_species.
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
# Run Script 001: select_structures
# ============================================================================

echo "Running Script 001: select_structures..."
echo ""

python3 ai/scripts/001_ai-python-select_structures.py \
    --config START_HERE-user_config.yaml

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "========================================================================"
    echo "FAILED! Script 001 exited with code ${EXIT_CODE}"
    echo "========================================================================"
    exit $EXIT_CODE
fi

# ============================================================================
# Run Script 002: visualize_structures (soft-fail on tooling issues)
# ============================================================================

echo ""
echo "Running Script 002: visualize_structures (PDF + SVG)..."
echo ""

python3 ai/scripts/002_ai-python-visualize_structures.py \
    --config START_HERE-user_config.yaml

# Script 002 is soft-fail -- don't gate the rest of the workflow on it.
# It always exits 0 unless there's a config error. Selection outputs remain valid.

# ============================================================================
# Create symlinks for output_to_input
# ============================================================================
# Expose the selected structures at output_to_input level for downstream use
# (e.g., a user-specific annotations_X_ocl run on just these 4 trees).

echo ""
echo "Creating symlinks for downstream subprojects..."

WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"
SHARED_DIR="../../output_to_input/BLOCK_user_requests/${RUN_LABEL}"
mkdir -p "${SHARED_DIR}"

# Remove stale symlinks from previous runs
for old_link in "${SHARED_DIR}"/*; do
    if [ -L "${old_link}" ]; then
        rm "${old_link}"
    fi
done

# Link the entire 1-output directory (matches table + selected newicks + previews)
ln -sf "../../../BLOCK_user_requests/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/1-output" \
    "${SHARED_DIR}/1-output" 2>/dev/null

echo "  output_to_input/BLOCK_user_requests/${RUN_LABEL}/ -> linked"

echo ""
echo "========================================================================"
echo "SUCCESS! Structure selection + visualization complete."
echo ""
echo "Selection outputs (Script 001):"
echo "  OUTPUT_pipeline/1-output/1_ai-matching_structures.tsv"
echo "  OUTPUT_pipeline/1-output/1_ai-canonical_structures.tsv"
echo "  OUTPUT_pipeline/1-output/1_ai-query_summary.md"
echo "  OUTPUT_pipeline/1-output/1_ai-selected_structures/     (all-match newicks)"
echo "  OUTPUT_pipeline/1-output/1_ai-canonical_structures/    (canonical newicks)"
echo "  OUTPUT_pipeline/1-output/1_ai-ascii_previews/          (all-match ASCII)"
echo "  OUTPUT_pipeline/1-output/1_ai-canonical_previews/      (canonical ASCII)"
echo ""
echo "Visualization outputs (Script 002 -- PDF primary, SVG secondary):"
echo "  OUTPUT_pipeline/2-output/2_ai-canonical_visualizations/     <- SHARE WITH COLLABORATORS"
echo "  OUTPUT_pipeline/2-output/2_ai-all_matched_visualizations/   (reference set)"
echo "  OUTPUT_pipeline/2-output/2_ai-visualization_summary.md"
echo ""
echo "Downstream symlinks:"
echo "  ../../output_to_input/BLOCK_user_requests/${RUN_LABEL}/"
echo "========================================================================"
echo "Completed: $(date)"
