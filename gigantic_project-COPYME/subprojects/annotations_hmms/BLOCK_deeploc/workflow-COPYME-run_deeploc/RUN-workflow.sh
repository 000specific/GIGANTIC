#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 10 | Purpose: Run DeepLoc Nextflow pipeline
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh
# =============================================================================
# Runs the DeepLoc annotation Nextflow pipeline.
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
# Activate GIGANTIC Environment
# ============================================================================

module load conda 2>/dev/null || true

if conda activate ai_gigantic_deeploc 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_deeploc"
    # Ensure conda's libstdc++ is found (needed for PyTorch/DeepLoc2)
    export LD_LIBRARY_PATH="${CONDA_PREFIX}/lib:${LD_LIBRARY_PATH}"
else
    echo "WARNING: Environment 'ai_gigantic_deeploc' not found."
    echo ""
    echo "Please run the environment setup script first:"
    echo "  cd ../../../../  # Go to project root"
    echo "  bash RUN-setup_environments.sh"
    echo ""
    echo "Or create this environment manually:"
    echo "  mamba env create -f ../../../../conda_environments/ai_gigantic_deeploc.yml"
    echo ""
    exit 1
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
        echo "  1. Install nextflow in conda env: conda install -n ai_gigantic_deeploc -c bioconda nextflow"
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
    SLURM_CPUS=$(read_config "cpus" "4")
    SLURM_MEM=$(read_config "memory_gb" "32")
    SLURM_TIME=$(read_config "time_hours" "12")
    SLURM_ACCOUNT=$(read_config "slurm_account" "")
    SLURM_QOS=$(read_config "slurm_qos" "")

    mkdir -p slurm_logs

    SLURM_PARTITION=$(read_config "slurm_partition" "hpg-turin")
    SLURM_GPU_TYPE=$(read_config "slurm_gpu_type" "l4")
    SLURM_GPU_COUNT=$(read_config "slurm_gpu_count" "1")

    SBATCH_ARGS="--job-name=deeploc"
    SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${SLURM_CPUS}"
    SBATCH_ARGS="${SBATCH_ARGS} --mem=${SLURM_MEM}gb"
    SBATCH_ARGS="${SBATCH_ARGS} --time=${SLURM_TIME}:00:00"
    SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/deeploc-%j.log"
    SBATCH_ARGS="${SBATCH_ARGS} --partition=${SLURM_PARTITION}"
    SBATCH_ARGS="${SBATCH_ARGS} --gres=gpu:${SLURM_GPU_TYPE}:${SLURM_GPU_COUNT}"

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

echo "========================================================================"
echo "Starting DeepLoc Annotation Pipeline"
echo "========================================================================"

# Optionally resume from cached work/ if user enabled it in config
RESUME=$(read_config "resume" "false")
RESUME_FLAG=""
if [ "${RESUME}" == "true" ]; then
    RESUME_FLAG="-resume"
    echo "  resume: enabled (using NextFlow work/ cache)"
fi

nextflow run ai/main.nf ${RESUME_FLAG} \
    -c ai/nextflow.config \
    -resume

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
#   ../../output_to_input/BLOCK_deeploc/
#
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

# --- Subproject-root output_to_input (single canonical location) ---
SUBPROJECT_SHARED_DIR="../../output_to_input/BLOCK_deeploc"
mkdir -p "${SUBPROJECT_SHARED_DIR}"
find "${SUBPROJECT_SHARED_DIR}" -type l -delete 2>/dev/null || true

# --- Create relative symlinks for per-species DeepLoc result files ---
# Real files: OUTPUT_pipeline/2-output/{phyloname}_deeploc_predictions.csv
RESULT_DIR="OUTPUT_pipeline/2-output"
SYMLINK_COUNT=0

for result_file in ${RESULT_DIR}/*_deeploc_predictions.csv; do
    if [ -f "$result_file" ]; then
        filename="$(basename "$result_file")"
        # Symlink from subproject output_to_input to real file
        ln -sf "../../BLOCK_deeploc/${WORKFLOW_DIR_NAME}/${result_file}" "${SUBPROJECT_SHARED_DIR}/${filename}"
        SYMLINK_COUNT=$((SYMLINK_COUNT + 1))
    fi
done

echo "  Created ${SYMLINK_COUNT} symlinks in output_to_input/BLOCK_deeploc/"

if [ $SYMLINK_COUNT -eq 0 ]; then
    echo "  WARNING: No DeepLoc result files found in ${RESULT_DIR}/"
    echo "  The pipeline may have produced no outputs."
fi

echo ""
echo "========================================================================"
echo "SUCCESS! DeepLoc Annotation Pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/"
echo ""
echo "Downstream symlinks:"
echo "  output_to_input/BLOCK_deeploc/  (subproject root)"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
