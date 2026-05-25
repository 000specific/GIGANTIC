#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 April 27 | Purpose: Run BLOCK_orthofinder_array parallel-DIAMOND NextFlow pipeline
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh
# =============================================================================
# Runs the BLOCK_orthofinder_array NextFlow pipeline.
# Supports both local and SLURM execution via START_HERE-user_config.yaml.
#
# Usage:
#   bash RUN-workflow.sh
#
# Set execution_mode in START_HERE-user_config.yaml:
#   "local" - runs directly on this machine
#   "slurm" - submits as a SLURM driver job with resources from config
# =============================================================================

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Activate Environment
# ============================================================================

# GIGANTIC env naming convention: aiG-<subproject>-<block_or_step>-<optional_details>
# Per-BLOCK conda env. Auto-created on first run from ai/conda_environment.yml.
# mamba is preferred (much faster); conda is the fallback if mamba is missing.
# This env is SHARED with BLOCK_orthofinder (same OrthoFinder tool).

ENV_NAME="aiG-orthogroups-orthofinder"
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
# Read execution mode from START_HERE-user_config.yaml
# ============================================================================
# Uses grep+sed to parse flat YAML keys (no Python dependency required).

read_config() {
    # Read a flat YAML key from START_HERE-user_config.yaml (no Python dependency)
    # Pipeline:
    #   1. grep the line beginning with the key
    #   2. strip "key: " prefix
    #   3. strip trailing inline yaml comments ("# ...") and trailing whitespace
    #   4. strip wrapping double-quotes
    local value=$(grep "^${1}:" START_HERE-user_config.yaml 2>/dev/null \
        | head -1 \
        | sed 's/^[^:]*: *//' \
        | sed 's/[[:space:]]*#.*$//' \
        | sed 's/[[:space:]]*$//' \
        | sed 's/^"//;s/"$//')
    echo "${value:-$2}"
}

EXECUTION_MODE=$(read_config "execution_mode" "local")

# ============================================================================
# SLURM submission (if execution_mode is "slurm" and not already inside a job)
# ============================================================================

if [ "${EXECUTION_MODE}" == "slurm" ] && [ -z "${SLURM_JOB_ID}" ]; then
    echo "Execution mode: SLURM (submitting driver job)"
    echo ""

    # Read SLURM settings from config
    SLURM_CPUS=$(read_config "slurm_cpus" "4")
    SLURM_MEM=$(read_config "slurm_memory_gb" "30")
    SLURM_TIME=$(read_config "slurm_time_hours" "240")
    SLURM_ACCOUNT=$(read_config "slurm_account" "")
    SLURM_QOS=$(read_config "slurm_qos" "")
    SLURM_MAIL_USER=$(read_config "slurm_mail_user" "")
    SLURM_MAIL_TYPE=$(read_config "slurm_mail_type" "END,FAIL")

    mkdir -p slurm_logs

    SBATCH_ARGS="--job-name=orthofinder_array"
    SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${SLURM_CPUS}"
    SBATCH_ARGS="${SBATCH_ARGS} --mem=${SLURM_MEM}gb"
    SBATCH_ARGS="${SBATCH_ARGS} --time=${SLURM_TIME}:00:00"
    SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/orthofinder_array-%j.log"

    if [ -n "${SLURM_ACCOUNT}" ]; then
        SBATCH_ARGS="${SBATCH_ARGS} --account=${SLURM_ACCOUNT}"
    fi
    if [ -n "${SLURM_QOS}" ]; then
        SBATCH_ARGS="${SBATCH_ARGS} --qos=${SLURM_QOS}"
    fi
    # Email notifications — only included if slurm_mail_user is set in yaml
    if [ -n "${SLURM_MAIL_USER}" ]; then
        SBATCH_ARGS="${SBATCH_ARGS} --mail-user=${SLURM_MAIL_USER}"
        SBATCH_ARGS="${SBATCH_ARGS} --mail-type=${SLURM_MAIL_TYPE}"
    fi

    echo "Submitting with: sbatch ${SBATCH_ARGS}"
    sbatch ${SBATCH_ARGS} --wrap="bash $(realpath $0)"

    echo ""
    echo "Driver job submitted. Check slurm_logs/ for output."
    echo "DIAMOND fan-out tasks will be submitted by NextFlow as burst-mode SLURM array jobs."
    conda deactivate 2>/dev/null || true
    exit 0
fi

# ============================================================================
# Run Nextflow pipeline (local execution or inside SLURM driver job)
# ============================================================================

if [ -n "${SLURM_JOB_ID}" ]; then
    echo "Running inside SLURM driver job ${SLURM_JOB_ID}"
else
    echo "Execution mode: local"
fi

# Validate prerequisites
echo "Validating prerequisites..."
echo ""

if [ ! -f "START_HERE-user_config.yaml" ]; then
    echo "ERROR: Configuration file not found!"
    echo "Expected: START_HERE-user_config.yaml"
    exit 1
fi
echo "  [OK] Configuration file found"
echo ""

echo "========================================================================"
echo "Starting BLOCK_orthofinder_array Pipeline"
echo "========================================================================"

# Optionally resume from cached work/ if user enabled it in config
RESUME=$(read_config "resume" "false")
RESUME_FLAG=""
if [ "${RESUME}" == "true" ]; then
    RESUME_FLAG="-resume"
    echo "  resume: enabled (using NextFlow work/ cache)"
fi

# ============================================================================
# Flatten START_HERE-user_config.yaml -> .params.json for NextFlow -params-file
# ============================================================================
# Universal GIGANTIC YAML->params pattern: pass-through json.dump (no flatten).

python3 <<'PYTHON_DUMP'
import yaml, json
with open( 'START_HERE-user_config.yaml' ) as f:
    cfg = yaml.safe_load( f )
with open( '.params.json', 'w' ) as f:
    json.dump( cfg, f, indent=2 )
PYTHON_DUMP

nextflow run ai/main.nf ${RESUME_FLAG} \
    -params-file .params.json \
    -c ai/nextflow.config

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "========================================================================"
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "========================================================================"
    exit $EXIT_CODE
fi

# ============================================================================
# Create symlinks for output_to_input (subproject root)
# ============================================================================
# Real files live in OUTPUT_pipeline/N-output/ (created by NextFlow above).
# Symlinks are created at the subproject-root output_to_input/BLOCK_orthofinder_array/.
#
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"
SUBPROJECT_SHARED_DIR="../../output_to_input/BLOCK_orthofinder_array"
mkdir -p "${SUBPROJECT_SHARED_DIR}"

# Remove any stale symlinks from previous runs
find "${SUBPROJECT_SHARED_DIR}" -type l -delete 2>/dev/null

# Final orthogroup tables (from script 007 — standardize_output)
ln -sf "../../BLOCK_orthofinder_array/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/7-output/7_ai-orthogroups_gigantic_ids.tsv" \
    "${SUBPROJECT_SHARED_DIR}/orthogroups_gigantic_ids.tsv"
ln -sf "../../BLOCK_orthofinder_array/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/7-output/7_ai-gene_count_gigantic_ids.tsv" \
    "${SUBPROJECT_SHARED_DIR}/gene_count_gigantic_ids.tsv"

# Summary statistics (from script 008)
ln -sf "../../BLOCK_orthofinder_array/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/8-output/8_ai-summary_statistics.tsv" \
    "${SUBPROJECT_SHARED_DIR}/summary_statistics.tsv"

# Per-species QC (from script 009)
ln -sf "../../BLOCK_orthofinder_array/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/9-output/9_ai-per_species_summary.tsv" \
    "${SUBPROJECT_SHARED_DIR}/per_species_summary.tsv"

echo "  Created symlinks in output_to_input/BLOCK_orthofinder_array/"

echo ""
echo "========================================================================"
echo "SUCCESS! BLOCK_orthofinder_array pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/ through 9-output/"
echo ""
echo "Downstream symlinks:"
echo "  ../../output_to_input/BLOCK_orthofinder_array/  (subproject root)"
echo ""
echo "Next: Review results, then run BLOCK_comparison for cross-tool analysis"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
