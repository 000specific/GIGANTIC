#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: Run STEP_2 standardization workflow locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC genomesDB STEP_2 - Standardize and Evaluate (Local)
################################################################################
#
# PURPOSE:
# Run the STEP_2 standardization workflow on your local machine using NextFlow.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Edit START_HERE-user_config.yaml with your project settings
# 2. Ensure STEP_1-sources is complete (provides proteomes, genomes, annotations)
# 3. Ensure phylonames subproject is complete (provides species naming)
# 4. Ensure INPUT_user/busco_lineages.txt exists for BUSCO evaluation
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN-workflow.sbatch
#
# WHAT THIS DOES:
# 1. Standardizes proteome filenames and FASTA headers with phylonames
# 2. Cleans proteome invalid residues (replaces '.' with 'X')
# 3. Creates phyloname-based symlinks for genomes and annotations
# 4. Calculates genome assembly statistics using gfastats
# 5. Runs BUSCO proteome completeness evaluation
# 6. Summarizes quality metrics and generates species manifest
#
# OUTPUT:
# Results in OUTPUT_pipeline/1-output through 6-output/
# Species manifest copied to ../../output_to_input/STEP_2-standardize_and_evaluate/
#
################################################################################

echo "========================================================================"
echo "GIGANTIC genomesDB STEP_2 Pipeline (Local)"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Activate GIGANTIC Environment (on-demand creation)
# ============================================================================
# The environment is created automatically on first run from the yml spec
# in conda_environments/. You can also pre-create all environments at once:
#   cd ../../../../ && bash RUN-setup_environments.sh
# ============================================================================

# GIGANTIC env naming convention: aiG-<subproject>-<block_or_step>-<optional_details>
# Per-BLOCK conda env. Auto-created on first run from ai/conda_environment.yml.
# mamba is preferred (much faster); conda is the fallback if mamba is missing.
# This env is SHARED across all 4 genomesDB STEPs.

ENV_NAME="aiG-genomesDB"
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
# Create symlinks for output_to_input directory
# ============================================================================

echo ""
echo "Publishing outputs to output_to_input/..."

# Determine the workflow directory name dynamically (supports COPYME and RUN_XX instances)
WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

# --- Subproject-root output_to_input (single canonical location) ---
SUBPROJECT_SHARED_DIR="../../output_to_input/STEP_2-standardize_and_evaluate"
mkdir -p "${SUBPROJECT_SHARED_DIR}"

# Remove any stale files/symlinks from previous runs
rm -f "${SUBPROJECT_SHARED_DIR}/gigantic_proteomes_cleaned"
rm -f "${SUBPROJECT_SHARED_DIR}/gigantic_genome_annotations"
rm -f "${SUBPROJECT_SHARED_DIR}/gigantic_genomes"

# Symlink cleaned proteomes for STEP_3 and STEP_4 access
ln -sf "../../STEP_2-standardize_and_evaluate/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/2-output/gigantic_proteomes_cleaned" \
    "${SUBPROJECT_SHARED_DIR}/gigantic_proteomes_cleaned"
echo "  gigantic_proteomes_cleaned -> symlinked"

# Symlink genome annotations for STEP_4 access
ln -sf "../../STEP_2-standardize_and_evaluate/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/3-output/gigantic_genome_annotations" \
    "${SUBPROJECT_SHARED_DIR}/gigantic_genome_annotations"
echo "  gigantic_genome_annotations -> symlinked"

# Symlink genomes for STEP_4 access
ln -sf "../../STEP_2-standardize_and_evaluate/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/3-output/gigantic_genomes" \
    "${SUBPROJECT_SHARED_DIR}/gigantic_genomes"
echo "  gigantic_genomes -> symlinked"

echo ""
echo "========================================================================"
echo "SUCCESS! STEP_2 pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/ through 6-output/"
echo ""
echo "Next: Review quality summary, then run STEP_3 and STEP_4"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
