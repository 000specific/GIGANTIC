#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 May 11 | Purpose: Run BLOCK_ocl_orthogroups parsimony workflow (local or SLURM via config)
# Human: Eric Edsinger

################################################################################
# parsimony_tree_structures - BLOCK_ocl_orthogroups - score structures
################################################################################
#
# PURPOSE:
# Rank species tree structures by parsimony scores derived from orthogroup OCL.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Edit START_HERE-user_config.yaml to set:
#    - run_label (e.g., "species70_X_OrthoHMM_GIGANTIC")
#    - species_set_name (e.g., "species70")
#    - inputs.ocl_orthogroups_dir (path to upstream orthogroups_X_ocl run_label)
#    - inputs.trees_species_dir
#    - execution_mode ("local" or "slurm")
# 2. Edit INPUT_user/structure_manifest.tsv with structure IDs to rank
# 3. Verify upstream subprojects have populated their output_to_input/:
#    - trees_species/output_to_input/BLOCK_permutations_and_features/
#    - orthogroups_X_ocl/output_to_input/BLOCK_ocl_analysis/<run_label>/
#
# WHAT THIS DOES:
# 1. Creates (or reuses) per-BLOCK conda env from ai/conda_environment.yml
# 2. Runs 7 scripts sequentially:
#    001: Validate inputs (structure manifest, OCL paths, columns)
#    002: Aggregate OCL per structure (one row per structure)
#    003: Compute parsimony scores side-by-side
#    004: Bootstrap orthogroups, estimate rank CIs
#    005: Rank structures, identify the best, emit final tables
#    006: Visualize (bar chart + heatmap, colorblind-safe)
#    007: Write run log
# 3. Creates output_to_input symlinks for downstream subprojects
#
# OUTPUT:
# Results in OUTPUT_pipeline/N-output/ for N in 1..6
# Downstream symlinks in ../../output_to_input/BLOCK_ocl_orthogroups/<run_label>/
#
################################################################################

echo "========================================================================"
echo "parsimony_tree_structures - BLOCK_ocl_orthogroups - score structures"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Read config (flat YAML keys via grep -- no python dependency at this point)
# ============================================================================

read_config() {
    local value=$(grep "^${1}:" START_HERE-user_config.yaml 2>/dev/null | head -1 | sed 's/^[^:]*: *//' | sed 's/^"//;s/"$//')
    echo "${value:-$2}"
}

EXECUTION_MODE=$(read_config "execution_mode" "local")

# ============================================================================
# SLURM self-submit (if execution_mode=slurm and not already inside a job)
# ============================================================================

if [ "${EXECUTION_MODE}" == "slurm" ] && [ -z "${SLURM_JOB_ID}" ]; then
    echo "Execution mode: SLURM (submitting job)"
    echo ""

    SLURM_CPUS=$(read_config "cpus" "2")
    SLURM_MEM=$(read_config "memory_gb" "8")
    SLURM_TIME=$(read_config "time_hours" "2")
    SLURM_ACCOUNT=$(read_config "slurm_account" "")
    SLURM_QOS=$(read_config "slurm_qos" "")

    mkdir -p slurm_logs

    SBATCH_ARGS="--job-name=parsimony_ocl_orthogroups"
    SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${SLURM_CPUS}"
    SBATCH_ARGS="${SBATCH_ARGS} --mem=${SLURM_MEM}gb"
    SBATCH_ARGS="${SBATCH_ARGS} --time=${SLURM_TIME}:00:00"
    SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/parsimony_ocl_orthogroups-%j.log"

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
# Activate conda environment (on-demand creation)
# ============================================================================

ENV_NAME="aiG-parsimony_tree_structures-ocl_orthogroups"
ENV_YML="ai/conda_environment.yml"

# Load conda module (HiPerGator/HPC)
module load conda 2>/dev/null || true

if ! command -v conda &> /dev/null; then
    echo "ERROR: conda not found!"
    echo "  On HPC (HiPerGator): module load conda"
    echo "  Otherwise: install conda from https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

if ! conda env list 2>/dev/null | grep -q "^${ENV_NAME} "; then
    echo "Environment '${ENV_NAME}' not found. Creating on-demand..."
    echo ""
    if [ ! -f "${ENV_YML}" ]; then
        echo "ERROR: Environment spec not found at: ${ENV_YML}"
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
        echo "ERROR: Failed to create conda environment '${ENV_NAME}' (exit ${CREATE_EXIT})"
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

# NextFlow availability
if ! command -v nextflow &> /dev/null; then
    echo "NextFlow not found in conda env. Trying system module..."
    module load nextflow 2>/dev/null || true
    if ! command -v nextflow &> /dev/null; then
        echo ""
        echo "ERROR: NextFlow not available."
        echo "  Install in env: conda install -n ${ENV_NAME} -c bioconda nextflow"
        echo "  Or system module: module load nextflow"
        exit 1
    fi
    echo "Using NextFlow from system module"
else
    echo "NextFlow available"
fi
echo ""

# ============================================================================
# Read configuration for logging + downstream symlink step
# ============================================================================

RUN_LABEL=$(read_config "run_label" "")
ORTHOGROUP_TOOL=$(read_config "orthogroup_tool" "")
SPECIES_SET=$(read_config "species_set_name" "")

echo "Configuration:"
echo "  Run Label       : ${RUN_LABEL}"
echo "  Species Set     : ${SPECIES_SET}"
echo "  Orthogroup Tool : ${ORTHOGROUP_TOOL}"
echo ""

# ============================================================================
# Validate prerequisites
# ============================================================================

echo "Validating prerequisites..."

if [ ! -f "START_HERE-user_config.yaml" ]; then
    echo "ERROR: Configuration file not found"
    exit 1
fi
echo "  [OK] Configuration file found"

if [ ! -d "INPUT_user" ]; then
    echo "ERROR: INPUT_user/ directory not found"
    exit 1
fi
echo "  [OK] INPUT_user/ directory found"

MANIFEST="INPUT_user/structure_manifest.tsv"
if [ ! -f "${MANIFEST}" ]; then
    echo "ERROR: Structure manifest not found: ${MANIFEST}"
    exit 1
fi
echo "  [OK] Structure manifest found: ${MANIFEST}"

STRUCTURE_COUNT=$(tail -n +2 "${MANIFEST}" | grep -v '^$' | wc -l)
echo "  [OK] Structures to process: ${STRUCTURE_COUNT}"
echo ""

# ============================================================================
# Run NextFlow pipeline
# ============================================================================

echo "Running NextFlow pipeline..."
echo ""

RESUME=$(read_config "resume" "false")
RESUME_FLAG=""
if [ "${RESUME}" == "true" ]; then
    RESUME_FLAG="-resume"
    echo "  resume: enabled"
fi

PARALLELISM_MODE=$(read_config "parallelism_mode" "local")
case "${PARALLELISM_MODE}" in
    slurm) PROFILE_FLAG="-profile slurm" ;;
    local) PROFILE_FLAG="-profile local" ;;
    *)
        echo "ERROR: unknown parallelism_mode: '${PARALLELISM_MODE}'"
        exit 1
        ;;
esac
echo "  parallelism_mode: ${PARALLELISM_MODE} (${PROFILE_FLAG})"

NEXTFLOW_SLURM_ACCOUNT=$(read_config "slurm_account" "")
NEXTFLOW_SLURM_QOS=$(read_config "slurm_qos" "")
NEXTFLOW_CPUS=$(read_config "cpus" "2")
NEXTFLOW_MEMORY_GB=$(read_config "memory_gb" "8")
NEXTFLOW_PARAMS=""
if [ -n "${NEXTFLOW_SLURM_ACCOUNT}" ]; then
    NEXTFLOW_PARAMS="${NEXTFLOW_PARAMS} --slurm_account=${NEXTFLOW_SLURM_ACCOUNT}"
fi
if [ -n "${NEXTFLOW_SLURM_QOS}" ]; then
    NEXTFLOW_PARAMS="${NEXTFLOW_PARAMS} --slurm_qos=${NEXTFLOW_SLURM_QOS}"
fi
NEXTFLOW_PARAMS="${NEXTFLOW_PARAMS} --cpus=${NEXTFLOW_CPUS} --memory_gb=${NEXTFLOW_MEMORY_GB}"

nextflow run ai/main.nf ${RESUME_FLAG} ${PROFILE_FLAG} ${NEXTFLOW_PARAMS}

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "========================================================================"
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "========================================================================"
    exit $EXIT_CODE
fi

# ============================================================================
# Create symlinks in output_to_input
# ============================================================================
# Real files live in OUTPUT_pipeline/5-output/.
# Symlinks go to ../../output_to_input/BLOCK_ocl_orthogroups/{run_label}/
# Downstream subprojects (e.g., a future BLOCK_comparison/) read from there.

echo ""
echo "Creating symlinks for downstream subprojects..."

WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"
SHARED_DIR="../../output_to_input/BLOCK_ocl_orthogroups/${RUN_LABEL}"
mkdir -p "${SHARED_DIR}"

# Remove stale symlinks
for old_link in "${SHARED_DIR}"/*; do
    if [ -L "$old_link" ]; then
        rm "$old_link"
    fi
done

# Symlink the ranking table and best-structure file
for source_filename in \
    "5_ai-parsimony_ranking-structures.tsv" \
    "5_ai-parsimony_best_structure.txt"
do
    source_path="OUTPUT_pipeline/5-output/${source_filename}"
    if [ -f "$source_path" ]; then
        ln -sf "../../../BLOCK_ocl_orthogroups/${WORKFLOW_DIR_NAME}/${source_path}" \
            "${SHARED_DIR}/${source_filename}"
    else
        echo "  WARNING: expected output not found: ${source_path}"
    fi
done

SYMLINK_COUNT=$(find "${SHARED_DIR}" -type l 2>/dev/null | wc -l)
echo "  output_to_input/BLOCK_ocl_orthogroups/${RUN_LABEL}/ -> ${SYMLINK_COUNT} symlinks"
echo ""

echo "========================================================================"
echo "SUCCESS! Parsimony ranking complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/  input validation report"
echo "  OUTPUT_pipeline/2-output/  per-structure OCL aggregates"
echo "  OUTPUT_pipeline/3-output/  parsimony scores side-by-side"
echo "  OUTPUT_pipeline/4-output/  bootstrap confidence per structure"
echo "  OUTPUT_pipeline/5-output/  FINAL ranking + best structure"
echo "  OUTPUT_pipeline/6-output/  figures (bar chart, heatmap)"
echo ""
echo "Downstream symlinks:"
echo "  ../../output_to_input/BLOCK_ocl_orthogroups/${RUN_LABEL}/"
echo ""
echo "Run Label: ${RUN_LABEL}"
echo "Structures processed: ${STRUCTURE_COUNT}"
echo "========================================================================"
echo "Completed: $(date)"

conda deactivate 2>/dev/null || true
