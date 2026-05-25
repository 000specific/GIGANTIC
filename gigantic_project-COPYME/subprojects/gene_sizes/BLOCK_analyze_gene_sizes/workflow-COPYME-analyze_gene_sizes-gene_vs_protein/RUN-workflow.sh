#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Run gene_sizes analysis workflow locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC gene_sizes - Analyze Gene Sizes (Local)
################################################################################
#
# PURPOSE:
# Compute gene structure metrics from user-provided CDS interval data and
# produce genome-wide statistics, relative size ranks, and cross-species summaries.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Provide per-species gene structure TSV files in INPUT_user/
#    (see START_HERE-user_config.yaml for format details)
# 2. Copy or symlink the GIGANTIC species list to INPUT_user/gigantic_species_list.txt
# 3. Edit START_HERE-user_config.yaml to verify paths
# 4. (Optional) Set proteome_dir in config for GIGANTIC ID linkage
#
# FOR SLURM CLUSTERS:
# Edit START_HERE-user_config.yaml: set execution_mode: "slurm"
# Then run: bash RUN-workflow.sh  (this script self-submits to SLURM)
#
# WHAT THIS DOES:
# 1. Validates user-provided gene structure files against the GIGANTIC species set
#    - Species with valid data: PROCESSED
#    - Species without files: SKIPPED_NO_DATA (graceful)
#    - Species with incomplete data: SKIPPED_INCOMPLETE (graceful)
# 2. Extracts per-gene metrics: gene length, exonic/intronic length, exon count, protein size
# 3. Computes genome-wide statistics and relative rank (quantile) per species
# 4. Compiles cross-species summary tables with processing status
# 5. Creates output_to_input/BLOCK_analyze_gene_sizes/ symlinks for downstream subprojects
#
# OUTPUT:
# Results in OUTPUT_pipeline/1-output through 4-output/
# Downstream symlinks in ../../output_to_input/BLOCK_analyze_gene_sizes/
#
################################################################################

echo "========================================================================"
echo "GIGANTIC gene_sizes Pipeline (Local)"
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
# Self-submits as a SLURM job so heavy work (conda env creation, NextFlow
# pipeline) runs on a compute node -- never on the login node.

if [ "${EXECUTION_MODE}" == "slurm" ] && [ -z "${SLURM_JOB_ID}" ]; then
    echo "Execution mode: SLURM (submitting job)"
    echo ""

    SLURM_CPUS=$(read_config "cpus" "4")
    SLURM_MEM=$(read_config "memory_gb" "16")
    SLURM_TIME=$(read_config "time_hours" "4")
    SLURM_ACCOUNT=$(read_config "slurm_account" "")
    SLURM_QOS=$(read_config "slurm_qos" "")

    mkdir -p slurm_logs

    SBATCH_ARGS="--job-name=gene_sizes_gene_vs_protein"
    SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${SLURM_CPUS}"
    SBATCH_ARGS="${SBATCH_ARGS} --mem=${SLURM_MEM}gb"
    SBATCH_ARGS="${SBATCH_ARGS} --time=${SLURM_TIME}:00:00"
    SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/gene_sizes_gene_vs_protein-%j.log"

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
# The environment is created automatically on first run from the yml spec
# in ai/conda_environment.yml. You can also pre-create all environments at once:
#   cd ../../../../ && bash RUN-setup_environments.sh
# ============================================================================

# GIGANTIC env naming convention: aiG-<subproject>-<block_or_step>-<optional_details>
# BLOCK-shared env: BOTH gene_sizes workflows (all_inclusive + gene_vs_protein)
# use the same env (whichever runs first auto-creates it; the other reuses it).
ENV_NAME="aiG-gene_sizes-analyze_gene_sizes"
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
# Validate Prerequisites
# ============================================================================

echo "Validating prerequisites..."
echo ""

# Check config file exists
if [ ! -f "START_HERE-user_config.yaml" ]; then
    echo "ERROR: Configuration file not found!"
    echo "Expected: START_HERE-user_config.yaml"
    exit 1
fi
echo "  [OK] Configuration file found"

# Check INPUT_user directory exists
if [ ! -d "INPUT_user" ]; then
    echo "ERROR: INPUT_user/ directory not found!"
    echo "  Create it and add per-species gene structure TSV files."
    echo "  See START_HERE-user_config.yaml for format details."
    exit 1
fi
echo "  [OK] INPUT_user/ directory found"

echo ""

# ============================================================================
# Run NextFlow Pipeline
# ============================================================================

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
# Create symlinks for output_to_input directories
# ============================================================================
# Real files live in OUTPUT_pipeline/4-output/ (created by NextFlow above).
# Symlinks are created in a tier-specific subdirectory at the subproject root:
#   ../../output_to_input/BLOCK_analyze_gene_sizes/${TIER}/
#
# The tier (all_inclusive | gene_vs_protein) is derived from this workflow's
# own directory name so each tier writes to its own subdir and the two tiers
# never clobber each other. Symlink targets use absolute paths so they always
# resolve regardless of how this directory was renamed (COPYME vs RUN_N).
#
# gene_sizes creates per-species directories (speciesN_gigantic_gene_metrics,
# speciesN_gigantic_gene_sizes_summary) which are discovered dynamically.
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

# Derive tier name from this workflow directory's basename.
# Examples:
#   workflow-COPYME-analyze_gene_sizes-all_inclusive   -> all_inclusive
#   workflow-RUN_1-analyze_gene_sizes-gene_vs_protein  -> gene_vs_protein
WORKFLOW_NAME=$(basename "${SCRIPT_DIR}")
TIER=$(echo "${WORKFLOW_NAME}" | sed 's/.*-analyze_gene_sizes-//')

if [ -z "${TIER}" ] || [ "${TIER}" == "${WORKFLOW_NAME}" ]; then
    echo "ERROR: Could not derive tier name from workflow directory: ${WORKFLOW_NAME}"
    echo "  Expected pattern: workflow-<COPYME|RUN_N>-analyze_gene_sizes-<tier>"
    exit 1
fi

echo "  Tier: ${TIER}"

# --- Subproject-root output_to_input/BLOCK_analyze_gene_sizes/${TIER}/ ---
SHARED_DIR="../../output_to_input/BLOCK_analyze_gene_sizes/${TIER}"
mkdir -p "${SHARED_DIR}"

# Remove any stale symlinks from previous runs (within this tier subdir only)
for old_link in "${SHARED_DIR}"/species*_gigantic_gene_*; do
    if [ -L "$old_link" ]; then
        rm "$old_link"
    fi
done

# Create symlinks for each species directory in 4-output/.
# Use absolute paths (via SCRIPT_DIR) so symlinks always resolve.
for species_dir in OUTPUT_pipeline/4-output/species*_gigantic_*; do
    if [ -d "$species_dir" ] || [ -L "$species_dir" ]; then
        dir_name=$(basename "$species_dir")
        ln -sf "${SCRIPT_DIR}/OUTPUT_pipeline/4-output/${dir_name}" \
            "${SHARED_DIR}/${dir_name}"
    fi
done

echo "  output_to_input/BLOCK_analyze_gene_sizes/${TIER}/ -> symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! gene_sizes pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/  Species processing status"
echo "  OUTPUT_pipeline/2-output/  Per-species gene metrics"
echo "  OUTPUT_pipeline/3-output/  Ranked metrics and genome summaries"
echo "  OUTPUT_pipeline/4-output/  Cross-species summary and downstream dirs"
echo ""
echo "Downstream symlinks:"
echo "  ../../output_to_input/BLOCK_analyze_gene_sizes/  (for downstream subprojects)"
echo ""
echo "Published directories:"
echo "  speciesN_gigantic_gene_metrics/         Per-species ranked gene metrics"
echo "  speciesN_gigantic_gene_sizes_summary/   Cross-species summary statistics"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
