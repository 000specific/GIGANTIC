#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Run phylonames STEP 1 - generate and evaluate
# Human: Eric Edsinger

################################################################################
# GIGANTIC Phylonames Pipeline - STEP 1: Generate and Evaluate
################################################################################
#
# PURPOSE:
# Generate phylonames from NCBI taxonomy for your species list.
# This is STEP 1 of a 2-STEP workflow.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Edit START_HERE-user_config.yaml with your project settings
# 2. Species list is loaded from (in priority order):
#    a. INPUT_user/species_list.txt  (workflow-level override, if present)
#    b. ../../../../INPUT_user/species_set/species_list.txt  (project-level default)
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN-workflow.sbatch
#
# WHAT THIS DOES:
# 1. Downloads NCBI taxonomy database (~2GB, skipped if already exists)
# 2. Generates phylonames for all NCBI species (~5-10 minutes)
# 3. Creates your project-specific mapping file
# 4. Generates taxonomy summary for your review
#
# AFTER RUNNING:
# Review the taxonomy summary in OUTPUT_pipeline/4-output/ for:
#   - NOTINNCBI species (not found in NCBI taxonomy)
#   - Numbered clades (e.g., Kingdom6555) that need meaningful names
# If changes are needed, use STEP 2 to apply custom phylonames.
#
# OUTPUT:
# Your mapping file will be at:
#   ../../output_to_input/maps/[project_name]_map-genus_species_X_phylonames.tsv
#
################################################################################

echo "========================================================================"
echo "GIGANTIC Phylonames Pipeline - STEP 1: Generate and Evaluate"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# Path to project-level INPUT_user (relative to this workflow)
INPUT_USER_PROJECT="../../../../INPUT_user"

# ============================================================================
# Resolve species list: workflow INPUT_user/ overrides project-level default
# ============================================================================
# Priority order:
#   1. Workflow INPUT_user/species_list.txt  (user override for this workflow)
#   2. Project INPUT_user/species_set/species_list.txt  (project-wide default)
#
# If the workflow has its own species_list.txt, it takes priority (user override).
# Otherwise, copy the project-level default into the workflow for this run.
# ============================================================================
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
# This workflow requires:
#   - conda environment: ai_gigantic_phylonames (Python, wget, etc.)
#   - NextFlow: from conda env OR system module
#
# The environment is created automatically on first run from the yml spec
# in conda_environments/. You can also pre-create all environments at once:
#   cd ../../../../ && bash RUN-setup_environments.sh
#
# NextFlow availability:
#   - If installed in conda env: used automatically
#   - If not in conda env: falls back to "module load nextflow" (HPC systems)
#   - If neither available: exits with error and instructions
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

# Check for species list
if [ ! -f "INPUT_user/species_list.txt" ]; then
    echo "ERROR: Species list not found!"
    echo ""
    echo "Please add your species to one of these locations:"
    echo ""
    echo "  RECOMMENDED (project-wide):"
    echo "    INPUT_user/species_set/species_list.txt  (at project root)"
    echo ""
    echo "  OR workflow-specific:"
    echo "    INPUT_user/species_list.txt  (in this workflow directory)"
    echo ""
    echo "Format: one species per line, Genus_species (e.g., Homo_sapiens)"
    echo ""
    exit 1
fi

# Show species count
SPECIES_COUNT=$(grep -v "^#" INPUT_user/species_list.txt | grep -v "^$" | wc -l)
echo "Species in your list: ${SPECIES_COUNT}"
echo ""

# Run NextFlow pipeline
echo "Running NextFlow pipeline..."
echo ""

nextflow run ai/main.nf

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
#   1. ../../output_to_input/STEP_1-generate_and_evaluate/maps/  (STEP-specific)
#   2. ../../output_to_input/maps/  (convenience symlink for downstream)
#
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
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
STEP_SHARED_DIR="../../output_to_input/STEP_1-generate_and_evaluate/maps"
mkdir -p "${STEP_SHARED_DIR}"

# Remove any stale symlinks from previous runs
find "${STEP_SHARED_DIR}" -type l -delete 2>/dev/null

# Symlink the project mapping from 3-output
ln -sf "../../../STEP_1-generate_and_evaluate/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/3-output/${PROJECT_NAME}_map-genus_species_X_phylonames.tsv" \
    "${STEP_SHARED_DIR}/${PROJECT_NAME}_map-genus_species_X_phylonames.tsv"

echo "  output_to_input/STEP_1-generate_and_evaluate/maps/ -> symlinks created"

# --- Convenience symlink: output_to_input/maps/ points to STEP_1 ---
# (STEP_2 will update this to point to its own output if run later)
CONVENIENCE_DIR="../../output_to_input/maps"
rm -rf "${CONVENIENCE_DIR}" 2>/dev/null
ln -sf "STEP_1-generate_and_evaluate/maps" "${CONVENIENCE_DIR}"

echo "  output_to_input/maps/ -> STEP_1-generate_and_evaluate/maps/ (convenience symlink)"

echo ""
echo "========================================================================"
echo "SUCCESS! STEP 1 complete - Phylonames generated."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/2-output/  NCBI phylonames data"
echo "  OUTPUT_pipeline/3-output/  Project-specific mapping"
echo "  OUTPUT_pipeline/4-output/  Taxonomy summary"
echo ""
echo "Downstream symlinks:"
echo "  ../../output_to_input/maps/  (for downstream subprojects)"
echo ""
echo "NEXT STEP: Review the taxonomy summary for:"
echo "  - NOTINNCBI species (not found in NCBI taxonomy)"
echo "  - Numbered clades (e.g., Kingdom6555) that need meaningful names"
echo ""
echo "If changes are needed, use STEP 2 to apply custom phylonames:"
echo "  cd ../../STEP_2-apply_user_phylonames/workflow-COPYME-apply_user_phylonames/"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
