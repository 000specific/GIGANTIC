#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 13 | Purpose: Run InterProScan Nextflow pipeline
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh
# =============================================================================
# Runs the InterProScan annotation Nextflow pipeline.
# Supports three execution modes via START_HERE-user_config.yaml:
#
#   "local"       - Runs directly on this machine (sequential)
#   "slurm"       - Submits as one SLURM job (sequential inside job)
#   "slurm_burst" - Submits each chunk as its own SLURM burst job (parallel)
#
# Usage:
#   bash RUN-workflow.sh
# =============================================================================

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Activate GIGANTIC Environment
# ============================================================================

module load conda 2>/dev/null || true

if conda activate ai_gigantic_interproscan 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_interproscan"
else
    echo "WARNING: Environment 'ai_gigantic_interproscan' not found."
    echo ""
    echo "Please run the environment setup script first:"
    echo "  cd ../../../../  # Go to project root"
    echo "  bash RUN-setup_environments.sh"
    echo ""
    echo "Or create this environment manually:"
    echo "  mamba env create -f ../../../../conda_environments/ai_gigantic_interproscan.yml"
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
        echo "  1. Install nextflow in conda env: conda install -n ai_gigantic_interproscan -c bioconda nextflow"
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
# Read configuration from START_HERE-user_config.yaml
# ============================================================================
# Uses grep to parse flat YAML keys (no Python dependency required).

read_config() {
    # Read a flat YAML key from START_HERE-user_config.yaml (no Python dependency)
    local value=$(grep "^${1}:" START_HERE-user_config.yaml 2>/dev/null | head -1 | sed 's/^[^:]*: *//' | sed 's/^"//;s/"$//')
    echo "${value:-$2}"
}

EXECUTION_MODE=$(read_config "execution_mode" "local")

# ============================================================================
# MODE: local
# ============================================================================
# Run Nextflow directly on this machine. All chunks process sequentially.

if [ "${EXECUTION_MODE}" == "local" ]; then
    echo "Execution mode: local"
    echo "========================================================================"
    echo "Starting InterProScan Annotation Pipeline (local)"
    echo "========================================================================"

# Optionally resume from cached work/ if user enabled it in config
RESUME=$(read_config "resume" "false")
RESUME_FLAG=""
if [ "${RESUME}" == "true" ]; then
    RESUME_FLAG="-resume"
    echo "  resume: enabled (using NextFlow work/ cache)"
fi

    nextflow run ai/main.nf ${RESUME_FLAG} \
        -c ai/nextflow.config

# ============================================================================
# MODE: slurm
# ============================================================================
# Submit as one SLURM job. Chunks process sequentially inside the job.

elif [ "${EXECUTION_MODE}" == "slurm" ]; then

    # If already inside a SLURM job, run the pipeline
    if [ -n "${SLURM_JOB_ID}" ]; then
        echo "Running inside SLURM job ${SLURM_JOB_ID}"
        echo "========================================================================"
        echo "Starting InterProScan Annotation Pipeline (slurm)"
        echo "========================================================================"

        nextflow run ai/main.nf \
            -c ai/nextflow.config

    # Otherwise, submit this script as a SLURM job
    else
        echo "Execution mode: slurm (submitting job)"
        echo ""

        SLURM_CPUS=$(read_config "cpus" "4")
        SLURM_MEM=$(read_config "memory_gb" "16")
        SLURM_TIME=$(read_config "time_hours" "96")
        SLURM_ACCOUNT=$(read_config "slurm_account" "")
        SLURM_QOS=$(read_config "slurm_qos" "")

        mkdir -p slurm_logs

        SBATCH_ARGS="--job-name=interproscan"
        SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${SLURM_CPUS}"
        SBATCH_ARGS="${SBATCH_ARGS} --mem=${SLURM_MEM}gb"
        SBATCH_ARGS="${SBATCH_ARGS} --time=${SLURM_TIME}:00:00"
        SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/interproscan-%j.log"

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
# MODE: slurm_burst
# ============================================================================
# Nextflow submits each InterProScan chunk as its own SLURM burst job.
# Hundreds of chunks can run in parallel across the cluster.
# The Nextflow orchestrator runs inside a small SLURM job to stay alive.

elif [ "${EXECUTION_MODE}" == "slurm_burst" ]; then

    # If already inside a SLURM job, run Nextflow as the orchestrator
    if [ -n "${SLURM_JOB_ID}" ]; then
        echo "Running as burst orchestrator inside SLURM job ${SLURM_JOB_ID}"
        echo "========================================================================"
        echo "Starting InterProScan Annotation Pipeline (slurm_burst)"
        echo "Nextflow will submit each chunk as its own SLURM burst job."
        echo "========================================================================"

        nextflow run ai/main.nf \
            -c ai/nextflow.config

    # Otherwise, submit the orchestrator as a small SLURM job
    else
        echo "Execution mode: slurm_burst"
        echo "Submitting orchestrator job (Nextflow will submit chunk jobs to burst QOS)"
        echo ""

        ORCH_CPUS=$(read_config "burst_orchestrator_cpus" "2")
        ORCH_MEM=$(read_config "burst_orchestrator_memory_gb" "8")
        ORCH_TIME=$(read_config "burst_orchestrator_time_hours" "96")
        SLURM_ACCOUNT=$(read_config "slurm_account" "")
        SLURM_QOS=$(read_config "slurm_qos" "")

        mkdir -p slurm_logs

        SBATCH_ARGS="--job-name=interproscan_orchestrator"
        SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${ORCH_CPUS}"
        SBATCH_ARGS="${SBATCH_ARGS} --mem=${ORCH_MEM}gb"
        SBATCH_ARGS="${SBATCH_ARGS} --time=${ORCH_TIME}:00:00"
        SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/interproscan_orchestrator-%j.log"

        if [ -n "${SLURM_ACCOUNT}" ]; then
            SBATCH_ARGS="${SBATCH_ARGS} --account=${SLURM_ACCOUNT}"
        fi
        if [ -n "${SLURM_QOS}" ]; then
            SBATCH_ARGS="${SBATCH_ARGS} --qos=${SLURM_QOS}"
        fi

        echo "Submitting orchestrator: sbatch ${SBATCH_ARGS}"
        sbatch ${SBATCH_ARGS} --wrap="bash $(realpath $0)"

        echo ""
        echo "Orchestrator job submitted."
        echo "Nextflow will submit individual chunk jobs to burst QOS."
        echo "Check slurm_logs/ for orchestrator output."
        echo "Use 'squeue -u \$(whoami)' to see chunk jobs as they are submitted."
        conda deactivate 2>/dev/null || true
        exit 0
    fi

else
    echo "ERROR: Unknown execution_mode '${EXECUTION_MODE}'"
    echo "Valid options: local, slurm, slurm_burst"
    exit 1
fi

# ============================================================================
# Post-pipeline: check exit code
# ============================================================================

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
#   ../../output_to_input/BLOCK_interproscan/
#
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

# --- Subproject-root output_to_input (single canonical location) ---
SUBPROJECT_SHARED_DIR="../../output_to_input/BLOCK_interproscan"
mkdir -p "${SUBPROJECT_SHARED_DIR}"
find "${SUBPROJECT_SHARED_DIR}" -type l -delete 2>/dev/null || true

# --- Create relative symlinks for per-species InterProScan result files ---
# Real files: OUTPUT_pipeline/4-output/{phyloname}_interproscan_results.tsv
RESULT_DIR="OUTPUT_pipeline/4-output"
SYMLINK_COUNT=0

for result_file in ${RESULT_DIR}/*_interproscan_results.tsv; do
    if [ -f "$result_file" ]; then
        filename="$(basename "$result_file")"
        # Symlink from subproject output_to_input to real file
        ln -sf "../../BLOCK_interproscan/${WORKFLOW_DIR_NAME}/${result_file}" "${SUBPROJECT_SHARED_DIR}/${filename}"
        SYMLINK_COUNT=$((SYMLINK_COUNT + 1))
    fi
done

echo "  Created ${SYMLINK_COUNT} symlinks in output_to_input/BLOCK_interproscan/"

if [ $SYMLINK_COUNT -eq 0 ]; then
    echo "  WARNING: No InterProScan result files found in ${RESULT_DIR}/"
    echo "  The pipeline may have produced no outputs."
fi

echo ""
echo "========================================================================"
echo "SUCCESS! InterProScan Annotation Pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/"
echo ""
echo "Downstream symlinks:"
echo "  output_to_input/BLOCK_interproscan/  (subproject root)"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
