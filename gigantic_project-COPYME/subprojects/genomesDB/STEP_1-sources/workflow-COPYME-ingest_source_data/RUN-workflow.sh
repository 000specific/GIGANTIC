#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 13 | Purpose: Run source data ingestion NextFlow pipeline
# Human: Eric Edsinger

################################################################################
# GIGANTIC Source Data Ingestion Pipeline - Local Execution
################################################################################
#
# PURPOSE:
# Ingest user-provided source data files (proteomes, genomes, GFFs)
# into GIGANTIC structure.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Place your genomic resource files in INPUT_user/ at the project root
#    (see INPUT_user/README.md for naming conventions)
# 2. Create INPUT_user/source_manifest.tsv in this workflow directory
#    listing paths to your files in the project-level INPUT_user/
#    (see INPUT_user/source_manifest_example.tsv for format)
# 3. Edit ingest_sources_config.yaml with your project settings
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN-workflow.sbatch
#
# WHAT THE WORKFLOW DOES (2 steps, each with visible output):
#   Step 1 -> OUTPUT_pipeline/1-output/  Validate manifest (check files exist)
#   Step 2 -> OUTPUT_pipeline/2-output/  Ingest data (hard copy files)
#
# After pipeline: RUN-workflow.sh creates symlinks in ../../output_to_input/STEP_1-sources/
#
################################################################################

echo "========================================================================"
echo "GIGANTIC Source Data Ingestion Pipeline"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# Path to project-level INPUT_user (relative to this workflow)
INPUT_USER_PROJECT="../../../../../../INPUT_user"

# ============================================================================
# Resolve species list: workflow INPUT_user/ overrides project-level default
# ============================================================================
# Priority order:
#   1. Workflow INPUT_user/species_list.txt  (user override for this workflow)
#   2. Project INPUT_user/species_set/species_list.txt  (project-wide default)
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
# The environment is created automatically on first run from the yml spec
# in conda_environments/. You can also pre-create all environments at once:
#   cd ../../../../../../ && bash RUN-setup_environments.sh
# ============================================================================

ENV_NAME="ai_gigantic_genomesdb"
ENV_YML="../../../../../../conda_environments/${ENV_NAME}.yml"

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
# Check for source manifest
# ============================================================================
if [ ! -f "INPUT_user/source_manifest.tsv" ]; then
    echo "ERROR: Source manifest not found!"
    echo ""
    echo "Please create INPUT_user/source_manifest.tsv with your source data paths."
    echo "See INPUT_user/source_manifest_example.tsv for format."
    exit 1
fi

SPECIES_COUNT=$(grep -v "^#" INPUT_user/source_manifest.tsv | grep -v "^$" | grep -v "^genus_species" | wc -l)
echo "Species in manifest: ${SPECIES_COUNT}"
echo ""

if [ "$SPECIES_COUNT" -eq 0 ]; then
    echo "ERROR: No species found in manifest!"
    exit 1
fi

# ============================================================================
# Run NextFlow pipeline (all 3 steps)
# ============================================================================
echo "Running NextFlow pipeline..."
echo ""

nextflow run ai/main.nf

NF_EXIT_CODE=$?

echo ""
if [ $NF_EXIT_CODE -ne 0 ]; then
    echo "========================================================================"
    echo "FAILED! NextFlow exited with code ${NF_EXIT_CODE}"
    echo "Check logs above for details."
    echo "========================================================================"
    exit $NF_EXIT_CODE
fi

# ============================================================================
# Create symlinks for output_to_input directory
# ============================================================================
# Real files live in OUTPUT_pipeline/2-output/ (created by NextFlow above).
# Symlinks are created in ONE location at the subproject root:
#   ../../output_to_input/STEP_1-sources/
#
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
# ============================================================================

echo ""
echo "Creating symlinks for downstream workflows..."

# Determine the workflow directory name dynamically (supports COPYME and RUN_XX instances)
WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

# --- Subproject-root output_to_input (single canonical location) ---
SUBPROJECT_SHARED_DIR="../../output_to_input/STEP_1-sources"

# Data types to symlink
DATA_TYPES=("T1_proteomes" "genomes" "gene_annotations")

TOTAL_LINKED=0

for DATA_TYPE in "${DATA_TYPES[@]}"; do
    SOURCE_SUBDIR="OUTPUT_pipeline/2-output/${DATA_TYPE}"

    if [ ! -d "${SOURCE_SUBDIR}" ]; then
        continue
    fi

    # Subproject-root symlinks
    mkdir -p "${SUBPROJECT_SHARED_DIR}/${DATA_TYPE}"
    find "${SUBPROJECT_SHARED_DIR}/${DATA_TYPE}" -type l -delete 2>/dev/null

    LINKED=0

    for source_file in "${SOURCE_SUBDIR}"/*; do
        [ -e "$source_file" ] || continue

        filename=$(basename "$source_file")

        # Symlink from subproject output_to_input to real file
        ln -sf "../../../STEP_1-sources/${WORKFLOW_DIR_NAME}/${source_file}" \
            "${SUBPROJECT_SHARED_DIR}/${DATA_TYPE}/${filename}"

        LINKED=$((LINKED + 1))
    done

    TOTAL_LINKED=$((TOTAL_LINKED + LINKED))
    echo "  ${DATA_TYPE}: ${LINKED} symlinks created"
done

echo "  Total: ${TOTAL_LINKED} symlinks"
echo "  output_to_input/STEP_1-sources/ -> symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS!"
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/  Validation report"
echo "  OUTPUT_pipeline/2-output/  Ingested data"
echo ""
echo "Downstream symlinks:"
echo "  ../../output_to_input/STEP_1-sources/  (for downstream STEP_2)"
echo ""
echo "Next step: Run STEP_2-standardize_and_evaluate workflow"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
