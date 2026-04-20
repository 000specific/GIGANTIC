#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 April 13 | Purpose: Run OCL analysis workflow (local or SLURM via config)
# Human: Eric Edsinger

################################################################################
# GIGANTIC orthogroups_X_ocl - STEP_1 Origin-Conservation-Loss Analysis
################################################################################
#
# PURPOSE:
# Run the OCL pipeline to determine orthogroup origins, quantify conservation
# and loss patterns, and validate results across phylogenetic species tree
# structures.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Edit START_HERE-user_config.yaml to set:
#    - run_label (e.g., "species70_X_OrthoHMM")
#    - species_set_name (e.g., "species70")
#    - orthogroup_tool (OrthoFinder, OrthoHMM, or Broccoli)
#    - execution_mode ("local" or "slurm")
#    - Input paths to upstream subprojects
# 2. Edit INPUT_user/structure_manifest.tsv with structure IDs to analyze
# 3. Verify upstream subprojects have populated their output_to_input/:
#    - trees_species/output_to_input/BLOCK_permutations_and_features/
#    - orthogroups/output_to_input/BLOCK_<tool>/
#    - genomesDB/output_to_input/STEP_4-create_final_species_set/
#
# WHAT THIS DOES:
# 1. Creates (or reuses) per-STEP conda env from ai/conda_environment.yml
# 2. Runs 5 scripts per structure (parallel across structures):
#    001: Prepare inputs from upstream subprojects
#    002: Determine orthogroup origins (MRCA algorithm)
#    003: Quantify conservation and loss (TEMPLATE_03 dual-metric)
#    004: Generate comprehensive OCL summaries
#    005: Validate results (strict fail-fast)
# 3. Creates output_to_input symlinks for downstream subprojects
#
# OUTPUT:
# Results in OUTPUT_pipeline/structure_NNN/1-output/ through 5-output/
# Downstream symlinks in ../../output_to_input/BLOCK_ocl_analysis/{run_label}/
#
################################################################################

echo "========================================================================"
echo "GIGANTIC orthogroups_X_ocl - STEP_1 OCL Pipeline"
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
# Uses grep to parse flat YAML keys (no Python dependency required).

read_config() {
    local value=$(grep "^${1}:" START_HERE-user_config.yaml 2>/dev/null | head -1 | sed 's/^[^:]*: *//' | sed 's/^"//;s/"$//')
    echo "${value:-$2}"
}

EXECUTION_MODE=$(read_config "execution_mode" "local")

# ============================================================================
# SLURM submission (if execution_mode is "slurm" and not already inside a job)
# ============================================================================
# Self-submits as a SLURM job so heavy work (conda env creation, NextFlow
# pipeline) runs on a compute node — never on the login node.

if [ "${EXECUTION_MODE}" == "slurm" ] && [ -z "${SLURM_JOB_ID}" ]; then
    echo "Execution mode: SLURM (submitting job)"
    echo ""

    SLURM_CPUS=$(read_config "cpus" "3")
    SLURM_MEM=$(read_config "memory_gb" "20")
    SLURM_TIME=$(read_config "time_hours" "24")
    SLURM_ACCOUNT=$(read_config "slurm_account" "")
    SLURM_QOS=$(read_config "slurm_qos" "")

    mkdir -p slurm_logs

    SBATCH_ARGS="--job-name=ocl_analysis"
    SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${SLURM_CPUS}"
    SBATCH_ARGS="${SBATCH_ARGS} --mem=${SLURM_MEM}gb"
    SBATCH_ARGS="${SBATCH_ARGS} --time=${SLURM_TIME}:00:00"
    SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/ocl_analysis-%j.log"

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
#   - conda environment: aiG-orthogroups_X_ocl-ocl_analysis (Python, PyYAML, NextFlow)
#   - NextFlow: from conda env OR system module
#
# The environment is created automatically on first run from the yml spec
# colocated at ai/conda_environment.yml. mamba is preferred (much faster);
# conda is the fallback if mamba is not available.
# ============================================================================

ENV_NAME="aiG-orthogroups_X_ocl-ocl_analysis"
ENV_YML="ai/conda_environment.yml"

# Specific to GIGANTIC development for GitHub
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

# Create environment on-demand if it does not exist
if ! conda env list 2>/dev/null | grep -q "^${ENV_NAME} "; then
    echo "Environment '${ENV_NAME}' not found. Creating on-demand..."
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

# Activate the environment
if conda activate "${ENV_NAME}" 2>/dev/null; then
    echo "Activated conda environment: ${ENV_NAME}"
else
    echo "WARNING: Could not activate '${ENV_NAME}'. Continuing with current environment."
fi

# Ensure NextFlow is available (conda env or system module)
if ! command -v nextflow &> /dev/null; then
    echo "NextFlow not found in conda env. Trying system module..."
    # Specific to GIGANTIC development for GitHub
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
# Read Configuration (for logging + downstream symlink step)
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
# Validate Prerequisites
# ============================================================================

echo "Validating prerequisites..."
echo ""

if [ ! -f "START_HERE-user_config.yaml" ]; then
    echo "ERROR: Configuration file not found!"
    echo "Expected: START_HERE-user_config.yaml"
    exit 1
fi
echo "  [OK] Configuration file found"

if [ ! -d "INPUT_user" ]; then
    echo "ERROR: INPUT_user/ directory not found!"
    echo "  Create it and add structure_manifest.tsv."
    exit 1
fi
echo "  [OK] INPUT_user/ directory found"

# Check structure manifest exists (read path via read_config to avoid nested-yaml python call)
MANIFEST="INPUT_user/structure_manifest.tsv"
if [ ! -f "${MANIFEST}" ]; then
    echo "ERROR: Structure manifest not found: ${MANIFEST}"
    echo "  Create the manifest with structure IDs to analyze."
    exit 1
fi
echo "  [OK] Structure manifest found: ${MANIFEST}"

STRUCTURE_COUNT=$(tail -n +2 "${MANIFEST}" | grep -v '^$' | wc -l)
echo "  [OK] Structures to process: ${STRUCTURE_COUNT}"

echo ""

# ============================================================================
# Run NextFlow Pipeline
# ============================================================================

echo "Running NextFlow pipeline..."
echo ""

# Optionally resume from cached work/ if user enabled it in config
RESUME=$(read_config "resume" "false")
RESUME_FLAG=""
if [ "${RESUME}" == "true" ]; then
    RESUME_FLAG="-resume"
    echo "  resume: enabled (using NextFlow work/ cache)"
fi

# Parallelism mode selects the NextFlow profile from ai/nextflow.config:
#   "slurm" -> process.executor = 'slurm' (each task is its own sbatch)
#   "local" -> process.executor = 'local' (tasks run in parallel here)
PARALLELISM_MODE=$(read_config "parallelism_mode" "local")
case "${PARALLELISM_MODE}" in
    slurm) PROFILE_FLAG="-profile standard" ;;
    local) PROFILE_FLAG="-profile local" ;;
    *)
        echo "ERROR: unknown parallelism_mode: '${PARALLELISM_MODE}'"
        echo "Valid values: 'slurm' | 'local' (see START_HERE-user_config.yaml)"
        exit 1
        ;;
esac
echo "  parallelism_mode: ${PARALLELISM_MODE} (nextflow ${PROFILE_FLAG})"

# Pipe SLURM account/QOS from START_HERE-user_config.yaml into nextflow.config
# via --param CLI args so nextflow.config never needs hand-edited duplicates.
# (nextflow.config's params.slurm_account / params.slurm_qos default to empty
# to fail fast if this plumbing breaks.)
# Re-read here because the outer SLURM_ACCOUNT/SLURM_QOS shell vars (if set)
# only exist in the self-submitting branch above, not when re-invoked by sbatch.
NEXTFLOW_SLURM_ACCOUNT=$(read_config "slurm_account" "")
NEXTFLOW_SLURM_QOS=$(read_config "slurm_qos" "")
NEXTFLOW_PARAMS=""
if [ -n "${NEXTFLOW_SLURM_ACCOUNT}" ]; then
    NEXTFLOW_PARAMS="${NEXTFLOW_PARAMS} --slurm_account=${NEXTFLOW_SLURM_ACCOUNT}"
fi
if [ -n "${NEXTFLOW_SLURM_QOS}" ]; then
    NEXTFLOW_PARAMS="${NEXTFLOW_PARAMS} --slurm_qos=${NEXTFLOW_SLURM_QOS}"
fi

nextflow run ai/main.nf ${RESUME_FLAG} ${PROFILE_FLAG} ${NEXTFLOW_PARAMS}

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
# Real files live in OUTPUT_pipeline/structure_NNN/4-output/ (created by pipeline).
# Symlinks go to ../../output_to_input/BLOCK_ocl_analysis/{run_label}/
# Each structure gets a symlink: structure_NNN -> real 4-output summary file.
#
# The run_label provides namespacing so different tool explorations coexist:
#   output_to_input/BLOCK_ocl_analysis/species70_X_OrthoHMM/structure_001/
#   output_to_input/BLOCK_ocl_analysis/species70_X_OrthoFinder/structure_001/
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

# Determine the workflow directory name dynamically
# (supports both COPYME templates and RUN_XX instances)
WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

SHARED_DIR="../../output_to_input/BLOCK_ocl_analysis/${RUN_LABEL}"
mkdir -p "${SHARED_DIR}"

# Remove any stale symlinks from previous runs
for old_link in "${SHARED_DIR}"/structure_*; do
    if [ -L "$old_link" ]; then
        rm "$old_link"
    fi
done

# Create symlinks for each structure directory
for structure_dir in OUTPUT_pipeline/structure_*; do
    if [ -d "$structure_dir" ]; then
        structure_name=$(basename "$structure_dir")
        summary_file="${structure_dir}/4-output/4_ai-orthogroups-complete_ocl_summary.tsv"

        if [ -f "$summary_file" ]; then
            mkdir -p "${SHARED_DIR}/${structure_name}"
            ln -sf "../../../../BLOCK_ocl_analysis/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/${structure_name}/4-output/4_ai-orthogroups-complete_ocl_summary.tsv" \
                "${SHARED_DIR}/${structure_name}/4_ai-orthogroups-complete_ocl_summary.tsv"
        fi
    fi
done

SYMLINK_COUNT=$(find "${SHARED_DIR}" -name "*.tsv" -type l 2>/dev/null | wc -l)
echo "  output_to_input/BLOCK_ocl_analysis/${RUN_LABEL}/ -> ${SYMLINK_COUNT} symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! STEP_1 OCL pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/structure_NNN/1-output/  Standardized inputs"
echo "  OUTPUT_pipeline/structure_NNN/2-output/  Orthogroup origins"
echo "  OUTPUT_pipeline/structure_NNN/3-output/  Conservation/loss patterns"
echo "  OUTPUT_pipeline/structure_NNN/4-output/  Comprehensive OCL summaries"
echo "  OUTPUT_pipeline/structure_NNN/5-output/  Validation reports"
echo ""
echo "Downstream symlinks:"
echo "  ../../output_to_input/BLOCK_ocl_analysis/${RUN_LABEL}/"
echo ""
echo "Run Label: ${RUN_LABEL}"
echo "Structures processed: ${STRUCTURE_COUNT}"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
