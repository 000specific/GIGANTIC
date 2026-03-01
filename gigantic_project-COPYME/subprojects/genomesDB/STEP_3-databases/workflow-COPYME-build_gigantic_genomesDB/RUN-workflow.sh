#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 27 | Purpose: Run STEP_3 database building workflow locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC genomesDB STEP_3 - Build BLAST Databases (Local)
################################################################################
#
# PURPOSE:
# Build per-genome BLAST databases from standardized proteomes.
# Each species gets its own individual BLAST database.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Ensure STEP_2-standardize_and_evaluate is complete
# 2. User should have edited the species_selection_manifest.tsv (Include=YES/NO)
# 3. Edit databases_config.yaml if needed
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN-workflow.sbatch
#
# OUTPUTS:
# - Per-genome BLAST databases in OUTPUT_pipeline/2-output/gigantic-T1-blastp/
# - Databases symlinked to output_to_input/ for downstream use (by RUN-workflow.sh)
#
################################################################################

echo "========================================================================"
echo "GIGANTIC genomesDB STEP_3 - Build BLAST Databases (Local)"
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
    # Check if nextflow and makeblastdb are available
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: Environment 'ai_gigantic_genomesdb' not found!"
        echo ""
        echo "Please ensure the environment is set up with:"
        echo "  - nextflow"
        echo "  - makeblastdb (BLAST+)"
        echo "  - python3"
        echo ""
        exit 1
    fi

    # Also try loading blast module
    module load blast 2>/dev/null || true

    echo "Using NextFlow from PATH"
fi

echo ""

# ============================================================================
# Validate Prerequisites
# ============================================================================

echo "Validating prerequisites..."
echo ""

# Check config file exists
if [ ! -f "databases_config.yaml" ]; then
    echo "ERROR: Configuration file not found!"
    echo "Expected: databases_config.yaml"
    exit 1
fi
echo "  [OK] Configuration file found"

# Check for species selection manifest
MANIFEST_PATH="../../output_to_input/species_selection_manifest.tsv"

if [ ! -f "${MANIFEST_PATH}" ]; then
    echo "ERROR: Species selection manifest not found!"
    echo ""
    echo "Expected location:"
    echo "  ${MANIFEST_PATH}"
    echo ""
    echo "Please ensure STEP_2 is complete and species_selection_manifest.tsv exists."
    exit 1
fi

TOTAL_SPECIES=$(tail -n +2 "${MANIFEST_PATH}" | grep -v "^#" | wc -l)
INCLUDE_YES=$(tail -n +2 "${MANIFEST_PATH}" | grep -v "^#" | grep -i "YES" | wc -l || echo 0)

echo "  [OK] Species selection manifest found"
echo "       Total species: ${TOTAL_SPECIES}"
echo "       Include=YES: ${INCLUDE_YES}"
echo ""

if [ "${INCLUDE_YES}" -eq 0 ]; then
    echo "ERROR: No species have Include=YES in the manifest!"
    echo "Please edit the manifest and set Include=YES for species to include."
    exit 1
fi

# Check makeblastdb
if ! command -v makeblastdb &> /dev/null; then
    echo "WARNING: makeblastdb not found in PATH"
    echo "Process 002 will fail unless BLAST+ is available."
    echo ""
fi

echo ""

# ============================================================================
# Run NextFlow Pipeline
# ============================================================================

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
# Create symlinks for output_to_input directories
# ============================================================================
# Real files live in OUTPUT_pipeline/N-output/ (created by NextFlow above).
# Symlinks are created in two locations:
#   1. ../../output_to_input/  (canonical, for downstream subprojects)
#   2. ai/output_to_input/     (archival, with this workflow run)
#
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

# --- STEP-level output_to_input (canonical) ---
STEP_SHARED_DIR="../../output_to_input"
mkdir -p "${STEP_SHARED_DIR}"

# Remove any stale BLAST database symlinks from previous runs
# (use -maxdepth 1 to only remove top-level symlinks, not from other STEPs)
if [ -L "${STEP_SHARED_DIR}/gigantic-T1-blastp" ]; then
    rm "${STEP_SHARED_DIR}/gigantic-T1-blastp"
fi

ln -sf "../STEP_3-databases/workflow-COPYME-build_gigantic_genomesDB/OUTPUT_pipeline/2-output/gigantic-T1-blastp" \
    "${STEP_SHARED_DIR}/gigantic-T1-blastp"

echo "  STEP output_to_input/ -> symlinks created"

# --- Workflow-level ai/output_to_input (archival) ---
WORKFLOW_SHARED_DIR="ai/output_to_input"
mkdir -p "${WORKFLOW_SHARED_DIR}"

# Remove any stale symlinks from previous runs
find "${WORKFLOW_SHARED_DIR}" -type l -delete 2>/dev/null

ln -sf "../../OUTPUT_pipeline/2-output/gigantic-T1-blastp" \
    "${WORKFLOW_SHARED_DIR}/gigantic-T1-blastp"

echo "  Workflow ai/output_to_input/ -> symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! STEP_3 pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/  Filtered species manifest"
echo "  OUTPUT_pipeline/2-output/  Per-genome BLAST databases"
echo ""
echo "Downstream symlinks:"
echo "  ../../output_to_input/  (for downstream subprojects)"
echo "  ai/output_to_input/     (archival with this run)"
echo "========================================================================"
echo "Completed: $(date)"
