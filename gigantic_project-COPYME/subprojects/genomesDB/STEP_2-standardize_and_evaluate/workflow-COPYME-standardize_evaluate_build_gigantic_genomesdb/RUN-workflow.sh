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
# 1. Edit standardize_evaluate_config.yaml with your project settings
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
# Species manifest copied to ../../output_to_input/
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
# Activate GIGANTIC Environment
# ============================================================================

# Load conda module (required on HPC systems like HiPerGator)
module load conda 2>/dev/null || true

# Activate the genomesdb environment
if conda activate ai_gigantic_genomesdb 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_genomesdb"
else
    # Check if nextflow is already available in PATH
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: Environment 'ai_gigantic_genomesdb' not found!"
        echo ""
        echo "Please run the environment setup script first:"
        echo ""
        echo "  cd ../../../  # Go to project root"
        echo "  bash RUN-setup_environments.sh"
        echo ""
        echo "Or create this environment manually:"
        echo "  mamba env create -f ../../../conda_environments/ai_gigantic_genomesdb.yml"
        echo ""
        exit 1
    fi
    echo "Using NextFlow from PATH (environment not activated)"
fi
echo ""

# ============================================================================
# Validate Prerequisites
# ============================================================================

echo "Validating prerequisites..."
echo ""

# Check config file exists
if [ ! -f "standardize_evaluate_config.yaml" ]; then
    echo "ERROR: Configuration file not found!"
    echo "Expected: standardize_evaluate_config.yaml"
    exit 1
fi
echo "  [OK] Configuration file found"

# Check BUSCO lineages manifest exists
if [ ! -f "INPUT_user/busco_lineages.txt" ]; then
    echo "WARNING: BUSCO lineage manifest not found"
    echo "Expected: INPUT_user/busco_lineages.txt"
    echo "BUSCO evaluation will be skipped."
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

# Remove any stale symlinks from previous runs
find "${STEP_SHARED_DIR}" -maxdepth 1 -type l -delete 2>/dev/null

ln -sf "../STEP_2-standardize_and_evaluate/workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/OUTPUT_pipeline/6-output/6_ai-species_selection_manifest.tsv" \
    "${STEP_SHARED_DIR}/species_selection_manifest.tsv"

echo "  STEP output_to_input/ -> symlinks created"

# --- Workflow-level ai/output_to_input (archival) ---
WORKFLOW_SHARED_DIR="ai/output_to_input"
mkdir -p "${WORKFLOW_SHARED_DIR}"

# Remove any stale symlinks from previous runs
find "${WORKFLOW_SHARED_DIR}" -type l -delete 2>/dev/null

ln -sf "../../OUTPUT_pipeline/6-output/6_ai-species_selection_manifest.tsv" \
    "${WORKFLOW_SHARED_DIR}/species_selection_manifest.tsv"

echo "  Workflow ai/output_to_input/ -> symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! STEP_2 pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/ through 6-output/"
echo ""
echo "Downstream symlinks:"
echo "  ../../output_to_input/  (for downstream subprojects)"
echo "  ai/output_to_input/     (archival with this run)"
echo ""
echo "Next: Run STEP_4 to create final species set in output_to_input/"
echo "========================================================================"
echo "Completed: $(date)"
