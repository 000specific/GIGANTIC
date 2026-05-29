#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 May 29 | Purpose: One-script entry point for the Phyloname Tree Generator toolkit
# Human: Eric Edsinger
# =============================================================================
# RUN-workflow.sh - Phyloname Tree Generator toolkit
# =============================================================================
# Canonical entry per GIGANTIC §29. Reads START_HERE-user_config.yaml and:
#   1. Refuses to run from a *COPYME* directory (§35; instantiate first).
#   2. Auto-creates the conda env `aiG-research_ai-phyloname_tree_generator`
#      on first run from ai/conda_environment.yml (§28).
#   3. Resolves config -> .params.json and invokes ai/main.nf via NextFlow.
#   4. (Optionally) self-submits to SLURM if execution_mode is "slurm".
#      Default execution_mode is "local" — this is a lightweight tool.
# =============================================================================

set -uo pipefail
# Note: not -e because we want explicit handling of NextFlow's exit code.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# -----------------------------------------------------------------------------
# COPYME guard
# -----------------------------------------------------------------------------
case "$( basename "${SCRIPT_DIR}" )" in
    *COPYME*)
        echo "ERROR: this script must be run from a RUN-instance directory, not the COPYME template."
        echo ""
        echo "  Current dir: ${SCRIPT_DIR}"
        echo ""
        echo "Copy first, then run:"
        echo "  cp -r toolkit-COPYME-phyloname_tree_generator toolkit-RUN_1-phyloname_tree_generator"
        echo "  cd toolkit-RUN_1-phyloname_tree_generator"
        echo "  bash RUN-workflow.sh"
        exit 1
        ;;
esac

CONFIG_YAML="START_HERE-user_config.yaml"
if [ ! -f "${CONFIG_YAML}" ]; then
    echo "ERROR: ${CONFIG_YAML} not found in $( pwd )"
    exit 1
fi

# -----------------------------------------------------------------------------
# Read top-level YAML scalars needed BEFORE the conda env activates.
# -----------------------------------------------------------------------------
read_yaml_scalar() {
    local key="$1"
    grep -E "^${key}:" "${CONFIG_YAML}" 2>/dev/null \
        | head -1 \
        | sed -E 's/^[^:]*:[[:space:]]*//' \
        | sed -E 's/^"(.*)"$/\1/' \
        | sed -E "s/^'(.*)'\$/\\1/" \
        | sed -E 's/[[:space:]]+#.*$//'
}

EXECUTION_MODE=$( read_yaml_scalar 'execution_mode' )
EXECUTION_MODE="${EXECUTION_MODE:-local}"

SLURM_ACCOUNT=$( read_yaml_scalar 'slurm_account' )
SLURM_QOS=$( read_yaml_scalar 'slurm_qos' )
CPUS=$( read_yaml_scalar 'cpus' )
MEMORY_GB=$( read_yaml_scalar 'memory_gb' )
TIME_HOURS=$( read_yaml_scalar 'time_hours' )
CPUS="${CPUS:-2}"
MEMORY_GB="${MEMORY_GB:-15}"
TIME_HOURS="${TIME_HOURS:-1}"

echo '========================================================================'
echo 'Phyloname Tree Generator Toolkit'
echo '========================================================================'
echo "Started:           $( date )"
echo "Working directory: ${SCRIPT_DIR}"
echo "Execution mode:    ${EXECUTION_MODE}"
echo ""

# -----------------------------------------------------------------------------
# SLURM self-submit branch
# -----------------------------------------------------------------------------
if [ "${EXECUTION_MODE}" = "slurm" ] && [ -z "${SLURM_JOB_ID:-}" ]; then
    if [ -z "${SLURM_ACCOUNT}" ] || [ "${SLURM_ACCOUNT}" = "your_account" ]; then
        echo "ERROR: execution_mode is slurm but slurm_account is unset or placeholder."
        echo "       Edit ${CONFIG_YAML} to set slurm_account + slurm_qos."
        exit 1
    fi
    mkdir -p slurm_logs
    echo "Self-submitting to SLURM ..."
    sbatch \
        --account="${SLURM_ACCOUNT}" \
        --qos="${SLURM_QOS}" \
        --cpus-per-task="${CPUS}" \
        --mem="${MEMORY_GB}g" \
        --time="${TIME_HOURS}:00:00" \
        --job-name="phyloname_tree_generator" \
        --output="slurm_logs/phyloname_tree_generator-%j.log" \
        --wrap="bash $( realpath "$0" )"
    echo "Job submitted. Check slurm_logs/ for output."
    exit 0
fi

if [ -n "${SLURM_JOB_ID:-}" ]; then
    echo "Running inside SLURM job ${SLURM_JOB_ID}"
    echo ""
fi

# -----------------------------------------------------------------------------
# Conda env (auto-create on first run per §28)
# -----------------------------------------------------------------------------
ENV_NAME="aiG-research_ai-phyloname_tree_generator"
ENV_YML="ai/conda_environment.yml"

module load conda 2>/dev/null || true

if ! command -v conda &> /dev/null; then
    echo "ERROR: conda not found on PATH."
    echo "  On HiPerGator: module load conda"
    exit 1
fi

if ! conda env list 2>/dev/null | awk '{print $1}' | grep -q -x "${ENV_NAME}"; then
    echo "Environment '${ENV_NAME}' not found. Creating from ${ENV_YML} (one-time)..."
    if [ ! -f "${ENV_YML}" ]; then
        echo "ERROR: ${ENV_YML} not found."
        exit 1
    fi
    if command -v mamba &> /dev/null; then
        mamba env create -f "${ENV_YML}" -y
    else
        conda env create -f "${ENV_YML}" -y
    fi
    echo "Environment '${ENV_NAME}' created."
    echo ""
fi

# shellcheck disable=SC1091
source "$( conda info --base )/etc/profile.d/conda.sh" 2>/dev/null || true
if conda activate "${ENV_NAME}" 2>/dev/null; then
    echo "Activated conda environment: ${ENV_NAME}"
else
    echo "WARNING: Could not activate '${ENV_NAME}'; continuing with current shell env."
fi

if ! command -v nextflow &> /dev/null; then
    echo "ERROR: nextflow not on PATH after activating ${ENV_NAME}."
    exit 1
fi
echo "  nextflow: $( nextflow -version 2>&1 | grep -i 'version' | head -1 )"

# -----------------------------------------------------------------------------
# Resume?
# -----------------------------------------------------------------------------
RESUME_VAL=$( read_yaml_scalar 'resume' )
RESUME_FLAG=""
if [ "${RESUME_VAL}" = "true" ]; then
    RESUME_FLAG="-resume"
    echo "Resume enabled (using NextFlow work/ cache)"
fi

# -----------------------------------------------------------------------------
# Flatten YAML -> .params.json and resolve relative paths to absolute
# -----------------------------------------------------------------------------
python3 <<'PYTHON_DUMP'
import json, os
from pathlib import Path
import yaml

with open( "START_HERE-user_config.yaml" ) as f:
    cfg = yaml.safe_load( f ) or {}

inputs = cfg.get( "inputs", {} ) or {}
output = cfg.get( "output", {} ) or {}
project = cfg.get( "project", {} ) or {}

def resolve( rel ):
    if rel is None or str( rel ).strip() == "":
        return None
    p = Path( rel )
    if p.is_absolute():
        return str( p )
    return str( ( Path.cwd() / p ).resolve() )

flat = {
    "phylonames":                     resolve( inputs.get( "phylonames" ) ),
    "config_file":                    resolve( inputs.get( "config_file" ) ),
    "trees_species_input_user_dir":   resolve( inputs.get( "trees_species_input_user_dir" ) ),
    "prefix":                         cfg.get( "prefix", "species_tree" ),
    "seed":                           int( cfg.get( "seed", 42 ) ),
    "output_dir":                     output.get( "base_dir", "OUTPUT_pipeline" ),
    "project_name":                   project.get( "name", "gigantic_project" ),
}

with open( ".params.json", "w" ) as f:
    json.dump( flat, f, indent = 2 )

print( f"  wrote .params.json with {len(flat)} keys" )
PYTHON_DUMP

mkdir -p .nextflow

echo ""
echo "Running NextFlow pipeline..."
nextflow run ai/main.nf ${RESUME_FLAG} \
    -c ai/nextflow.config \
    -params-file .params.json
EXIT_CODE=$?

echo ""
echo '========================================================================'
if [ "${EXIT_CODE}" -eq 0 ]; then
    echo 'SUCCESS! Phyloname Tree Generator completed.'
    echo ""
    echo "Outputs:"
    echo "  OUTPUT_pipeline/1-output/  (per-species TSVs + extraction log)"
    echo "  OUTPUT_pipeline/2-output/  (validation summary + log)"
    echo "  OUTPUT_pipeline/3-output/  (bridge log)"
    echo ""
    echo "Downstream symlinks:"
    echo "  <hotspots_gene_coordinates_dir>/<Genus_species>-gene_coordinates.tsv"
    echo "    -> $( pwd )/OUTPUT_pipeline/1-output/<Genus_species>-gene_coordinates.tsv"
    echo ""
    echo "Audit log: ai/logs/run_<timestamp>-subproject-hotspots_success.log"
else
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "See trace above + .nextflow.log for details."
fi
echo '========================================================================'
echo "Completed: $( date )"
exit "${EXIT_CODE}"
