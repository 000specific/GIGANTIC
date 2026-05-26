#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 30 | Purpose: Run STEP_0 HGNC gene group RGS generation Nextflow pipeline
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh
# =============================================================================
# Runs the STEP_0 HGNC Gene Group RGS Generation Nextflow pipeline.
# Supports both local and SLURM execution via START_HERE-user_config.yaml.
#
# Usage:
#   bash RUN-workflow.sh
#
# Set execution_mode in START_HERE-user_config.yaml:
#   "local" - runs directly on this machine
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
# levels up is the instance dir (e.g. gene_groups-hugo_hgnc, or a user-list
# instance like gene_groups-snap_family). Derived dynamically so this script
# works for every instance of gene_groups_hgnc-COPYME, not just hugo_hgnc.
STEP_NAME="$( basename "$( cd "${SCRIPT_DIR}/.." && pwd )" )"
INSTANCE_NAME="$( basename "$( cd "${SCRIPT_DIR}/../.." && pwd )" )"

# Refuse to run from the template directly; users must instantiate first.
if [[ "${INSTANCE_NAME}" == *COPYME* ]]; then
    echo "ERROR: Refusing to run from a template directory."
    echo "  Detected instance name: ${INSTANCE_NAME}"
    echo ""
    echo "Copy this template to a real instance, e.g.:"
    echo "  cp -r ../../../${INSTANCE_NAME} ../../../gene_groups-<your_name>"
    echo "Then run from inside the new instance's workflow dir."
    exit 1
fi

# ============================================================================
# Activate GIGANTIC Environment (on-demand creation)
# ============================================================================
# The environment is auto-created on first RUN_1 run from the yml spec
# colocated at ai/conda_environment.yml. mamba is preferred (much faster);
# conda is the fallback if mamba is not available.

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
# Uses grep to parse flat YAML keys (no Python dependency required).

read_config() {
    # Read a flat YAML key from START_HERE-user_config.yaml (no Python dependency)
    local value=$(grep "^${1}:" START_HERE-user_config.yaml 2>/dev/null | head -1 | sed 's/^[^:]*: *//' | sed 's/^"//;s/"$//')
    echo "${value:-$2}"
}

EXECUTION_MODE=$(read_config "execution_mode" "local")

# ============================================================================
# SLURM submission (if execution_mode is "slurm" and not already inside a job)
# ============================================================================

if [ "${EXECUTION_MODE}" == "slurm" ] && [ -z "${SLURM_JOB_ID}" ]; then
    echo "Execution mode: SLURM (submitting job)"
    echo ""

    # Read resources and SLURM settings from config
    SLURM_CPUS=$(read_config "cpus" "4")
    SLURM_MEM=$(read_config "memory_gb" "16")
    SLURM_TIME=$(read_config "time_hours" "1")
    SLURM_ACCOUNT=$(read_config "slurm_account" "")
    SLURM_QOS=$(read_config "slurm_qos" "")

    mkdir -p slurm_logs

    SBATCH_ARGS="--job-name=hgnc_gene_groups"
    SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${SLURM_CPUS}"
    SBATCH_ARGS="${SBATCH_ARGS} --mem=${SLURM_MEM}gb"
    SBATCH_ARGS="${SBATCH_ARGS} --time=${SLURM_TIME}:00:00"
    SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/hgnc_gene_groups-%j.log"

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
echo "Starting STEP_0 HGNC Gene Group RGS Generation Pipeline"
echo "========================================================================"

# Optionally resume from cached work/ if user enabled it in config
RESUME=$(read_config "resume" "false")
RESUME_FLAG=""
if [ "${RESUME}" == "true" ]; then
    RESUME_FLAG="-resume"
    echo "  resume: enabled (using NextFlow work/ cache)"
fi

# Flatten START_HERE-user_config.yaml → .params.json for nextflow -params-file.
# Compatible with nextflow 26.x strict-mode config parser (no Groovy `import` in nextflow.config).
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
    'human_proteome_path': resolve(cfg.get('inputs', {}).get('human_proteome_path')),
    'output_dir': cfg.get('output', {}).get('base_dir', 'OUTPUT_pipeline'),
    'cpus': cfg.get('cpus', 4),
    'memory_gb': cfg.get('memory_gb', 16),
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
# Real files live in this workflow's OUTPUT_pipeline/N-output/ (created by
# NextFlow above). Symlinks are organized at the subproject-root
# output_to_input/ in two scopes:
#
#   1. Subproject-level (shared across instances) for HGNC reference data:
#        ../../../output_to_input/hugo_hgnc_database/hgnc_complete_set.txt
#      Consumed by the sibling workflow-COPYME-hgnc_user_list to resolve user
#      symbols to UniProt accessions without re-downloading HGNC.
#
#   2. Per-instance for this workflow's RGS FASTAs and manifests:
#        ../../../output_to_input/${INSTANCE_NAME}/${STEP_NAME}/...
#      Consumed by STEP_1 (homolog discovery).
#
# Symlink targets are RELATIVE paths from the symlink location back to the
# real files in OUTPUT_pipeline/. ${INSTANCE_NAME} and ${STEP_NAME} are
# derived from the directory hierarchy at the top of this script.
# ============================================================================

echo ""
echo "Creating symlinks for downstream workflows..."

WORKFLOW_DIR_NAME="$( basename "${SCRIPT_DIR}" )"

# --- 1. Subproject-level: HGNC reference data (hgnc_complete_set.txt) ---
HGNC_REF_SYMLINK_DIR="../../../output_to_input/hugo_hgnc_database"
mkdir -p "${HGNC_REF_SYMLINK_DIR}"

if [ -f "OUTPUT_pipeline/0-output/hgnc_complete_set.txt" ]; then
    ln -sf "../../${INSTANCE_NAME}/${STEP_NAME}/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/0-output/hgnc_complete_set.txt" \
        "${HGNC_REF_SYMLINK_DIR}/hgnc_complete_set.txt"
    echo "  hgnc_complete_set.txt symlink created (subproject reference)"
fi

# --- 2. Per-instance: RGS FASTAs + manifests ---
SYMLINK_DIR="../../../output_to_input/${INSTANCE_NAME}/${STEP_NAME}"
mkdir -p "${SYMLINK_DIR}/rgs_fastas"

# Clean old symlinks (only the symlinks themselves, not the subdir structure)
find "${SYMLINK_DIR}/rgs_fastas" -type l -delete 2>/dev/null
find "${SYMLINK_DIR}" -maxdepth 1 -type l -delete 2>/dev/null

# Symlink each RGS FASTA file (flat - no subdirectories)
if [ -d "OUTPUT_pipeline/3-output/rgs_fastas" ]; then
    for rgs_file in OUTPUT_pipeline/3-output/rgs_fastas/*.aa; do
        [ -f "$rgs_file" ] || continue
        FILENAME=$( basename "$rgs_file" )

        ln -sf "../../../../${INSTANCE_NAME}/${STEP_NAME}/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/3-output/rgs_fastas/${FILENAME}" \
            "${SYMLINK_DIR}/rgs_fastas/${FILENAME}"
    done

    RGS_COUNT=$( ls OUTPUT_pipeline/3-output/rgs_fastas/*.aa 2>/dev/null | wc -l )
    echo "  RGS FASTA symlinks created: ${RGS_COUNT} gene groups"
fi

# Symlink the summary and manifest TSVs
for tsv_file in OUTPUT_pipeline/3-output/3_ai-rgs_generation_summary.tsv \
                OUTPUT_pipeline/3-output/3_ai-rgs_generation_manifest.tsv; do
    if [ -f "$tsv_file" ]; then
        FILENAME=$( basename "$tsv_file" )
        ln -sf "../../../${INSTANCE_NAME}/${STEP_NAME}/${WORKFLOW_DIR_NAME}/${tsv_file}" \
            "${SYMLINK_DIR}/${FILENAME}"
        echo "  ${FILENAME} symlink created"
    fi
done

echo ""
echo "========================================================================"
echo "SUCCESS! STEP_0 pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/0-output/  (HGNC complete_set TSV; shared reference)"
echo "  OUTPUT_pipeline/1-output/  (downloaded HGNC gene-group data)"
echo "  OUTPUT_pipeline/2-output/  (aggregated gene sets)"
echo "  OUTPUT_pipeline/3-output/  (RGS FASTA files + manifest/summary)"
echo ""
echo "Downstream symlinks:"
echo "  ../../../output_to_input/hugo_hgnc_database/hgnc_complete_set.txt"
echo "  ../../../output_to_input/${INSTANCE_NAME}/${STEP_NAME}/rgs_fastas/"
echo "  ../../../output_to_input/${INSTANCE_NAME}/${STEP_NAME}/3_ai-rgs_generation_summary.tsv"
echo "  ../../../output_to_input/${INSTANCE_NAME}/${STEP_NAME}/3_ai-rgs_generation_manifest.tsv"
echo ""
echo "Next: Use individual RGS files in STEP_1 (validation) or STEP_2 (homolog discovery)"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
