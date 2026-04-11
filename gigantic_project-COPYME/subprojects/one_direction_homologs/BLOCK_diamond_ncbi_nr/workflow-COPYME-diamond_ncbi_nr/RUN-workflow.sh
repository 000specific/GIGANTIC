#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 31 | Purpose: Run DIAMOND NCBI nr search pipeline with local/slurm/burst modes
# Human: Eric Edsinger

################################################################################
# GIGANTIC One-Direction Homologs Pipeline
################################################################################
#
# Runs the DIAMOND NCBI nr search workflow.
# Supports three execution modes via START_HERE-user_config.yaml:
#
#   "local"       - Runs directly on this machine (sequential)
#   "slurm"       - Submits as one SLURM job (sequential inside job)
#   "slurm_burst" - Submits each DIAMOND split as its own SLURM burst job (parallel)
#
# Usage:
#   bash RUN-workflow.sh
#
# Before running:
#   1. Edit START_HERE-user_config.yaml (DIAMOND database path, execution mode)
#   2. Create INPUT_user/proteome_manifest.tsv with your species and proteome paths
#
################################################################################

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Resolve species list: workflow INPUT_user/ overrides project-level default
# ============================================================================

INPUT_USER_PROJECT="../../../../INPUT_user"

if [ -f "INPUT_user/species_list.txt" ]; then
    WORKFLOW_SPECIES_COUNT=$(grep -v "^#" "INPUT_user/species_list.txt" | grep -v "^$" | wc -l)
    if [ "$WORKFLOW_SPECIES_COUNT" -gt 0 ]; then
        echo "Using workflow-level species list (user override)..."
        echo "  ${WORKFLOW_SPECIES_COUNT} species in INPUT_user/species_list.txt"
        echo ""
    fi
elif [ -f "${INPUT_USER_PROJECT}/species_set/species_list.txt" ]; then
    PROJECT_SPECIES_COUNT=$(grep -v "^#" "${INPUT_USER_PROJECT}/species_set/species_list.txt" | grep -v "^$" | wc -l)
    if [ "$PROJECT_SPECIES_COUNT" -gt 0 ]; then
        echo "Using project-level species list (default)..."
        cp "${INPUT_USER_PROJECT}/species_set/species_list.txt" "INPUT_user/species_list.txt"
        echo "  Copied ${PROJECT_SPECIES_COUNT} species from project INPUT_user/species_set/"
        echo ""
    fi
fi

# ============================================================================
# Activate GIGANTIC Environment (on-demand creation)
# ============================================================================

ENV_NAME="ai_gigantic_one_direction_homologs"
ENV_YML="../../../../conda_environments/${ENV_NAME}.yml"

module load conda 2>/dev/null || true

if ! command -v conda &> /dev/null; then
    echo "ERROR: conda not found!"
    echo "On HPC (HiPerGator): module load conda"
    exit 1
fi

# Create environment on-demand if it does not exist
if ! conda env list 2>/dev/null | grep -q "^${ENV_NAME} "; then
    echo "Environment '${ENV_NAME}' not found. Creating on-demand..."
    echo ""
    if [ ! -f "${ENV_YML}" ]; then
        echo "ERROR: Environment spec not found at: ${ENV_YML}"
        exit 1
    fi
    if command -v mamba &> /dev/null; then
        mamba env create -f "${ENV_YML}" -y
    else
        conda env create -f "${ENV_YML}" -y
    fi
    echo ""
    echo "Environment '${ENV_NAME}' created successfully."
    echo ""
fi

# Activate the environment
if conda activate "${ENV_NAME}" 2>/dev/null; then
    echo "Activated conda environment: ${ENV_NAME}"
else
    echo "WARNING: Could not activate '${ENV_NAME}'. Continuing with current environment."
fi

# Ensure NextFlow is available (conda env or system module)
if ! command -v nextflow &> /dev/null; then
    module load nextflow 2>/dev/null || true
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: NextFlow not available!"
        echo "Options: conda install -n ${ENV_NAME} -c bioconda nextflow, or module load nextflow"
        exit 1
    fi
    echo "Using NextFlow from system module"
else
    echo "NextFlow available"
fi
echo ""

# ============================================================================
# Validate inputs
# ============================================================================

# Check for proteome manifest
if [ ! -f "INPUT_user/proteome_manifest.tsv" ]; then
    echo "ERROR: Proteome manifest not found!"
    echo ""
    echo "Please create: INPUT_user/proteome_manifest.tsv"
    echo "See INPUT_user/proteome_manifest_example.tsv for format."
    exit 1
fi

# Check for config file
CONFIG_FILE="START_HERE-user_config.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Configuration file not found: ${CONFIG_FILE}"
    exit 1
fi

# Show manifest summary
SPECIES_COUNT=$(grep -v "^#" INPUT_user/proteome_manifest.tsv | grep -v "^$" | tail -n +2 | wc -l)
echo "Species in manifest: ${SPECIES_COUNT}"
echo ""

# ============================================================================
# Read configuration from START_HERE-user_config.yaml
# ============================================================================

read_config() {
    local value=$(grep "^${1}:" START_HERE-user_config.yaml 2>/dev/null | head -1 | sed 's/^[^:]*: *//' | sed 's/^"//;s/"$//')
    echo "${value:-$2}"
}

EXECUTION_MODE=$(read_config "execution_mode" "local")

# ============================================================================
# MODE: local
# ============================================================================
# Run Nextflow directly on this machine. All processes run sequentially.

if [ "${EXECUTION_MODE}" == "local" ]; then
    echo "Execution mode: local"
    echo "========================================================================"
    echo "Starting One-Direction Homologs Pipeline (local)"
    echo "Started: $(date)"
    echo "========================================================================"

    nextflow run ai/main.nf \
        -c ai/nextflow.config

# ============================================================================
# MODE: slurm
# ============================================================================
# Submit as one SLURM job. All processes run sequentially inside the job.

elif [ "${EXECUTION_MODE}" == "slurm" ]; then

    # If already inside a SLURM job, run the pipeline
    if [ -n "${SLURM_JOB_ID}" ]; then
        echo "Running inside SLURM job ${SLURM_JOB_ID}"
        echo "========================================================================"
        echo "Starting One-Direction Homologs Pipeline (slurm)"
        echo "Started: $(date)"
        echo "========================================================================"

        nextflow run ai/main.nf \
            -c ai/nextflow.config

    # Otherwise, submit this script as a SLURM job
    else
        echo "Execution mode: slurm (submitting job)"
        echo ""

        SLURM_CPUS=$(read_config "cpus" "50")
        SLURM_MEM=$(read_config "memory_gb" "350")
        SLURM_TIME=$(read_config "time_hours" "96")
        SLURM_ACCOUNT=$(read_config "slurm_account" "")
        SLURM_QOS=$(read_config "slurm_qos" "")

        mkdir -p slurm_logs

        SBATCH_ARGS="--job-name=one_direction_homologs"
        SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${SLURM_CPUS}"
        SBATCH_ARGS="${SBATCH_ARGS} --mem=${SLURM_MEM}gb"
        SBATCH_ARGS="${SBATCH_ARGS} --time=${SLURM_TIME}:00:00"
        SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/one_direction_homologs-%j.log"

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
# Nextflow submits each DIAMOND split as its own SLURM burst job.
# Thousands of splits can run in parallel across the cluster.
# The Nextflow orchestrator runs inside a small SLURM job to stay alive.

elif [ "${EXECUTION_MODE}" == "slurm_burst" ]; then

    # If already inside a SLURM job, run Nextflow as the orchestrator
    if [ -n "${SLURM_JOB_ID}" ]; then
        echo "Running as burst orchestrator inside SLURM job ${SLURM_JOB_ID}"
        echo "========================================================================"
        echo "Starting One-Direction Homologs Pipeline (slurm_burst)"
        echo "Nextflow will submit each DIAMOND split as its own SLURM burst job."
        echo "Started: $(date)"
        echo "========================================================================"

        nextflow run ai/main.nf \
            -c ai/nextflow.config

    # Otherwise, submit the orchestrator as a small SLURM job
    else
        echo "Execution mode: slurm_burst"
        echo "Submitting orchestrator job (Nextflow will submit DIAMOND jobs to burst QOS)"
        echo ""

        ORCH_CPUS=$(read_config "burst_orchestrator_cpus" "2")
        ORCH_MEM=$(read_config "burst_orchestrator_memory_gb" "8")
        ORCH_TIME=$(read_config "burst_orchestrator_time_hours" "96")
        SLURM_ACCOUNT=$(read_config "slurm_account" "")
        SLURM_QOS=$(read_config "slurm_qos" "")

        mkdir -p slurm_logs

        SBATCH_ARGS="--job-name=diamond_ncbi_nr_orchestrator"
        SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${ORCH_CPUS}"
        SBATCH_ARGS="${SBATCH_ARGS} --mem=${ORCH_MEM}gb"
        SBATCH_ARGS="${SBATCH_ARGS} --time=${ORCH_TIME}:00:00"
        SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/diamond_ncbi_nr_orchestrator-%j.log"

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
        echo "Nextflow will submit individual DIAMOND jobs to burst QOS."
        echo "Check slurm_logs/ for orchestrator output."
        echo "Use 'squeue -u \$(whoami)' to see DIAMOND jobs as they are submitted."
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
#   ../../output_to_input/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits/
#
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"
OUTPUT_TO_INPUT_DIR="../../output_to_input/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits"
mkdir -p "${OUTPUT_TO_INPUT_DIR}"

# Remove any stale symlinks from previous runs
find "${OUTPUT_TO_INPUT_DIR}" -type l -delete 2>/dev/null

# Symlink per-species top hits and statistics from 5-output/
SYMLINK_COUNT=0
for file_path in OUTPUT_pipeline/5-output/*_top_hits.tsv OUTPUT_pipeline/5-output/*_statistics.tsv; do
    [ -f "${file_path}" ] || continue
    file_name="$(basename "${file_path}")"
    ln -sf "../../../BLOCK_diamond_ncbi_nr/${WORKFLOW_DIR_NAME}/${file_path}" "${OUTPUT_TO_INPUT_DIR}/${file_name}"
    SYMLINK_COUNT=$((SYMLINK_COUNT + 1))
done

# Symlink master statistics from 6-output/
if [ -f "OUTPUT_pipeline/6-output/6_ai-all_species_statistics.tsv" ]; then
    ln -sf "../../../BLOCK_diamond_ncbi_nr/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/6-output/6_ai-all_species_statistics.tsv" \
        "${OUTPUT_TO_INPUT_DIR}/all_species_statistics.tsv"
    SYMLINK_COUNT=$((SYMLINK_COUNT + 1))
fi

echo "  Created ${SYMLINK_COUNT} symlinks in output_to_input/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits/"

if [ $SYMLINK_COUNT -eq 0 ]; then
    echo "  WARNING: No output files found in OUTPUT_pipeline/5-output/ or 6-output/"
    echo "  The pipeline may have produced no outputs."
fi

echo ""
echo "========================================================================"
echo "SUCCESS! One-Direction Homologs Pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/ through 6-output/"
echo ""
echo "Downstream symlinks:"
echo "  ../../output_to_input/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits/"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true

exit 0
