#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Run phylonames STEP 2 - apply user phylonames
# Human: Eric Edsinger

################################################################################
# GIGANTIC Phylonames Pipeline - STEP 2: Apply User Phylonames
################################################################################
#
# PURPOSE:
# Apply user-provided custom phylonames to override STEP 1 output.
# This is STEP 2 of a 2-STEP workflow.
#
# PREREQUISITES:
# 1. STEP 1 must have been run successfully
# 2. Review STEP 1 taxonomy summary to identify species needing overrides
# 3. Create INPUT_user/user_phylonames.tsv with your custom phylonames
#
# USAGE:
#   bash RUN-workflow.sh
#
# FOR SLURM CLUSTERS:
#   sbatch RUN-workflow.sbatch
#
# INPUT:
# - STEP 1 mapping from: ../../output_to_input/STEP_1-generate_and_evaluate/maps/
# - User phylonames from: INPUT_user/user_phylonames.tsv
#
# OUTPUT:
# Your updated mapping file will be at:
#   ../../output_to_input/maps/[project_name]_map-genus_species_X_phylonames.tsv
#
################################################################################

echo "========================================================================"
echo "GIGANTIC Phylonames Pipeline - STEP 2: Apply User Phylonames"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Verify STEP 1 output exists
# ============================================================================

STEP1_MAPS="../../output_to_input/STEP_1-generate_and_evaluate/maps"

if [ ! -d "${STEP1_MAPS}" ] || [ -z "$(ls -A "${STEP1_MAPS}" 2>/dev/null)" ]; then
    echo "ERROR: STEP 1 output not found!"
    echo ""
    echo "STEP 1 must be run before STEP 2."
    echo "Expected mapping files in: ${STEP1_MAPS}"
    echo ""
    echo "Run STEP 1 first:"
    echo "  cd ../../STEP_1-generate_and_evaluate/workflow-COPYME-generate_phylonames/"
    echo "  bash RUN-workflow.sh"
    echo ""
    exit 1
fi

echo "STEP 1 mapping found in: ${STEP1_MAPS}"
echo "  $(ls ${STEP1_MAPS}/*.tsv 2>/dev/null | wc -l) mapping file(s)"
echo ""

# ============================================================================
# Check for user phylonames file
# ============================================================================

if [ ! -f "INPUT_user/user_phylonames.tsv" ]; then
    echo "ERROR: User phylonames file not found!"
    echo ""
    echo "Please create: INPUT_user/user_phylonames.tsv"
    echo ""
    echo "Format: TSV with columns: genus_species<TAB>custom_phyloname"
    echo "Example:"
    echo "  Monosiga_brevicollis_MX1	Holozoa_Choanozoa_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1"
    echo ""
    echo "See INPUT_user/user_phylonames_example.tsv for a template."
    echo ""
    exit 1
fi

USER_SPECIES_COUNT=$(grep -v "^#" INPUT_user/user_phylonames.tsv | grep -v "^$" | wc -l)
echo "User phylonames: ${USER_SPECIES_COUNT} species to override"
echo ""

# ============================================================================
# Activate GIGANTIC Environment (on-demand creation)
# ============================================================================

ENV_NAME="ai_gigantic_phylonames"
ENV_YML="../../../../conda_environments/${ENV_NAME}.yml"

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

nextflow run ai/main.nf ${RESUME_FLAG}

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
# Symlinks are created in TWO locations:
#   1. ../../output_to_input/STEP_2-apply_user_phylonames/maps/  (STEP-specific)
#   2. ../../output_to_input/maps/  (convenience symlink updated to point to STEP_2)
#
# This follows GIGANTIC convention: between STEPs, read from output_to_input/
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

# Read project name from config (nested YAML: project: name: "value")
PROJECT_NAME=$(grep "^  name:" START_HERE-user_config.yaml 2>/dev/null | head -1 | awk '{print $2}' | tr -d '"' | tr -d "'")
if [ -z "${PROJECT_NAME}" ]; then
    PROJECT_NAME="my_project"
fi

# Determine the workflow directory name dynamically (supports COPYME and RUN_XX instances)
WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

# --- STEP-specific output_to_input ---
STEP_SHARED_DIR="../../output_to_input/STEP_2-apply_user_phylonames/maps"
mkdir -p "${STEP_SHARED_DIR}"

# Remove any stale symlinks from previous runs
find "${STEP_SHARED_DIR}" -type l -delete 2>/dev/null

# Symlink the final mapping from 1-output (same filename as STEP_1 for downstream compatibility)
ln -sf "../../../STEP_2-apply_user_phylonames/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/1-output/final_project_mapping.tsv" \
    "${STEP_SHARED_DIR}/${PROJECT_NAME}_map-genus_species_X_phylonames.tsv"

echo "  output_to_input/STEP_2-apply_user_phylonames/maps/ -> symlinks created"

# --- Update convenience symlink: output_to_input/maps/ now points to STEP_2 ---
# (This overrides the STEP_1 convenience symlink)
CONVENIENCE_DIR="../../output_to_input/maps"
rm -rf "${CONVENIENCE_DIR}" 2>/dev/null
ln -sf "STEP_2-apply_user_phylonames/maps" "${CONVENIENCE_DIR}"

echo "  output_to_input/maps/ -> STEP_2-apply_user_phylonames/maps/ (updated convenience symlink)"

echo ""
echo "========================================================================"
echo "SUCCESS! STEP 2 complete - User phylonames applied."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/  Final mapping with user phylonames"
echo "  OUTPUT_pipeline/2-output/  Updated taxonomy summary"
echo ""
echo "Downstream symlinks:"
echo "  ../../output_to_input/maps/  (updated to point to STEP 2 output)"
echo ""
echo "Note: Clades differing from NCBI are marked UNOFFICIAL."
echo "      Set mark_unofficial: false in config to disable."
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
