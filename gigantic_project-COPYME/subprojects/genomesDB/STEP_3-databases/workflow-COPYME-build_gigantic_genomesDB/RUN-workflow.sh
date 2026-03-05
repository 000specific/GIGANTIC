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
# 3. Edit START_HERE-user_config.yaml if needed
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN-workflow.sbatch
#
# OUTPUTS:
# - Per-genome BLAST databases in OUTPUT_pipeline/2-output/gigantic-T1-blastp/
# - Databases symlinked to ../../output_to_input/STEP_3-databases/ for downstream use (by RUN-workflow.sh)
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
    # Check if required tools are available in PATH
    MISSING_TOOLS=""
    if ! command -v nextflow &> /dev/null; then
        MISSING_TOOLS="${MISSING_TOOLS} nextflow"
    fi
    if ! command -v makeblastdb &> /dev/null; then
        # Also try loading blast module before giving up
        module load blast 2>/dev/null || true
        if ! command -v makeblastdb &> /dev/null; then
            MISSING_TOOLS="${MISSING_TOOLS} makeblastdb"
        fi
    fi
    if ! command -v python3 &> /dev/null; then
        MISSING_TOOLS="${MISSING_TOOLS} python3"
    fi

    if [ -n "${MISSING_TOOLS}" ]; then
        echo "ERROR: Environment 'ai_gigantic_genomesdb' not found and required tools missing:${MISSING_TOOLS}"
        echo ""
        echo "Please run the environment setup script first:"
        echo ""
        echo "  cd ../../../../  # Go to project root"
        echo "  bash RUN-setup_environments.sh"
        echo ""
        echo "Or create this environment manually:"
        echo "  mamba env create -f ../../../../conda_environments/ai_gigantic_genomesdb.yml"
        echo ""
        exit 1
    fi
    echo "Using tools from PATH (environment not activated)"
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

# Check for species selection manifest
MANIFEST_PATH="../../output_to_input/STEP_2-standardize_and_evaluate/species_selection_manifest.tsv"

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
# Use awk to count Include=YES in the correct column (not grep which matches anywhere in the line)
INCLUDE_YES=$(awk -F'\t' 'NR==1{for(i=1;i<=NF;i++) if($i ~ /Include/) col=i} NR>1 && $col ~ /^[Yy][Ee][Ss]$/{c++} END{print c+0}' "${MANIFEST_PATH}")

echo "  [OK] Species selection manifest found"
echo "       Total species: ${TOTAL_SPECIES}"
echo "       Include=YES: ${INCLUDE_YES}"
echo ""

if [ "${INCLUDE_YES}" -eq 0 ]; then
    echo "ERROR: No species have Include=YES in the manifest!"
    echo "Please edit the manifest and set Include=YES for species to include."
    exit 1
fi

# Check for cleaned proteomes directory
PROTEOMES_DIR="../../output_to_input/STEP_2-standardize_and_evaluate/gigantic_proteomes_cleaned"

if [ ! -d "${PROTEOMES_DIR}" ]; then
    echo "ERROR: Cleaned proteomes directory not found!"
    echo ""
    echo "Expected location:"
    echo "  ${PROTEOMES_DIR}"
    echo ""
    echo "Please ensure STEP_2 is complete and its RUN-workflow.sh created the output_to_input symlinks."
    exit 1
fi

PROTEOME_COUNT=$(ls "${PROTEOMES_DIR}"/*.aa 2>/dev/null | wc -l)
echo "  [OK] Cleaned proteomes directory found (${PROTEOME_COUNT} proteome files)"

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
# Create symlinks for output_to_input directory
# ============================================================================
# Real files live in OUTPUT_pipeline/N-output/ (created by NextFlow above).
# Symlinks are created in ONE location at the subproject root:
#   ../../output_to_input/STEP_3-databases/
#
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

# Determine the workflow directory name dynamically (supports COPYME and RUN_XX instances)
WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

# --- Subproject-root output_to_input (single canonical location) ---
SUBPROJECT_SHARED_DIR="../../output_to_input/STEP_3-databases"
mkdir -p "${SUBPROJECT_SHARED_DIR}"

# Remove any stale BLAST database symlinks from previous runs
if [ -L "${SUBPROJECT_SHARED_DIR}/gigantic-T1-blastp" ]; then
    rm "${SUBPROJECT_SHARED_DIR}/gigantic-T1-blastp"
fi

ln -sf "../../STEP_3-databases/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/2-output/gigantic-T1-blastp" \
    "${SUBPROJECT_SHARED_DIR}/gigantic-T1-blastp"

echo "  output_to_input/STEP_3-databases/ -> symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! STEP_3 pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/  Filtered species manifest"
echo "  OUTPUT_pipeline/2-output/  Per-genome BLAST databases"
echo ""
echo "Downstream symlinks:"
echo "  ../../output_to_input/STEP_3-databases/  (for downstream subprojects)"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
