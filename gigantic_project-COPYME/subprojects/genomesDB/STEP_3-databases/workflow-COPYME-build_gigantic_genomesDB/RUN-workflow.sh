#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 06 | Purpose: Run STEP_3 database building workflow
# Human: Eric Edsinger

################################################################################
# GIGANTIC genomesDB STEP_3 - Build BLAST Databases
################################################################################
#
# PURPOSE:
# Build per-genome BLAST databases from ALL standardized proteomes in STEP_2.
# Each species gets its own individual BLAST database.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Ensure STEP_2-standardize_and_evaluate is complete
# 2. Edit START_HERE-user_config.yaml if needed
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN-workflow.sbatch
#
# OUTPUTS:
# - Per-genome BLAST databases in OUTPUT_pipeline/1-output/gigantic-T1-blastp/
# - Databases symlinked to ../../output_to_input/STEP_3-databases/ for downstream use
#
################################################################################

echo "========================================================================"
echo "GIGANTIC genomesDB STEP_3 - Build BLAST Databases"
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
    MISSING_TOOLS=""
    if ! command -v nextflow &> /dev/null; then
        MISSING_TOOLS="${MISSING_TOOLS} nextflow"
    fi
    if ! command -v makeblastdb &> /dev/null; then
        module load blast 2>/dev/null || true
        if ! command -v makeblastdb &> /dev/null; then
            MISSING_TOOLS="${MISSING_TOOLS} makeblastdb"
        fi
    fi
    if ! command -v python3 &> /dev/null; then
        MISSING_TOOLS="${MISSING_TOOLS} python3"
    fi

    if [ -n "${MISSING_TOOLS}" ]; then
        echo "ERROR: Required tools missing:${MISSING_TOOLS}"
        echo "Install the ai_gigantic_genomesdb conda environment or ensure tools are in PATH."
        exit 1
    fi
    echo "Using tools from PATH (environment not activated)"
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

echo ""
echo "Creating symlinks for downstream subprojects..."

WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"
SUBPROJECT_SHARED_DIR="../../output_to_input/STEP_3-databases"
mkdir -p "${SUBPROJECT_SHARED_DIR}"

# Remove stale symlink from previous runs
if [ -L "${SUBPROJECT_SHARED_DIR}/gigantic-T1-blastp" ]; then
    rm "${SUBPROJECT_SHARED_DIR}/gigantic-T1-blastp"
fi

ln -sf "../../STEP_3-databases/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/1-output/gigantic-T1-blastp" \
    "${SUBPROJECT_SHARED_DIR}/gigantic-T1-blastp"

echo "  output_to_input/STEP_3-databases/gigantic-T1-blastp -> symlink created"

echo ""
echo "========================================================================"
echo "SUCCESS! STEP_3 pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/  Per-genome BLAST databases"
echo ""
echo "Downstream symlinks:"
echo "  ../../output_to_input/STEP_3-databases/  (for downstream subprojects)"
echo "========================================================================"
echo "Completed: $(date)"

conda deactivate 2>/dev/null || true
