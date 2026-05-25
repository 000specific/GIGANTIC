#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 09 | Purpose: Run NCBI nr BLAST protein database build Nextflow pipeline
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh
# =============================================================================
# Downloads the NCBI nr protein FASTA and builds a BLAST protein database
# using makeblastdb for downstream BLASTp homology searches.
#
# PURPOSE:
#   Download NCBI nr FASTA, decompress, build BLAST protein database,
#   validate, and create symlinks for downstream subprojects.
#
# USAGE:
#   bash RUN-workflow.sh
#
# FOR SLURM CLUSTERS:
# Edit START_HERE-user_config.yaml: set execution_mode: "slurm"
# Then run: bash RUN-workflow.sh  (this script self-submits to SLURM)
#
# BEFORE RUNNING:
#   1. Edit START_HERE-user_config.yaml
#   2. Ensure sufficient disk space (~300 GB)
#   3. Ensure sufficient memory (~100 GB for makeblastdb)
#
# WHAT THIS DOES:
#   1. Downloads NCBI nr.gz from NCBI FTP (~100 GB compressed)
#   2. Decompresses and builds BLAST protein database with makeblastdb
#   3. Validates database with blastdbcmd -info
#   4. Writes timestamped run log
#   5. Creates symlinks in output_to_input/BLOCK_ncbi_nr_blastp/
# =============================================================================

set -e

echo "========================================================================"
echo "Starting NCBI nr BLAST Protein Database Pipeline"
echo "========================================================================"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Read execution mode from START_HERE-user_config.yaml
# ============================================================================
# Uses grep to parse flat YAML keys (no Python dependency required at this
# stage — conda env may not yet exist).

read_config() {
    local value=$(grep "^${1}:" START_HERE-user_config.yaml 2>/dev/null | head -1 | sed 's/^[^:]*: *//' | sed 's/^"//;s/"$//')
    echo "${value:-$2}"
}

EXECUTION_MODE=$(read_config "execution_mode" "local")

# ============================================================================
# SLURM self-submit (if execution_mode=slurm and not already inside a SLURM job)
# ============================================================================

if [ "${EXECUTION_MODE}" == "slurm" ] && [ -z "${SLURM_JOB_ID}" ]; then
    echo "Execution mode: SLURM (submitting job)"
    echo ""

    SLURM_CPUS=$(read_config "cpus" "15")
    SLURM_MEM=$(read_config "memory_gb" "100")
    SLURM_TIME=$(read_config "time_hours" "72")
    SLURM_ACCOUNT=$(read_config "slurm_account" "")
    SLURM_QOS=$(read_config "slurm_qos" "")

    mkdir -p slurm_logs

    SBATCH_ARGS="--job-name=ncbi_nr_blastp"
    SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${SLURM_CPUS}"
    SBATCH_ARGS="${SBATCH_ARGS} --mem=${SLURM_MEM}gb"
    SBATCH_ARGS="${SBATCH_ARGS} --time=${SLURM_TIME}:00:00"
    SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/ncbi_nr_blastp-%j.log"

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

# ============================================================================
# Activate GIGANTIC Environment (on-demand creation)
# ============================================================================
# GIGANTIC env naming convention: aiG-<subproject>-<block_or_step>-<optional_details>
# Subproject-shared env: BOTH public_databases BLOCKs (ncbi_nr_blastp + ncbi_nr_diamond)
# use the same env (whichever runs first auto-creates it; the other reuses it).
ENV_NAME="aiG-public_databases"
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
# Run Nextflow Pipeline
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
# Real files live in OUTPUT_pipeline/N-output/ (created by NextFlow above).
# Symlinks are created in ONE location at the subproject root:
#   ../../output_to_input/BLOCK_ncbi_nr_blastp/
#
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

# --- Subproject-root output_to_input (single canonical location) ---
SUBPROJECT_SHARED_DIR="../../output_to_input/BLOCK_ncbi_nr_blastp"
mkdir -p "${SUBPROJECT_SHARED_DIR}"
find "${SUBPROJECT_SHARED_DIR}" -type l -delete 2>/dev/null || true

# --- Create relative symlinks for BLAST database files ---
# Real files: OUTPUT_pipeline/2-output/nr.*
RESULT_DIR="OUTPUT_pipeline/2-output"
SYMLINK_COUNT=0

for database_file in ${RESULT_DIR}/nr.p*; do
    if [ -f "$database_file" ]; then
        filename="$(basename "$database_file")"
        ln -sf "../../BLOCK_ncbi_nr_blastp/${WORKFLOW_DIR_NAME}/${database_file}" "${SUBPROJECT_SHARED_DIR}/${filename}"
        SYMLINK_COUNT=$((SYMLINK_COUNT + 1))
    fi
done

echo "  Created ${SYMLINK_COUNT} symlinks in output_to_input/BLOCK_ncbi_nr_blastp/"

if [ $SYMLINK_COUNT -eq 0 ]; then
    echo "  WARNING: No BLAST database files found in ${RESULT_DIR}/"
    echo "  The pipeline may have produced no outputs."
fi

echo ""
echo "========================================================================"
echo "SUCCESS! NCBI nr BLAST Protein Database Pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/"
echo ""
echo "Downstream symlinks:"
echo "  output_to_input/BLOCK_ncbi_nr_blastp/  (subproject root)"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
