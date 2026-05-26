#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 May 25 | Purpose: Run STEP_2-filter_secretome NextFlow pipeline
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh — STEP_2 filter_secretome
# =============================================================================
# Applies one user-defined filter manifest (JSON, authored via the HTML
# builder in INPUT_user/) to all STEP_1 per-species evidence tables.
# Each run produces one per-species secretome TSV, tagged with an
# auto-incremented `secretome_NNN[_<output_name>]` label.
#
# Counter logic:
#   - Scans existing `output_to_input/STEP_2-filter_secretome/` for files
#     matching `*_secretome_NNN[_*]_secretome.tsv` and picks NNN+1.
#   - User's optional `output_name` (from the JSON manifest) is appended
#     to the label: `secretome_007_moroz_strict_<phyloname>_secretome.tsv`.
#
# Supports execution_mode: local | slurm  (set in START_HERE-user_config.yaml)
# =============================================================================

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# Disable NextFlow telemetry/update checks (prevents curl hangs on compute nodes)
export NXF_OFFLINE=true

read_config() {
    local value=$(grep "^${1}:" START_HERE-user_config.yaml 2>/dev/null | head -1 | sed 's/^[^:]*: *//' | sed 's/^"//;s/"$//')
    echo "${value:-$2}"
}

EXECUTION_MODE=$(read_config "execution_mode" "local")

# =============================================================================
# SLURM self-submit (if execution_mode=slurm and not already in a SLURM job)
# =============================================================================

if [ "${EXECUTION_MODE}" == "slurm" ] && [ -z "${SLURM_JOB_ID}" ]; then
    echo "Execution mode: SLURM (submitting job)"
    echo ""

    SLURM_CPUS=$(read_config "cpus" "8")
    SLURM_MEM=$(read_config "memory_gb" "16")
    SLURM_TIME=$(read_config "time_hours" "4")
    SLURM_ACCOUNT=$(read_config "slurm_account" "")
    SLURM_QOS=$(read_config "slurm_qos" "")

    mkdir -p slurm_logs

    SBATCH_ARGS="--job-name=secretome_filter"
    SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${SLURM_CPUS}"
    SBATCH_ARGS="${SBATCH_ARGS} --mem=${SLURM_MEM}gb"
    SBATCH_ARGS="${SBATCH_ARGS} --time=${SLURM_TIME}:00:00"
    SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/secretome_filter-%j.log"

    if [ -n "${SLURM_ACCOUNT}" ]; then
        SBATCH_ARGS="${SBATCH_ARGS} --account=${SLURM_ACCOUNT}"
    fi
    if [ -n "${SLURM_QOS}" ]; then
        SBATCH_ARGS="${SBATCH_ARGS} --qos=${SLURM_QOS}"
    fi

    echo "Submitting with: sbatch ${SBATCH_ARGS}"
    sbatch ${SBATCH_ARGS} --wrap="bash $(realpath $0)"
    echo ""
    echo "Job submitted. Check slurm_logs/ for output."
    exit 0
fi

if [ -n "${SLURM_JOB_ID}" ]; then
    echo "Running inside SLURM job ${SLURM_JOB_ID}"
else
    echo "Execution mode: local"
fi
echo ""

# =============================================================================
# Activate conda env (auto-create on first run)
# =============================================================================

ENV_NAME="aiG-secretome-filter_secretome"
ENV_YML="ai/conda_environment.yml"

module load conda 2>/dev/null || true

if ! command -v conda &> /dev/null; then
    echo "ERROR: conda not found! On HPC: module load conda"
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
        echo "ERROR: env spec not found: ${ENV_YML}"
        exit 1
    fi
    if command -v mamba &> /dev/null; then
        mamba env create -f "${ENV_YML}" -y
    else
        conda env create -f "${ENV_YML}" -y
    fi
    if ! env_is_complete; then
        echo "ERROR: Env creation failed -- '${ENV_NAME}' not complete."
        exit 1
    fi
    echo "Env '${ENV_NAME}' created."
fi

if conda activate "${ENV_NAME}" 2>/dev/null; then
    echo "Activated conda environment: ${ENV_NAME}"
else
    echo "WARNING: Could not activate '${ENV_NAME}'. Continuing with current environment."
fi

if ! command -v nextflow &> /dev/null; then
    module load nextflow 2>/dev/null || true
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: NextFlow not available."
        exit 1
    fi
fi
echo ""

# =============================================================================
# Compute run_label
# =============================================================================
# Counter: scan existing output_to_input/STEP_2-filter_secretome/ for files
# named *_secretome_NNN[_*]_secretome.tsv  → pick max(NNN) + 1
# User's optional output_name from the JSON manifest is appended.

OUTPUT_TO_INPUT_DIR="../../output_to_input/STEP_2-filter_secretome"
mkdir -p "${OUTPUT_TO_INPUT_DIR}"

USER_OUTPUT_NAME=$(python3 -c "
import json, sys
try:
    with open('INPUT_user/secretome_filter_manifest.json') as f:
        d = json.load( f )
    print( d.get( 'output_name', '' ) or '' )
except Exception:
    print( '' )
" 2>/dev/null)

LAST_NNN=$(ls "${OUTPUT_TO_INPUT_DIR}/" 2>/dev/null \
    | grep -oE '_secretome_[0-9]+' \
    | sed -E 's/^_secretome_0*//' \
    | sort -n | tail -1)
NEXT_NNN=$(printf "%03d" $((${LAST_NNN:-0} + 1)))
if [ -n "${USER_OUTPUT_NAME}" ]; then
    RUN_LABEL="secretome_${NEXT_NNN}_${USER_OUTPUT_NAME}"
else
    RUN_LABEL="secretome_${NEXT_NNN}"
fi

echo "========================================================================"
echo "Starting STEP_2 — filter_secretome pipeline"
echo "  Run label:           ${RUN_LABEL}"
echo "  Last counter found:  ${LAST_NNN:-0}"
echo "  Output name suffix:  ${USER_OUTPUT_NAME:-(none)}"
echo "========================================================================"

# =============================================================================
# Build .params.json (YAML pass-through + run_label override)
# =============================================================================

RESUME=$(read_config "resume" "false")
RESUME_FLAG=""
if [ "${RESUME}" == "true" ]; then
    RESUME_FLAG="-resume"
    echo "  resume: enabled (using NextFlow work/ cache)"
fi

python3 <<PYTHON_DUMP
import yaml, json
with open( 'START_HERE-user_config.yaml' ) as f:
    cfg = yaml.safe_load( f )
cfg[ 'run_label' ] = '${RUN_LABEL}'
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

# =============================================================================
# Symlinks: OUTPUT_pipeline/3-output/ → output_to_input/STEP_2-filter_secretome/
# =============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"
# Subproject root → STEP_2 dir → workflow dir is 2 levels up from workflow dir
# output_to_input is at subproject root

# Real files live at:
#   OUTPUT_pipeline/3-output/<phyloname>_<run_label>_secretome.tsv
RESULT_DIR="OUTPUT_pipeline/3-output"
SYMLINK_COUNT=0

for result_file in ${RESULT_DIR}/*_${RUN_LABEL}_secretome.tsv; do
    if [ -f "$result_file" ]; then
        filename="$(basename "$result_file")"
        # Symlink target is RELATIVE: output_to_input/STEP_2-filter_secretome/  →  ../../STEP_2-filter_secretome/<workflow>/OUTPUT_pipeline/3-output/<file>
        ln -sf "../../STEP_2-filter_secretome/${WORKFLOW_DIR_NAME}/${result_file}" "${OUTPUT_TO_INPUT_DIR}/${filename}"
        SYMLINK_COUNT=$((SYMLINK_COUNT + 1))
    fi
done

# Also symlink the validated manifest snapshot for provenance
VALIDATED_MANIFEST="OUTPUT_pipeline/1-output/${RUN_LABEL}_validated_manifest.json"
if [ -f "$VALIDATED_MANIFEST" ]; then
    ln -sf "../../STEP_2-filter_secretome/${WORKFLOW_DIR_NAME}/${VALIDATED_MANIFEST}" \
           "${OUTPUT_TO_INPUT_DIR}/${RUN_LABEL}_validated_manifest.json"
    SYMLINK_COUNT=$((SYMLINK_COUNT + 1))
fi

echo "  Created ${SYMLINK_COUNT} symlinks in ${OUTPUT_TO_INPUT_DIR}/"

echo ""
echo "========================================================================"
echo "SUCCESS! STEP_2 filter_secretome pipeline complete."
echo "  Run label:    ${RUN_LABEL}"
echo "  Per-species:  OUTPUT_pipeline/3-output/*_${RUN_LABEL}_secretome.tsv"
echo "  Downstream:   ${OUTPUT_TO_INPUT_DIR}/"
echo "========================================================================"
echo "Completed: $(date)"

conda deactivate 2>/dev/null || true
