#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 10 | Purpose: Run STEP_1 RBH/RBF homolog discovery Nextflow pipeline
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh
# =============================================================================
# Runs the STEP_1 RBH/RBF homolog discovery Nextflow pipeline.
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
# Activate GIGANTIC Environment (on-demand creation)
# ============================================================================
# The environment is auto-created on first RUN_1 run from the yml spec
# colocated at ai/conda_environment.yml. mamba is preferred (much faster);
# conda is the fallback if mamba is not available.

# Disable NextFlow telemetry/update checks (prevents curl hangs on compute nodes)
export NXF_OFFLINE=true

ENV_NAME="aiG-trees_gene_families-rbh_rbf_homologs"
ENV_YML="ai/conda_environment.yml"

module load conda 2>/dev/null || true

if ! command -v conda &> /dev/null; then
    echo "ERROR: conda not found!"
    echo ""
    echo "On HPC (HiPerGator): module load conda"
    echo "Otherwise: install conda from https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Create environment on-demand if it does not exist
if ! conda env list 2>/dev/null | grep -q "^${ENV_NAME} "; then
    echo "Environment '${ENV_NAME}' not found. Creating on-demand from ${ENV_YML}..."
    echo ""
    if [ ! -f "${ENV_YML}" ]; then
        echo "ERROR: Environment spec not found at: ${ENV_YML}"
        echo "Make sure you are running from a valid GIGANTIC workflow directory."
        exit 1
    fi
    if command -v mamba &> /dev/null; then
        mamba env create -f "${ENV_YML}" -y
        CREATE_EXIT=$?
    else
        conda env create -f "${ENV_YML}" -y
        CREATE_EXIT=$?
    fi
    if [ $CREATE_EXIT -ne 0 ]; then
        echo ""
        echo "ERROR: Failed to create conda environment '${ENV_NAME}' (exit code $CREATE_EXIT)"
        echo "Check the error messages above and verify the spec at: ${ENV_YML}"
        echo ""
        echo "If a partial env was left behind, remove it before retrying:"
        echo "  mamba env remove -n ${ENV_NAME} -y"
        exit 1
    fi
    echo ""
    echo "Environment '${ENV_NAME}' created successfully."
    echo ""
fi

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
    SLURM_CPUS=$(read_config "cpus" "50")
    SLURM_MEM=$(read_config "memory_gb" "187")
    SLURM_TIME=$(read_config "time_hours" "96")
    SLURM_ACCOUNT=$(read_config "slurm_account" "")
    SLURM_QOS=$(read_config "slurm_qos" "")

    mkdir -p slurm_logs

    SBATCH_ARGS="--job-name=rbh_rbf_homologs"
    SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${SLURM_CPUS}"
    SBATCH_ARGS="${SBATCH_ARGS} --mem=${SLURM_MEM}gb"
    SBATCH_ARGS="${SBATCH_ARGS} --time=${SLURM_TIME}:00:00"
    SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/rbh_rbf_homologs-%j.log"

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

if [ ! -f "INPUT_user/species_keeper_list.tsv" ]; then
    echo "ERROR: Species keeper list not found!"
    echo "Expected: INPUT_user/species_keeper_list.tsv"
    exit 1
fi
echo "  [OK] Species keeper list found"
echo ""

echo "========================================================================"
echo "Starting STEP_1 RBH/RBF Homolog Discovery Pipeline"
echo "========================================================================"

# Optionally resume from cached work/ if user enabled it in config
RESUME=$(read_config "resume" "false")
RESUME_FLAG=""
if [ "${RESUME}" == "true" ]; then
    RESUME_FLAG="-resume"
    echo "  resume: enabled (using NextFlow work/ cache)"
fi

# Universal GIGANTIC YAML->params pattern: pass the YAML directly via
# -params-file. NextFlow loads YAML natively; all keys (cpus, memory_gb,
# inputs.*, output.*, gene_family.*, project.*, blast.*) flow through.

nextflow run ai/main.nf ${RESUME_FLAG} \
    -c ai/nextflow.config \
    -params-file START_HERE-user_config.yaml

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
# Real files live in OUTPUT_pipeline/16-output/ (created by NextFlow above).
# Symlinks are organized by gene family at the subproject-root output_to_input/:
#   ../../../output_to_input/<gene_family>/STEP_1-homolog_discovery/
#
# Structure:
#   output_to_input/
#   ├── nitric_oxide_synthases/
#   │   ├── STEP_1-homolog_discovery/   <- created here
#   │   └── STEP_2-phylogenetic_analysis/  <- created by STEP_2
#   └── innexin_pannexin/
#       ├── STEP_1-homolog_discovery/
#       └── STEP_2-phylogenetic_analysis/
#
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
# ============================================================================

echo ""
echo "Creating symlinks for downstream workflows..."

# Extract gene family name from config
GENE_FAMILY=$(grep -A5 "^gene_family:" START_HERE-user_config.yaml | grep "name:" | head -1 | sed 's/.*: *"\([^"]*\)".*/\1/')
WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"
GENE_FAMILY_DIR="$(basename "$(dirname "$(dirname "${SCRIPT_DIR}")")")"

# --- Subproject-root output_to_input ---
SYMLINK_DIR="../../../output_to_input/${GENE_FAMILY}/STEP_1-homolog_discovery"
mkdir -p "${SYMLINK_DIR}"
find "${SYMLINK_DIR}" -type l -delete 2>/dev/null

for ags_file in OUTPUT_pipeline/16-output/16_ai-ags-*.aa; do
    if [ -f "$ags_file" ]; then
        filename=$(basename "$ags_file")
        ln -sf "../../../${GENE_FAMILY_DIR}/STEP_1-homolog_discovery/${WORKFLOW_DIR_NAME}/${ags_file}" \
            "${SYMLINK_DIR}/${filename}"
    fi
done

echo "  output_to_input/${GENE_FAMILY}/STEP_1-homolog_discovery/ -> symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! STEP_1 pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/ through 16-output/"
echo ""
echo "Downstream symlinks:"
echo "  ../../../output_to_input/${GENE_FAMILY}/STEP_1-homolog_discovery/"
echo ""
echo "Next: Run STEP_2 phylogenetic analysis with AGS files"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
