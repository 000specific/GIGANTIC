#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 April 18 | Purpose: Run annotations OCL analysis workflow (local or SLURM via config)
# Human: Eric Edsinger

################################################################################
# GIGANTIC annotations_X_ocl - STEP_1 Origin-Conservation-Loss Analysis
################################################################################
#
# PURPOSE:
# Run the OCL pipeline to determine annogroup origins, quantify conservation
# and loss patterns, and validate results across phylogenetic species tree
# structures.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Edit START_HERE-user_config.yaml to set:
#    - species_set_name (e.g., "species70")
#    - annotation_databases ("all" or a list like [ pfam, go ]; the run fans out per source)
#    - annogroup_types (feature, combination, architecture; absent excluded)
#    - execution_mode ("local" or "slurm")
#    - Input paths to upstream subprojects
# 2. Edit INPUT_user/structure_manifest.tsv with structure IDs to analyze
# 3. Verify upstream subprojects have populated their output_to_input/:
#    - trees_species/output_to_input/BLOCK_permutations_and_features/
#    - annogroups/output_to_input/BLOCK_build_annogroups/ (the annogroup map)
#
# WHAT THIS DOES:
# 1. Creates (or reuses) per-STEP conda env from ai/conda_environment.yml
# 2. Runs the per-structure chain (parallel across structures):
#    001: Load annogroups (imported from the annogroups subproject) + phylo inputs
#    002: Determine annogroup origins (MRCA algorithm)
#    003: Quantify conservation and loss (Rule 7 block-state classification)
#    004: Generate comprehensive OCL summaries (per-type + all-types)
#    005: Species-tree deconvolution (member species + protein counts per clade)
#    006: Validate results (strict fail-fast)
#    Then ONCE after all structures (barrier):
#    007: Composite clades (classify annogroups by member species; structure-independent)
#    008: Write run log
#    009: Aggregate run summary -> OUTPUT_pipeline/9-output/9_ai-run_summary.md
# 3. Creates output_to_input symlinks for downstream subprojects
#
# OUTPUT:
# Results in OUTPUT_pipeline/structure_NNN/1-output/ through 6-output/
#   plus OUTPUT_pipeline/composite_clades/ (computed once)
# Downstream symlinks in ../../output_to_input/BLOCK_annotations_X_ocl/{species_set}_{source}/
#
################################################################################

echo "========================================================================"
echo "GIGANTIC annotations_X_ocl - STEP_1 OCL Pipeline"
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
# Clear stale run-summary fragments (before SLURM submit)
# ============================================================================
# Each pipeline script emits a JSON fragment to ai/logs/run_summary_fragments/;
# the final aggregator (Script 009) reads them and writes the consolidated run
# summary into OUTPUT_pipeline/9-output/. Clear any previous run's fragments so
# the aggregator sees only this run's data.
FRAGMENTS_DIR="ai/logs/run_summary_fragments"

# Clear fragments only on login-node entry (not when inside SLURM job).
# The SLURM job re-runs this script, and we don't want to clear fragments
# that may have just been written by early parallel tasks.
if [ -z "${SLURM_JOB_ID}" ]; then
    if [ -d "${FRAGMENTS_DIR}" ]; then
        rm -f "${FRAGMENTS_DIR}"/*.json 2>/dev/null
    fi
    mkdir -p "${FRAGMENTS_DIR}"
fi

# ============================================================================
# SLURM submission (if execution_mode is "slurm" and not already inside a job)
# ============================================================================
# Self-submits as a SLURM job so heavy work (conda env creation, NextFlow
# pipeline) runs on a compute node -- never on the login node.

if [ "${EXECUTION_MODE}" == "slurm" ] && [ -z "${SLURM_JOB_ID}" ]; then
    echo "Execution mode: SLURM (submitting job)"
    echo ""

    SLURM_CPUS=$(read_config "cpus" "3")
    SLURM_MEM=$(read_config "memory_gb" "20")
    SLURM_TIME=$(read_config "time_hours" "24")
    SLURM_ACCOUNT=$(read_config "slurm_account" "")
    SLURM_QOS=$(read_config "slurm_qos" "")

    mkdir -p slurm_logs

    SBATCH_ARGS="--job-name=annotations_ocl"
    SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${SLURM_CPUS}"
    SBATCH_ARGS="${SBATCH_ARGS} --mem=${SLURM_MEM}gb"
    SBATCH_ARGS="${SBATCH_ARGS} --time=${SLURM_TIME}:00:00"
    SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/annotations_ocl-%j.log"

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
#   - conda environment: aiG-ocl_phylogenetic_structures-annotations_X_ocl (Python, PyYAML, NextFlow)
#   - NextFlow: from conda env OR system module
#
# The environment is created automatically on first run from the yml spec
# colocated at ai/conda_environment.yml. mamba is preferred (much faster);
# conda is the fallback if mamba is not available.
# ============================================================================

ENV_NAME="aiG-ocl_phylogenetic_structures-annotations_X_ocl"
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

ANNOTATION_DATABASES=$(read_config "annotation_databases" "all")
SPECIES_SET=$(read_config "species_set_name" "")

echo "Configuration:"
echo "  Species Set          : ${SPECIES_SET}"
echo "  Annotation Sources   : ${ANNOTATION_DATABASES} (fans out per source)"
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

# Check structure manifest exists
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

# Universal GIGANTIC YAML->params pattern: pass the YAML directly via
# -params-file. NextFlow loads YAML natively, populating params.X.Y.Z to
# mirror the yaml shape. All keys (slurm_account/qos, cpus, memory_gb,
# inputs.*, output.*, etc.) flow through automatically.

nextflow run ai/main.nf ${RESUME_FLAG} ${PROFILE_FLAG} \
    -params-file START_HERE-user_config.yaml

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
# Create symlinks for output_to_input directory (PER SOURCE)
# ============================================================================
# Real files live in OUTPUT_pipeline/<source>/structure_NNN/4-output/ (pipeline).
# Symlinks go to ../../output_to_input/BLOCK_annotations_X_ocl/<species_set>_<source>/
# Each (source, structure) gets a symlink to that structure's 4-output summary.
#
# The <species_set>_<source> namespace lets the per-source OCL results coexist (one
# run produces them all) and preserves the downstream consumer contract -- e.g.
# integrator's `annogroup_ocl_run_label: "species70_pfam"`.
#   output_to_input/BLOCK_annotations_X_ocl/species70_pfam/structure_001/
#   output_to_input/BLOCK_annotations_X_ocl/species70_go/structure_001/
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects (per source)..."

# Determine the workflow directory name dynamically
# (supports both COPYME templates and RUN_XX instances)
WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

# Discover the sources actually produced (the OUTPUT_pipeline/<source>/ subdirs)
TOTAL_SYMLINKS=0
for source_dir in OUTPUT_pipeline/*/; do
    [ -d "$source_dir" ] || continue
    source_name=$(basename "$source_dir")
    # Skip non-source aggregate dirs if any ever appear at this level
    case "$source_name" in
        composite_clades|logs ) continue ;;
    esac

    SHARED_DIR="../../output_to_input/BLOCK_annotations_X_ocl/${SPECIES_SET}_${source_name}"
    mkdir -p "${SHARED_DIR}"

    # Remove ALL stale per-structure symlink dirs from previous runs before recreating.
    # output_to_input holds ONLY symlinks into OUTPUT_pipeline (never real data), so this
    # is safe. The old per-link `rm` checked the structure_NNN *directories* for -L (they
    # are dirs, not links) and so never removed anything -- symlinks from earlier runs and
    # obsolete schemes (e.g. the retired single/combo files) accumulated indefinitely.
    find "${SHARED_DIR}" -mindepth 1 -maxdepth 1 -type d -name 'structure_*' -exec rm -rf {} +

    # One symlink per structure -> that structure's all-types integrated OCL summary.
    #
    # NOTE: OCL no longer exposes annogroup membership here. Annogroup membership
    # (member Sequence_IDs) lives in the annogroups subproject, which downstream
    # consumers read DIRECTLY. This BLOCK only shares its own OCL inference outputs.
    for structure_dir in "${source_dir}"structure_*; do
        [ -d "$structure_dir" ] || continue
        structure_name=$(basename "$structure_dir")
        summary_file="${structure_dir}/4-output/4_ai-${structure_name}_annogroups-complete_ocl_summary-all_types.tsv"

        if [ -f "$summary_file" ]; then
            mkdir -p "${SHARED_DIR}/${structure_name}"
            ln -sf "../../../../BLOCK_annotations_X_ocl/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/${source_name}/${structure_name}/4-output/4_ai-${structure_name}_annogroups-complete_ocl_summary-all_types.tsv" \
                "${SHARED_DIR}/${structure_name}/4_ai-${structure_name}_annogroups-complete_ocl_summary-all_types.tsv"
        fi
    done

    SOURCE_SYMLINKS=$(find "${SHARED_DIR}" -name "*.tsv" -type l 2>/dev/null | wc -l)
    echo "  output_to_input/BLOCK_annotations_X_ocl/${SPECIES_SET}_${source_name}/ -> ${SOURCE_SYMLINKS} symlinks"
    TOTAL_SYMLINKS=$(( TOTAL_SYMLINKS + SOURCE_SYMLINKS ))
done

echo "  total: ${TOTAL_SYMLINKS} symlinks across all sources"

echo ""
echo "========================================================================"
echo "SUCCESS! STEP_1 annotations OCL pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/structure_NNN/1-output/  Annogroups + phylogenetic data"
echo "  OUTPUT_pipeline/structure_NNN/2-output/  Annogroup origins"
echo "  OUTPUT_pipeline/structure_NNN/3-output/  Conservation/loss patterns"
echo "  OUTPUT_pipeline/structure_NNN/4-output/  Comprehensive OCL summaries"
echo "  OUTPUT_pipeline/structure_NNN/5-output/  Species-tree deconvolution (species + protein counts per clade)"
echo "  OUTPUT_pipeline/structure_NNN/6-output/  Validation reports + QC metrics"
echo "  OUTPUT_pipeline/composite_clades/        Composite clades (computed once)"
echo ""
echo "Primary downstream file (per structure):"
echo "  4_ai-{structure}_annogroups-complete_ocl_summary-all_types.tsv"
echo ""
echo "Downstream symlinks (per source):"
echo "  ../../output_to_input/BLOCK_annotations_X_ocl/${SPECIES_SET}_<source>/"
echo ""
echo "Species set: ${SPECIES_SET}"
echo "Annotation sources: ${ANNOTATION_DATABASES} (fanned out per source)"
echo "Structures processed: ${STRUCTURE_COUNT}"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
