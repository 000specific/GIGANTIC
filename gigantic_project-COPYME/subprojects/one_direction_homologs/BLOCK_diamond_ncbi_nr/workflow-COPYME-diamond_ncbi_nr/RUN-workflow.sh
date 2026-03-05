#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 01 | Purpose: Run DIAMOND NCBI nr search pipeline locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC One-Direction Homologs Pipeline - Local Execution
################################################################################
#
# PURPOSE:
# Run the DIAMOND NCBI nr search workflow on your local machine using NextFlow.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Edit START_HERE-user_config.yaml with your DIAMOND database path
# 2. Create INPUT_user/proteome_manifest.tsv with your species and proteome paths
#    (in this workflow directory)
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN-workflow.sbatch
#
# WHAT THIS DOES:
# 1. Validates proteome files exist and are valid FASTA
# 2. Splits proteomes into N parts for parallel DIAMOND search
# 3. Runs DIAMOND blastp against NCBI nr database
# 4. Combines results per species
# 5. Identifies top self/non-self hits with NCBI headers and sequences
# 6. Compiles master statistics table
#
# OUTPUT:
# Results in OUTPUT_pipeline/ (numbered subdirectories per script)
# Summary: OUTPUT_pipeline/6-output/6_ai-all_species_statistics.tsv
#
################################################################################

echo "========================================================================"
echo "GIGANTIC One-Direction Homologs Pipeline (Local)"
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
#   cd ../../../../ && bash RUN-setup_environments.sh
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

# Check for proteome manifest
if [ ! -f "INPUT_user/proteome_manifest.tsv" ]; then
    echo "ERROR: Proteome manifest not found!"
    echo ""
    echo "Please create a manifest at one of these locations:"
    echo ""
    echo "  Workflow-specific:"
    echo "    INPUT_user/proteome_manifest.tsv  (in this workflow directory)"
    echo ""
    echo "See INPUT_user/proteome_manifest_example.tsv for format."
    echo ""
    exit 1
fi

# Check for DIAMOND database in config
CONFIG_FILE="START_HERE-user_config.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Configuration file not found: ${CONFIG_FILE}"
    exit 1
fi

# Show manifest summary
SPECIES_COUNT=$(grep -v "^#" INPUT_user/proteome_manifest.tsv | grep -v "^$" | tail -n +2 | wc -l)
echo "Species in manifest: ${SPECIES_COUNT}"
echo ""

# Run NextFlow pipeline
echo "Running NextFlow pipeline..."
echo ""

nextflow run ai/main.nf

EXIT_CODE=$?

echo ""

if [ $EXIT_CODE -ne 0 ]; then
    echo "========================================================================"
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "Check the logs above for error details."
    echo "========================================================================"
    echo "Completed: $(date)"
    exit $EXIT_CODE
fi

# ============================================================================
# Create symlinks for output_to_input directory
# ============================================================================
# Real files live in OUTPUT_pipeline/N-output/ (created by NextFlow above).
# Symlinks are created in the subproject-root output_to_input/ directory:
#   ../../output_to_input/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits/
#
# This is the single canonical location for downstream subprojects.
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

# --- Subproject-root output_to_input (canonical) ---
# Symlink location: ../../output_to_input/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits/
# Real files:       OUTPUT_pipeline/5-output/ and OUTPUT_pipeline/6-output/
# Relative from symlink to real: ../../../BLOCK_diamond_ncbi_nr/workflow-COPYME-diamond_ncbi_nr/OUTPUT_pipeline/...

OUTPUT_TO_INPUT_DIR="../../output_to_input/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits"
mkdir -p "${OUTPUT_TO_INPUT_DIR}"

# Remove any stale symlinks from previous runs
find "${OUTPUT_TO_INPUT_DIR}" -type l -delete 2>/dev/null

for file_path in OUTPUT_pipeline/5-output/*_top_hits.tsv OUTPUT_pipeline/5-output/*_statistics.tsv; do
    [ -f "${file_path}" ] || continue
    file_name="$(basename "${file_path}")"
    ln -sf "../../../BLOCK_diamond_ncbi_nr/workflow-COPYME-diamond_ncbi_nr/${file_path}" "${OUTPUT_TO_INPUT_DIR}/${file_name}"
done

ln -sf "../../../BLOCK_diamond_ncbi_nr/workflow-COPYME-diamond_ncbi_nr/OUTPUT_pipeline/6-output/6_ai-all_species_statistics.tsv" \
    "${OUTPUT_TO_INPUT_DIR}/all_species_statistics.tsv"

echo "  output_to_input/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits/ -> symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! Pipeline completed."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/ through 6-output/"
echo ""
echo "Downstream symlinks:"
echo "  ../../output_to_input/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits/  (for downstream subprojects)"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true

exit 0
