#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 30 | Purpose: Run orthogroup clustering comparison Nextflow pipeline
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh
# =============================================================================
# Runs the orthogroup clustering comparison pipeline.
#
# Prerequisites:
#   1. Edit START_HERE-user_config.yaml (or use defaults)
#   2. Create INPUT_user/clustering_manifest.tsv from the example:
#        cp INPUT_user/clustering_manifest_example.tsv INPUT_user/clustering_manifest.tsv
#   3. Edit the manifest with paths to your clustering run OUTPUT_pipeline directories
#   4. At least 2 clustering runs must be listed in the manifest
#
# Usage:
#   bash RUN-workflow.sh
#
# FOR SLURM CLUSTERS:
#   sbatch SLURM_workflow.sbatch
# =============================================================================

set -e

echo "========================================================================"
echo "Starting Orthogroup Clustering Comparison Pipeline"
echo "========================================================================"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Validate manifest exists
# ============================================================================

MANIFEST="INPUT_user/clustering_manifest.tsv"

if [ ! -f "${MANIFEST}" ]; then
    echo "ERROR: Manifest not found: ${MANIFEST}"
    echo ""
    echo "Create it from the example:"
    echo "  cp INPUT_user/clustering_manifest_example.tsv INPUT_user/clustering_manifest.tsv"
    echo ""
    echo "Then edit it with your clustering run paths."
    exit 1
fi

echo "Manifest: ${MANIFEST}"
echo ""

# ============================================================================
# Activate GIGANTIC Environment (on-demand creation)
# ============================================================================
# GIGANTIC env naming convention: aiG-<subproject>-<block_or_step>-<optional_details>
# Per-BLOCK conda env. Auto-created on first run from ai/conda_environment.yml.
# mamba is preferred (much faster); conda is the fallback if mamba is missing.
# This env is dedicated to BLOCK_comparison (lightweight: matplotlib + numpy
# for cross-tool comparison; does NOT run orthohmm/orthofinder/broccoli).

ENV_NAME="aiG-orthogroups-comparison"
ENV_YML="ai/conda_environment.yml"

module load conda 2>/dev/null || true

if ! command -v conda &> /dev/null; then
    echo "ERROR: conda not found!"
    echo "On HPC (HiPerGator): module load conda"
    exit 1
fi

env_is_complete() {
    local env_prefix=$(conda env list 2>/dev/null | awk -v n="${ENV_NAME}" '$1==n {print $NF}')
    if [ -z "${env_prefix}" ]; then return 1; fi
    if [ ! -x "${env_prefix}/bin/python" ]; then return 1; fi
    return 0
}

if ! env_is_complete; then
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

if conda activate "${ENV_NAME}" 2>/dev/null; then
    echo "Activated conda environment: ${ENV_NAME}"
else
    echo "WARNING: Could not activate '${ENV_NAME}'. Continuing with current environment."
fi

if ! command -v nextflow &> /dev/null; then
    module load nextflow 2>/dev/null || true
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: NextFlow not available!"
        exit 1
    fi
fi
echo ""

# ============================================================================
# Run Nextflow pipeline
# ============================================================================

# Optionally resume from cached work/ if user enabled it in config
# (inline yaml-read since this older workflow lacks the read_config helper)
RESUME=$(grep "^resume:" START_HERE-user_config.yaml 2>/dev/null | head -1 | sed 's/^[^:]*: *//' | sed 's/^"//;s/"$//')
RESUME_FLAG=""
if [ "${RESUME}" == "true" ]; then
    RESUME_FLAG="-resume"
    echo "  resume: enabled (using NextFlow work/ cache)"
fi

# ============================================================================
# Flatten START_HERE-user_config.yaml -> .params.json for NextFlow -params-file
# ============================================================================
# Universal GIGANTIC YAML->params pattern: pass-through json.dump (no flatten).
# NextFlow's params is a ConfigMap that supports nested access (params.X.Y.Z)
# natively, so we preserve the YAML shape rather than translating it.

python3 <<'PYTHON_DUMP'
import yaml, json
with open( 'START_HERE-user_config.yaml' ) as f:
    cfg = yaml.safe_load( f )
with open( '.params.json', 'w' ) as f:
    json.dump( cfg, f, indent=2 )
PYTHON_DUMP

nextflow run ai/main.nf ${RESUME_FLAG} \
    -c ai/nextflow.config \
    -params-file .params.json

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "========================================================================"
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "========================================================================"
    exit $EXIT_CODE
fi

# ============================================================================
# Create symlinks for output_to_input directory
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

SUBPROJECT_SHARED_DIR="../../output_to_input/BLOCK_comparison"
mkdir -p "${SUBPROJECT_SHARED_DIR}"

# Remove stale symlinks from previous runs
find "${SUBPROJECT_SHARED_DIR}" -type l -delete 2>/dev/null

ln -sf "../../BLOCK_comparison/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/1-output/1_ai-compare_clustering_runs.tsv" \
    "${SUBPROJECT_SHARED_DIR}/compare_clustering_runs.tsv"
ln -sf "../../BLOCK_comparison/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/1-output/1_ai-per_species_copy_number_profiles.tsv" \
    "${SUBPROJECT_SHARED_DIR}/per_species_copy_number_profiles.tsv"
ln -sf "../../BLOCK_comparison/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/1-output/1_ai-pairwise_run_overlap.tsv" \
    "${SUBPROJECT_SHARED_DIR}/pairwise_run_overlap.tsv"

echo "  Created symlinks in output_to_input/BLOCK_comparison/"

echo ""
echo "========================================================================"
echo "SUCCESS! Clustering comparison pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/  (comparison tables)"
echo "  OUTPUT_pipeline/2-output/  (visualization plots)"
echo ""
echo "Downstream symlinks:"
echo "  output_to_input/BLOCK_comparison/  (subproject root)"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
