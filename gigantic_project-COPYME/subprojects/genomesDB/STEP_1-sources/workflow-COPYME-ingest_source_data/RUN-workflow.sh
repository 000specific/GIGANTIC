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
# 1. Place your source files somewhere accessible (e.g., user_research/)
# 2. Create INPUT_user/source_manifest.tsv listing your source data paths
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
# After pipeline: RUN-workflow.sh creates symlinks for downstream STEP_2
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

# ============================================================================
# Activate GIGANTIC Environment
# ============================================================================
module load conda 2>/dev/null || true

if conda activate ai_gigantic_genomesdb 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_genomesdb"
else
    if ! command -v nextflow &> /dev/null; then
        echo "WARNING: Environment 'ai_gigantic_genomesdb' not found!"
        echo ""
        module load nextflow 2>/dev/null || true
        if ! command -v nextflow &> /dev/null; then
            echo "ERROR: NextFlow not found!"
            echo ""
            echo "Please run the environment setup script first:"
            echo "  cd ../../../../  # Go to project root"
            echo "  bash RUN-setup_environments.sh"
            exit 1
        fi
    fi
    echo "Using NextFlow from PATH"
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
# Create symlinks for output_to_input directories
# ============================================================================
# Real files live in OUTPUT_pipeline/2-output/ (created by NextFlow above).
# Symlinks are created in two locations:
#   1. ../output_to_input/  (STEP-level, for downstream STEP_2)
#   2. ai/output_to_input/  (archival, with this workflow run)
#
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
# ============================================================================

echo ""
echo "Creating symlinks for downstream workflows..."

WORKFLOW_NAME=$(basename "${SCRIPT_DIR}")

# --- STEP-level output_to_input ---
STEP_SHARED_DIR="../output_to_input"

# --- Workflow-level ai/output_to_input (archival) ---
WORKFLOW_SHARED_DIR="ai/output_to_input"

# Data types to symlink
DATA_TYPES=("T1_proteomes" "genomes" "gene_annotations")

TOTAL_LINKED=0

for DATA_TYPE in "${DATA_TYPES[@]}"; do
    SOURCE_SUBDIR="OUTPUT_pipeline/2-output/${DATA_TYPE}"

    if [ ! -d "${SOURCE_SUBDIR}" ]; then
        continue
    fi

    # STEP-level symlinks
    mkdir -p "${STEP_SHARED_DIR}/${DATA_TYPE}"
    find "${STEP_SHARED_DIR}/${DATA_TYPE}" -type l -delete 2>/dev/null

    # Workflow-level archival symlinks
    mkdir -p "${WORKFLOW_SHARED_DIR}/${DATA_TYPE}"
    find "${WORKFLOW_SHARED_DIR}/${DATA_TYPE}" -type l -delete 2>/dev/null

    LINKED=0

    for source_file in "${SOURCE_SUBDIR}"/*; do
        [ -e "$source_file" ] || continue

        filename=$(basename "$source_file")

        # STEP-level symlink
        ln -sf "../../${WORKFLOW_NAME}/${source_file}" \
            "${STEP_SHARED_DIR}/${DATA_TYPE}/${filename}"

        # Workflow-level archival symlink
        ln -sf "../../../${source_file}" \
            "${WORKFLOW_SHARED_DIR}/${DATA_TYPE}/${filename}"

        LINKED=$((LINKED + 1))
    done

    TOTAL_LINKED=$((TOTAL_LINKED + LINKED))
    echo "  ${DATA_TYPE}: ${LINKED} symlinks created"
done

echo "  Total: ${TOTAL_LINKED} symlinks"
echo "  STEP output_to_input/ -> symlinks created"
echo "  Workflow ai/output_to_input/ -> symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS!"
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/  Validation report"
echo "  OUTPUT_pipeline/2-output/  Ingested data"
echo ""
echo "Downstream symlinks:"
echo "  ../output_to_input/T1_proteomes/   (for downstream STEP_2)"
echo "  ../output_to_input/genomes/        (for downstream STEP_2)"
echo "  ../output_to_input/gene_annotations/ (for downstream STEP_2)"
echo "  ai/output_to_input/                (archival with this run)"
echo ""
echo "Next step: Run STEP_2-standardize_and_evaluate workflow"
echo "========================================================================"
echo "Completed: $(date)"
