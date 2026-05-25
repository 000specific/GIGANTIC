#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 May 25 | Purpose: Run STEP_0-hgnc_based_rgs workflow-hgnc_user_list orchestrator
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh
# =============================================================================
# Resolves user-supplied human gene symbols to UniProt accessions (via local
# HGNC complete_set) and emits per-group RGS FASTAs for STEP_1.
#
# Supports both local and SLURM execution via START_HERE-user_config.yaml.
#
# Usage:
#   bash RUN-workflow.sh
#
# Set execution_mode in START_HERE-user_config.yaml:
#   "local" - runs directly on this machine (default; recommended)
#   "slurm" - submits as a SLURM job with resources from config
# =============================================================================

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Derive instance + step names from the directory hierarchy
# ============================================================================
# SCRIPT_DIR points at the workflow dir; one level up is the STEP dir; two
# levels up is the instance dir (e.g. gene_groups-snap_family). Derived
# dynamically so this script works for every instance of
# gene_groups_hgnc-COPYME, not just hugo_hgnc.
STEP_NAME="$( basename "$( cd "${SCRIPT_DIR}/.." && pwd )" )"
INSTANCE_NAME="$( basename "$( cd "${SCRIPT_DIR}/../.." && pwd )" )"

# Refuse to run from the template directly; users must instantiate first.
if [[ "${INSTANCE_NAME}" == *COPYME* ]]; then
    echo "ERROR: Refusing to run from a template directory."
    echo "  Detected instance name: ${INSTANCE_NAME}"
    echo ""
    echo "Copy this template to a real instance, e.g.:"
    echo "  cp -r ../../../${INSTANCE_NAME} ../../../gene_groups-<your_name>"
    echo "Then edit INPUT_user/user_gene_set.tsv and run from inside the new"
    echo "instance's workflow dir."
    exit 1
fi

# ============================================================================
# Activate GIGANTIC Environment (on-demand creation)
# ============================================================================
# Shared env across workflow-hgnc_database and workflow-hgnc_user_list under
# this STEP. Auto-created on first run from ai/conda_environment.yml; mamba
# preferred, conda fallback.

# Disable NextFlow telemetry/update checks (prevents curl hangs on compute nodes)
export NXF_OFFLINE=true

ENV_NAME="aiG-trees_gene_groups-hgnc_based_rgs"
ENV_YML="ai/conda_environment.yml"

module load conda 2>/dev/null || true

if ! type conda &>/dev/null; then
    echo "ERROR: conda is not available."
    echo "On HPC (HiPerGator): module load conda"
    exit 1
fi

if ! conda env list 2>/dev/null | grep -q "^${ENV_NAME} "; then
    echo "Conda env '${ENV_NAME}' not found. Creating once from ${ENV_YML}..."
    if [ ! -f "${ENV_YML}" ]; then
        echo "ERROR: Environment spec not found at: ${ENV_YML}"
        exit 1
    fi
    if command -v mamba &>/dev/null; then
        mamba env create -f "${ENV_YML}" -y
    else
        conda env create -f "${ENV_YML}" -y
    fi
fi

if conda activate "${ENV_NAME}" 2>/dev/null; then
    echo "Activated conda environment: ${ENV_NAME}"
else
    echo "WARNING: Could not activate '${ENV_NAME}'. Continuing with current environment."
fi

if ! command -v nextflow &> /dev/null; then
    echo "NextFlow not found in env. Trying system module..."
    module load nextflow 2>/dev/null || true
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: NextFlow not available." >&2
        exit 1
    fi
fi
echo "NextFlow available"
echo ""

# ============================================================================
# Read execution mode from START_HERE-user_config.yaml
# ============================================================================

read_config() {
    # Read a flat YAML key (no Python dependency). Strip comment first, then quotes.
    local value=$(grep "^${1}:" START_HERE-user_config.yaml 2>/dev/null | head -1 | sed 's/^[^:]*: *//' | sed 's/#.*$//' | sed 's/[[:space:]]*$//' | sed 's/^"//;s/"$//')
    echo "${value:-$2}"
}

EXECUTION_MODE=$(read_config "execution_mode" "local")

# ============================================================================
# SLURM submission (if execution_mode is "slurm" and not already inside a job)
# ============================================================================

if [ "${EXECUTION_MODE}" == "slurm" ] && [ -z "${SLURM_JOB_ID}" ]; then
    echo "Execution mode: SLURM (submitting job)"
    echo ""

    SLURM_CPUS=$(read_config "cpus" "2")
    SLURM_MEM=$(read_config "memory_gb" "4")
    SLURM_TIME=$(read_config "time_hours" "1")
    SLURM_ACCOUNT=$(read_config "slurm_account" "")
    SLURM_QOS=$(read_config "slurm_qos" "")

    mkdir -p slurm_logs

    SBATCH_ARGS="--job-name=hgnc_user_list"
    SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${SLURM_CPUS}"
    SBATCH_ARGS="${SBATCH_ARGS} --mem=${SLURM_MEM}gb"
    SBATCH_ARGS="${SBATCH_ARGS} --time=${SLURM_TIME}:00:00"
    SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/hgnc_user_list-%j.log"

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
    conda deactivate 2>/dev/null || true
    exit 0
fi

# ============================================================================
# Run Nextflow pipeline (local execution or inside SLURM job)
# ============================================================================

if [ -n "${SLURM_JOB_ID}" ]; then
    echo "Running inside SLURM job ${SLURM_JOB_ID}"
else
    echo "Execution mode: local"
fi

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
echo "Starting STEP_0-hgnc_based_rgs workflow-hgnc_user_list pipeline"
echo "========================================================================"

RESUME=$(read_config "resume" "false")
RESUME_FLAG=""
if [ "${RESUME}" == "true" ]; then
    RESUME_FLAG="-resume"
    echo "  resume: enabled (using NextFlow work/ cache)"
fi

# Flatten START_HERE-user_config.yaml → .params.json for nextflow -params-file.
python3 - <<'PYTHON_FLATTEN'
import yaml, json
from pathlib import Path
WORKFLOW_ROOT = Path('.').resolve()
with open('START_HERE-user_config.yaml') as f:
    cfg = yaml.safe_load(f)
def resolve(rel):
    if rel is None: return None
    return str((WORKFLOW_ROOT / rel).resolve())
flat = {
    'user_gene_set_file': resolve(cfg.get('inputs', {}).get('user_gene_set_file')),
    'output_dir': cfg.get('output', {}).get('base_dir', 'OUTPUT_pipeline'),
    'cpus': cfg.get('cpus', 2),
    'memory_gb': cfg.get('memory_gb', 4),
    'time_hours': cfg.get('time_hours', 1),
}
with open('.params.json', 'w') as f:
    json.dump(flat, f, indent=2)
print(f"Wrote .params.json with {len(flat)} keys")
PYTHON_FLATTEN

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
# Create symlinks for output_to_input (subproject root)
# ============================================================================
# Two scopes:
#   1. Subproject-level (shared) HGNC reference:
#        ../../../output_to_input/hugo_hgnc_database/hgnc_complete_set.txt
#   2. Per-instance RGS FASTAs + manifest:
#        ../../../output_to_input/${INSTANCE_NAME}/${STEP_NAME}/...
#      (Same target as workflow-hgnc_database — STEP_1 reads from a single
#       canonical path regardless of which workflow produced the RGS.)
# ============================================================================

echo ""
echo "Creating symlinks for downstream workflows..."

WORKFLOW_DIR_NAME="$( basename "${SCRIPT_DIR}" )"

# --- 1. Subproject-level: HGNC reference data ---
HGNC_REF_SYMLINK_DIR="../../../output_to_input/hugo_hgnc_database"
mkdir -p "${HGNC_REF_SYMLINK_DIR}"

if [ -f "OUTPUT_pipeline/0-output/hgnc_complete_set.txt" ]; then
    ln -sf "../../${INSTANCE_NAME}/${STEP_NAME}/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/0-output/hgnc_complete_set.txt" \
        "${HGNC_REF_SYMLINK_DIR}/hgnc_complete_set.txt"
    echo "  hgnc_complete_set.txt symlink created (subproject reference)"
fi

# --- 2. Per-instance: RGS FASTAs + manifest ---
SYMLINK_DIR="../../../output_to_input/${INSTANCE_NAME}/${STEP_NAME}"
mkdir -p "${SYMLINK_DIR}/rgs_fastas"

# Clean old symlinks (only the symlinks themselves)
find "${SYMLINK_DIR}/rgs_fastas" -type l -delete 2>/dev/null
find "${SYMLINK_DIR}" -maxdepth 1 -type l -delete 2>/dev/null

# Symlink each RGS FASTA file (flat - no subdirectories)
if [ -d "OUTPUT_pipeline/2-output/rgs_fastas" ]; then
    for rgs_file in OUTPUT_pipeline/2-output/rgs_fastas/*.aa; do
        [ -f "$rgs_file" ] || continue
        FILENAME=$( basename "$rgs_file" )

        ln -sf "../../../../${INSTANCE_NAME}/${STEP_NAME}/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/2-output/rgs_fastas/${FILENAME}" \
            "${SYMLINK_DIR}/rgs_fastas/${FILENAME}"
    done

    RGS_COUNT=$( ls OUTPUT_pipeline/2-output/rgs_fastas/*.aa 2>/dev/null | wc -l )
    echo "  RGS FASTA symlinks created: ${RGS_COUNT} gene groups"
fi

# Symlink the per-group summary (STEP_1 reads this), the per-gene manifest, and the
# resolved-symbols audit trail.
for tsv_file in OUTPUT_pipeline/2-output/2_ai-rgs_generation_summary.tsv \
                OUTPUT_pipeline/2-output/2_ai-rgs_generation_manifest.tsv \
                OUTPUT_pipeline/1-output/1_ai-resolved_symbols.tsv; do
    if [ -f "$tsv_file" ]; then
        FILENAME=$( basename "$tsv_file" )
        ln -sf "../../../${INSTANCE_NAME}/${STEP_NAME}/${WORKFLOW_DIR_NAME}/${tsv_file}" \
            "${SYMLINK_DIR}/${FILENAME}"
        echo "  ${FILENAME} symlink created"
    fi
done

echo ""
echo "========================================================================"
echo "SUCCESS! STEP_0-hgnc_based_rgs workflow-hgnc_user_list complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/0-output/  (HGNC complete_set TSV; shared reference)"
echo "  OUTPUT_pipeline/1-output/  (resolved symbols → UniProt manifest)"
echo "  OUTPUT_pipeline/2-output/  (RGS FASTA files + generation manifest)"
echo ""
echo "Downstream symlinks:"
echo "  ../../../output_to_input/hugo_hgnc_database/hgnc_complete_set.txt"
echo "  ../../../output_to_input/${INSTANCE_NAME}/${STEP_NAME}/rgs_fastas/"
echo "  ../../../output_to_input/${INSTANCE_NAME}/${STEP_NAME}/1_ai-resolved_symbols.tsv"
echo "  ../../../output_to_input/${INSTANCE_NAME}/${STEP_NAME}/2_ai-rgs_generation_manifest.tsv"
echo ""
echo "Next: Use individual RGS files in STEP_1 (homolog discovery)."
echo "========================================================================"
echo "Completed: $(date)"
