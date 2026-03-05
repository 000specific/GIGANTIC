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
# 1. Edit START_HERE-user_config.yaml with your project settings
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
# Species manifest copied to ../../output_to_input/STEP_2-standardize_and_evaluate/
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
    # Check if required tools are available in PATH
    MISSING_TOOLS=""
    if ! command -v nextflow &> /dev/null; then
        MISSING_TOOLS="${MISSING_TOOLS} nextflow"
    fi
    if ! command -v gfastats &> /dev/null; then
        MISSING_TOOLS="${MISSING_TOOLS} gfastats"
    fi
    if ! command -v busco &> /dev/null; then
        MISSING_TOOLS="${MISSING_TOOLS} busco"
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

# Check BUSCO configuration
# Read busco.enabled from config (defaults to true if not found)
BUSCO_ENABLED=$(grep -A1 "^busco:" START_HERE-user_config.yaml | grep "enabled:" | awk '{print $2}' | tr -d '[:space:]')
if [ -z "${BUSCO_ENABLED}" ]; then
    BUSCO_ENABLED="true"
fi

if [ "${BUSCO_ENABLED}" = "true" ]; then
    if [ ! -f "INPUT_user/busco_lineages.txt" ]; then
        echo "ERROR: BUSCO is enabled but lineage manifest not found!"
        echo "Expected: INPUT_user/busco_lineages.txt"
        echo ""
        echo "Either:"
        echo "  1. Create INPUT_user/busco_lineages.txt with BUSCO lineage assignments"
        echo "  2. Set busco.enabled: false in START_HERE-user_config.yaml to skip BUSCO"
        exit 1
    fi
    echo "  [OK] BUSCO lineage manifest found"
else
    echo "  [INFO] BUSCO evaluation disabled in config (busco.enabled: false)"
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
# Copy species manifest to output_to_input directory
# ============================================================================
# The species selection manifest is COPIED (not symlinked) to output_to_input/
# because users need to edit this file directly to select species for STEP_4.
# A real file is easier to edit than a symlink.
# ============================================================================

echo ""
echo "Publishing outputs to output_to_input/..."

# Determine the workflow directory name dynamically (supports COPYME and RUN_XX instances)
WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

# --- Subproject-root output_to_input (single canonical location) ---
SUBPROJECT_SHARED_DIR="../../output_to_input/STEP_2-standardize_and_evaluate"
mkdir -p "${SUBPROJECT_SHARED_DIR}"

# Remove any stale files/symlinks from previous runs
rm -f "${SUBPROJECT_SHARED_DIR}/species_selection_manifest.tsv"
rm -f "${SUBPROJECT_SHARED_DIR}/gigantic_proteomes_cleaned"
rm -f "${SUBPROJECT_SHARED_DIR}/gigantic_genome_annotations"
rm -f "${SUBPROJECT_SHARED_DIR}/gigantic_genomes"

# Copy manifest (real file, not symlink - users edit this directly)
cp "OUTPUT_pipeline/6-output/6_ai-species_selection_manifest.tsv" \
    "${SUBPROJECT_SHARED_DIR}/species_selection_manifest.tsv"
echo "  species_selection_manifest.tsv -> copied"

# Symlink cleaned proteomes for STEP_3 and STEP_4 access
ln -sf "../../STEP_2-standardize_and_evaluate/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/2-output/gigantic_proteomes_cleaned" \
    "${SUBPROJECT_SHARED_DIR}/gigantic_proteomes_cleaned"
echo "  gigantic_proteomes_cleaned -> symlinked"

# Symlink genome annotations for STEP_4 access
ln -sf "../../STEP_2-standardize_and_evaluate/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/3-output/gigantic_genome_annotations" \
    "${SUBPROJECT_SHARED_DIR}/gigantic_genome_annotations"
echo "  gigantic_genome_annotations -> symlinked"

# Symlink genomes for STEP_4 access
ln -sf "../../STEP_2-standardize_and_evaluate/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/3-output/gigantic_genomes" \
    "${SUBPROJECT_SHARED_DIR}/gigantic_genomes"
echo "  gigantic_genomes -> symlinked"

echo ""
echo "========================================================================"
echo "SUCCESS! STEP_2 pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/ through 6-output/"
echo ""
echo "Species manifest (edit this to select species for STEP_4):"
echo "  ../../output_to_input/STEP_2-standardize_and_evaluate/species_selection_manifest.tsv"
echo ""
echo "Next: Review quality summary, edit species manifest, then run STEP_4"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
