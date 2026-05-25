#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 09 | Purpose: Run NCBI nr DIAMOND database build workflow
# Human: Eric Edsinger

################################################################################
# GIGANTIC Public Databases - NCBI nr DIAMOND Database
################################################################################
#
# PURPOSE:
# Download the NCBI nr protein database and build a DIAMOND search database.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Edit START_HERE-user_config.yaml with your project settings
# 2. Ensure ~300 GB free disk space (nr.gz ~100 GB + nr.dmnd ~150 GB)
#
# FOR SLURM CLUSTERS:
# Edit START_HERE-user_config.yaml: set execution_mode: "slurm"
# Then run: bash RUN-workflow.sh  (this script self-submits to SLURM)
#
# WHAT THIS DOES:
# 1. Downloads NCBI nr protein FASTA (nr.gz, ~100 GB)
# 2. Builds DIAMOND database (nr.dmnd, ~150 GB, 1-4 hours)
# 3. Validates database integrity (sequence count, file size)
# 4. Writes timestamped run log
#
# OUTPUT:
# Your DIAMOND database will be at:
#   OUTPUT_pipeline/2-output/nr.dmnd
# And symlinked to:
#   ../../output_to_input/BLOCK_ncbi_nr_diamond/nr.dmnd
#
################################################################################

echo "========================================================================"
echo "GIGANTIC Public Databases - NCBI nr DIAMOND Database"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Read execution mode from START_HERE-user_config.yaml
# ============================================================================
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

    SBATCH_ARGS="--job-name=ncbi_nr_diamond"
    SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${SLURM_CPUS}"
    SBATCH_ARGS="${SBATCH_ARGS} --mem=${SLURM_MEM}gb"
    SBATCH_ARGS="${SBATCH_ARGS} --time=${SLURM_TIME}:00:00"
    SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/ncbi_nr_diamond-%j.log"

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
# This workflow requires:
#   - conda environment: aiG-public_databases (DIAMOND, BLAST+, Python, wget)
#   - NextFlow: from conda env OR system module
#
# The environment is created automatically on first run from the yml spec
# at ai/conda_environment.yml. mamba is preferred (much faster); conda is
# the fallback. This env is SHARED with BLOCK_ncbi_nr_blastp.
# ============================================================================

# GIGANTIC env naming convention: aiG-<subproject>-<block_or_step>-<optional_details>
ENV_NAME="aiG-public_databases"
ENV_YML="ai/conda_environment.yml"

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

# Check disk space (warn if less than 300 GB free)
FREE_SPACE_GB=$(df -BG . | tail -1 | awk '{print $4}' | tr -d 'G')
if [ "${FREE_SPACE_GB}" -lt 300 ] 2>/dev/null; then
    echo "WARNING: Only ${FREE_SPACE_GB} GB free disk space detected."
    echo "This workflow requires ~300 GB (nr.gz ~100 GB + nr.dmnd ~150 GB)."
    echo "Continuing anyway..."
    echo ""
fi

# Run NextFlow pipeline
echo "Running NextFlow pipeline..."
echo ""

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
    -params-file .params.json

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
# Symlinks are created in:
#   ../../output_to_input/BLOCK_ncbi_nr_diamond/
#
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

# Determine the workflow directory name dynamically (supports COPYME and RUN_XX instances)
WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

SHARED_DIR="../../output_to_input/BLOCK_ncbi_nr_diamond"
mkdir -p "${SHARED_DIR}"

# Remove any stale symlinks from previous runs
find "${SHARED_DIR}" -type l -delete 2>/dev/null

# Symlink the DIAMOND database from 2-output
ln -sf "../../BLOCK_ncbi_nr_diamond/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/2-output/nr.dmnd" \
    "${SHARED_DIR}/nr.dmnd"

echo "  output_to_input/BLOCK_ncbi_nr_diamond/nr.dmnd -> symlink created"

echo ""
echo "========================================================================"
echo "SUCCESS! NCBI nr DIAMOND database build complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/  Downloaded nr.gz"
echo "  OUTPUT_pipeline/2-output/  DIAMOND database (nr.dmnd)"
echo "  OUTPUT_pipeline/3-output/  Validation report"
echo "  OUTPUT_pipeline/4-output/  Run log"
echo ""
echo "Downstream symlinks:"
echo "  ../../output_to_input/BLOCK_ncbi_nr_diamond/nr.dmnd"
echo ""
echo "USAGE: diamond blastp -d OUTPUT_pipeline/2-output/nr.dmnd -q query.fasta -o results.tsv"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
