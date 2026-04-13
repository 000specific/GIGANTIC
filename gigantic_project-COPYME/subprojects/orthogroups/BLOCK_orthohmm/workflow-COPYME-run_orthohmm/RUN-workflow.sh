#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 06 | Purpose: Run OrthoHMM Nextflow pipeline
# Human: Eric Edsinger

################################################################################
# GIGANTIC Orthogroups - BLOCK OrthoHMM Pipeline
################################################################################
#
# PURPOSE:
# Run the OrthoHMM orthogroup detection workflow using NextFlow.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Edit START_HERE-user_config.yaml with your project settings
# 2. Ensure genomesDB STEP_4 is complete (provides cleaned proteomes)
# 3. Ensure conda environment ai_gigantic_orthogroups_orthohmm is created
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN-workflow.sbatch
#
# WHAT THIS DOES:
# 1. Validates proteomes from genomesDB STEP_4 output
# 2. Converts FASTA headers to short IDs for OrthoHMM compatibility
# 3. Runs OrthoHMM clustering (diamond + HMM-based orthogroup detection)
# 4. Restores full GIGANTIC identifiers in results
# 5. Generates summary statistics
# 6. Per-species QC analysis
# 7. Writes run log
#
# OUTPUT:
# Results in OUTPUT_pipeline/1-output through 6-output/
# Symlinks created in ../../output_to_input/BLOCK_orthohmm/
#
################################################################################

set -e

echo "========================================================================"
echo "GIGANTIC Orthogroups - OrthoHMM Pipeline"
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

# Load conda module (required on HPC systems like HiPerGator)
module load conda 2>/dev/null || true

# Activate the orthohmm environment
if conda activate ai_gigantic_orthogroups_orthohmm 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_orthogroups_orthohmm"
else
    # Check if required tools are available in PATH
    MISSING_TOOLS=""
    if ! command -v nextflow &> /dev/null; then
        MISSING_TOOLS="${MISSING_TOOLS} nextflow"
    fi
    if ! command -v orthohmm &> /dev/null; then
        MISSING_TOOLS="${MISSING_TOOLS} orthohmm"
    fi
    if ! command -v diamond &> /dev/null; then
        MISSING_TOOLS="${MISSING_TOOLS} diamond"
    fi

    if [ -n "${MISSING_TOOLS}" ]; then
        echo "ERROR: Environment 'ai_gigantic_orthogroups_orthohmm' not found and required tools missing:${MISSING_TOOLS}"
        echo ""
        echo "Please run the environment setup script first:"
        echo ""
        echo "  cd ../../../../  # Go to project root"
        echo "  bash RUN-setup_environments.sh"
        echo ""
        echo "Or create this environment manually:"
        echo "  mamba env create -f ../../../../conda_environments/ai_gigantic_orthogroups_orthohmm.yml"
        echo ""
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

nextflow run ai/main.nf ${RESUME_FLAG} \
    -c ai/nextflow.config

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
#   ../../output_to_input/BLOCK_orthohmm/
#
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
# ============================================================================

echo ""
echo "Publishing outputs to output_to_input/..."

# Determine the workflow directory name dynamically (supports COPYME and RUN_XX instances)
WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

# --- Subproject-root output_to_input (single canonical location) ---
SUBPROJECT_SHARED_DIR="../../output_to_input/BLOCK_orthohmm"
mkdir -p "${SUBPROJECT_SHARED_DIR}"

# Remove any stale symlinks from previous runs
find "${SUBPROJECT_SHARED_DIR}" -type l -delete 2>/dev/null

ln -sf "../../BLOCK_orthohmm/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/4-output/4_ai-orthogroups_gigantic_ids.tsv" \
    "${SUBPROJECT_SHARED_DIR}/orthogroups_gigantic_ids.tsv"
ln -sf "../../BLOCK_orthohmm/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/4-output/4_ai-gene_count_gigantic_ids.tsv" \
    "${SUBPROJECT_SHARED_DIR}/gene_count_gigantic_ids.tsv"
ln -sf "../../BLOCK_orthohmm/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/5-output/5_ai-summary_statistics.tsv" \
    "${SUBPROJECT_SHARED_DIR}/summary_statistics.tsv"
ln -sf "../../BLOCK_orthohmm/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/6-output/6_ai-per_species_summary.tsv" \
    "${SUBPROJECT_SHARED_DIR}/per_species_summary.tsv"

echo "  Created symlinks in output_to_input/BLOCK_orthohmm/"

echo ""
echo "========================================================================"
echo "SUCCESS! OrthoHMM pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/ through 6-output/"
echo ""
echo "Downstream symlinks:"
echo "  output_to_input/BLOCK_orthohmm/  (subproject root)"
echo ""
echo "Next: Review results, then run BLOCK_comparison for cross-tool analysis"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
