#!/usr/bin/env bash
# AI: Claude Code | Opus 4.7 (1M context) | 2026 May 28 | Purpose: Unified entry point for the NCBI Genomes T1 Toolkit per gigantic_conventions.md §29 (local OR self-submit to SLURM based on execution_mode in YAML).
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh
#
# One canonical entry point per §29:
#   - bash RUN-workflow.sh
#
# Reads ./START_HERE-user_config.yaml to determine:
#   execution_mode  -- "local" | "slurm"
#   slurm_account / slurm_qos / cpus / memory_gb / time_hours  (when slurm)
#
# When execution_mode is "slurm" and we are NOT already inside a SLURM job, the
# script self-submits via sbatch and exits. The submitted instance re-enters
# this script with SLURM_JOB_ID set and proceeds to run NextFlow.
#
# This script also:
#   - Refuses to run from a *COPYME* directory (per the workflow-COPYME / RUN_N
#     pattern documented in §35 -- the user is expected to copy the template
#     into toolkit-RUN_N-* first, then run from the RUN dir).
#   - Auto-creates the conda env `aiG-toolkit-ncbi_genomes` on first run from
#     ai/conda_environment.yml (per §28).
#   - Verifies NCBI datasets CLI is available before invoking NextFlow.
# =============================================================================

set -uo pipefail
# Note: not using -e because we want explicit handling of nextflow's exit codes.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# -----------------------------------------------------------------------------
# COPYME guard (§35: run from a RUN dir, not from the template)
# -----------------------------------------------------------------------------
case "$(basename "${SCRIPT_DIR}")" in
    *COPYME*)
        echo "ERROR: this script must be run from a RUN-instance directory, not the COPYME template."
        echo ""
        echo "  Current dir: ${SCRIPT_DIR}"
        echo ""
        echo "Copy first, then run:"
        echo "  cp -r toolkit-COPYME-ncbi_genomes_T1 toolkit-RUN_1-ncbi_genomes_T1"
        echo "  cd toolkit-RUN_1-ncbi_genomes_T1"
        echo "  bash RUN-workflow.sh"
        exit 1
        ;;
esac

CONFIG_YAML="START_HERE-user_config.yaml"
if [ ! -f "${CONFIG_YAML}" ]; then
    echo "ERROR: ${CONFIG_YAML} not found in $(pwd)"
    exit 1
fi

# -----------------------------------------------------------------------------
# Read top-level YAML scalars needed BEFORE the conda env is active.
# Just two: execution_mode (to decide local vs slurm-self-submit) and the
# slurm_account / slurm_qos / cpus / memory_gb / time_hours used to construct
# the sbatch wrapper. All other YAML values are passed to NextFlow via
# `-params-file .params.json` after the conda env activates -- see below.
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
SLURM_ACCOUNT=$(  read_yaml_scalar 'slurm_account' )
SLURM_QOS=$(      read_yaml_scalar 'slurm_qos' )
CPUS=$(           read_yaml_scalar 'cpus' )
MEMORY_GB=$(      read_yaml_scalar 'memory_gb' )
TIME_HOURS=$(     read_yaml_scalar 'time_hours' )

EXECUTION_MODE="${EXECUTION_MODE:-local}"
CPUS="${CPUS:-4}"
MEMORY_GB="${MEMORY_GB:-16}"
TIME_HOURS="${TIME_HOURS:-6}"

echo '========================================================================'
echo 'NCBI Genomes T1 Toolkit'
echo '========================================================================'
echo ""
echo "Started:           $(date)"
echo "Working directory: ${SCRIPT_DIR}"
echo "Execution mode:    ${EXECUTION_MODE}"
echo ""

# -----------------------------------------------------------------------------
# SLURM self-submit branch (§29)
# -----------------------------------------------------------------------------
if [ "${EXECUTION_MODE}" = "slurm" ] && [ -z "${SLURM_JOB_ID:-}" ]; then
    if [ -z "${SLURM_ACCOUNT}" ] || [ "${SLURM_ACCOUNT}" = "your_account" ]; then
        echo "ERROR: execution_mode is slurm but slurm_account is unset or placeholder."
        echo "       Edit ${CONFIG_YAML} to set slurm_account + slurm_qos."
        exit 1
    fi

    mkdir -p slurm_logs

    SBATCH_ARGS=(
        "--account=${SLURM_ACCOUNT}"
        "--qos=${SLURM_QOS}"
        "--cpus-per-task=${CPUS}"
        "--mem=${MEMORY_GB}g"
        "--time=${TIME_HOURS}:00:00"
        "--job-name=ncbi_genomes_T1_toolkit"
        "--output=slurm_logs/ncbi_genomes_T1_toolkit-%j.log"
    )

    echo "Self-submitting to SLURM..."
    echo "  sbatch ${SBATCH_ARGS[*]}"
    echo ""
    sbatch "${SBATCH_ARGS[@]}" --wrap="bash $( realpath "$0" )"

    echo ""
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
ENV_NAME="aiG-toolkit-ncbi_genomes"
ENV_YML="ai/conda_environment.yml"

module load conda 2>/dev/null || true

if ! command -v conda &> /dev/null; then
    echo "ERROR: conda not found on PATH."
    echo "  On HiPerGator: module load conda"
    echo "  Otherwise: install miniconda from https://docs.conda.io/en/latest/miniconda.html"
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

# `conda activate` requires the conda function in this shell, not just the binary
# shellcheck disable=SC1091
source "$( conda info --base )/etc/profile.d/conda.sh" 2>/dev/null || true
if conda activate "${ENV_NAME}" 2>/dev/null; then
    echo "Activated conda environment: ${ENV_NAME}"
else
    echo "WARNING: Could not activate '${ENV_NAME}' via conda function; continuing with current shell env."
fi

# -----------------------------------------------------------------------------
# Sanity checks: nextflow + datasets CLI
# -----------------------------------------------------------------------------
if ! command -v nextflow &> /dev/null; then
    echo "ERROR: nextflow not on PATH after activating ${ENV_NAME}."
    exit 1
fi
echo "  nextflow: $( nextflow -version 2>&1 | grep -i 'version' | head -1 )"

if ! command -v datasets &> /dev/null; then
    echo "ERROR: NCBI 'datasets' CLI not on PATH after activating ${ENV_NAME}."
    echo "       The conda env should provide ncbi-datasets-cli."
    exit 1
fi
echo "  datasets: $( datasets --version 2>&1 )"

# -----------------------------------------------------------------------------
# Manifest sanity check (using the YAML's toolkit.manifest_path, not hardcoded)
# -----------------------------------------------------------------------------
MANIFEST_PATH=$( python3 -c "
import yaml
with open('${CONFIG_YAML}') as f:
    cfg = yaml.safe_load(f)
print(cfg.get('toolkit', {}).get('manifest_path') or 'INPUT_user/ncbi_genomes_manifest.tsv')
" )

if [ ! -f "${MANIFEST_PATH}" ]; then
    echo ""
    echo "ERROR: Manifest not found: ${MANIFEST_PATH}"
    echo "       Create it (2-column TSV: genus_species<TAB>accession)."
    exit 1
fi
SPECIES_COUNT=$( grep -v '^#' "${MANIFEST_PATH}" | grep -v '^genus_species' | grep -v '^[[:space:]]*$' | wc -l )
echo ""
echo "Species in manifest: ${SPECIES_COUNT}"
echo ""

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
# Flatten START_HERE-user_config.yaml -> .params.json for NextFlow -params-file
# -----------------------------------------------------------------------------
# Universal GIGANTIC YAML->params pattern: pass-through json.dump (no flatten).
# Resolves toolkit.download_date 'auto' -> 'downloaded_YYYYMMDD' before dump.

python3 <<'PYTHON_DUMP'
import yaml, json, datetime

with open( 'START_HERE-user_config.yaml' ) as input_yaml:
    cfg = yaml.safe_load( input_yaml ) or {}

# Resolve toolkit.download_date: 'auto' / blank -> today; bare YYYYMMDD -> prefix.
toolkit = cfg.setdefault( 'toolkit', {} )
dd = toolkit.get( 'download_date' )
if dd is None or str( dd ).strip() == '' or str( dd ).lower() == 'auto':
    dd_resolved = 'downloaded_' + datetime.date.today().strftime( '%Y%m%d' )
elif not str( dd ).startswith( 'downloaded_' ):
    dd_resolved = 'downloaded_' + str( dd )
else:
    dd_resolved = str( dd )
toolkit[ 'download_date' ] = dd_resolved

with open( '.params.json', 'w' ) as output_json:
    json.dump( cfg, output_json, indent = 2 )
PYTHON_DUMP

mkdir -p .nextflow

echo "Running NextFlow pipeline..."
echo "  Config: START_HERE-user_config.yaml -> .params.json -> -params-file"
echo ""
nextflow run ai/main.nf ${RESUME_FLAG} \
    -params-file .params.json
EXIT_CODE=$?

echo ""
echo '========================================================================'
if [ $EXIT_CODE -eq 0 ]; then
    echo 'SUCCESS! Toolkit completed.'
    echo ""
    echo "Outputs at:"
    echo "  OUTPUT_pipeline/3-output/        (real GIGANTIC-named files)"
    echo "  ../output_to_input/              (parent stable-name symlinks)"
    echo "  ../../../../../INPUT_user/genomic_resources/"
    echo "                                   (project INPUT_user symlinks)"
    echo ""
    echo "Audit log:"
    echo "  ai/logs/run_<timestamp>-ncbi_genomes_T1_toolkit_success.log"
else
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "See the trace above + .nextflow.log for details."
fi
echo '========================================================================'
echo "Completed: $(date)"
exit $EXIT_CODE
