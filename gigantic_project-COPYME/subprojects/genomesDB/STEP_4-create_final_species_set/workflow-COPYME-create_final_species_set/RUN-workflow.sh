#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: Run STEP_4 final species set workflow locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC genomesDB STEP_4 - Create Final Species Set (Local)
################################################################################
#
# PURPOSE:
# Create the final species set for downstream subprojects by copying
# user-selected species from STEP_2 and STEP_3 to output_to_input/.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Complete STEP_2 (standardize and evaluate all species)
# 2. Complete STEP_3 (create BLAST databases for all species)
# 3. Review STEP_2 quality metrics and decide which species to keep
# 4. Edit INPUT_user/selected_species.txt (or use all species by default)
# 5. Edit final_species_set_config.yaml with paths to STEP_2 and STEP_3 outputs
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN-workflow.sbatch
#
# WHAT THIS DOES:
# 1. Validates species selection against STEP_2 and STEP_3 outputs
# 2. Copies selected proteomes from STEP_2 with speciesN naming
# 3. Copies selected BLAST databases from STEP_3 with speciesN naming
# 4. Creates output_to_input/speciesN_gigantic_T1_proteomes/
# 5. Creates output_to_input/speciesN_gigantic_T1_blastp/
#
# OUTPUT:
# Results in OUTPUT_pipeline/1-output and 2-output/
# Final species set copied to ../../output_to_input/
#
################################################################################

echo "========================================================================"
echo "GIGANTIC genomesDB STEP_4 Pipeline (Local)"
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
if [ ! -f "final_species_set_config.yaml" ]; then
    echo "ERROR: Configuration file not found!"
    echo "Expected: final_species_set_config.yaml"
    exit 1
fi
echo "  [OK] Configuration file found"

# Check if selected_species.txt exists - if not, create default from STEP_2
if [ ! -f "INPUT_user/selected_species.txt" ]; then
    echo "  [INFO] No selected_species.txt found - will use all species from STEP_2"
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
# STEP_4 creates per-species directories (species*_gigantic_T1_proteomes,
# species*_gigantic_T1_blastp) which are discovered dynamically.
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

# --- STEP-level output_to_input (canonical) ---
STEP_SHARED_DIR="../../output_to_input"
mkdir -p "${STEP_SHARED_DIR}"

# Remove any stale species directory symlinks from previous runs
for old_link in "${STEP_SHARED_DIR}"/species*_gigantic_T1_*; do
    if [ -L "$old_link" ]; then
        rm "$old_link"
    fi
done

# Create symlinks for each species directory in 2-output/
for species_dir in OUTPUT_pipeline/2-output/species*_gigantic_T1_*; do
    if [ -d "$species_dir" ] || [ -L "$species_dir" ]; then
        dir_name=$(basename "$species_dir")
        ln -sf "../STEP_4-create_final_species_set/workflow-COPYME-create_final_species_set/OUTPUT_pipeline/2-output/${dir_name}" \
            "${STEP_SHARED_DIR}/${dir_name}"
    fi
done

echo "  STEP output_to_input/ -> symlinks created"

# --- Workflow-level ai/output_to_input (archival) ---
WORKFLOW_SHARED_DIR="ai/output_to_input"
mkdir -p "${WORKFLOW_SHARED_DIR}"

# Remove any stale symlinks from previous runs
find "${WORKFLOW_SHARED_DIR}" -type l -delete 2>/dev/null

# Create symlinks for each species directory
for species_dir in OUTPUT_pipeline/2-output/species*_gigantic_T1_*; do
    if [ -d "$species_dir" ] || [ -L "$species_dir" ]; then
        dir_name=$(basename "$species_dir")
        ln -sf "../../OUTPUT_pipeline/2-output/${dir_name}" \
            "${WORKFLOW_SHARED_DIR}/${dir_name}"
    fi
done

echo "  Workflow ai/output_to_input/ -> symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! STEP_4 pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/  Validated species list"
echo "  OUTPUT_pipeline/2-output/  Final species set directories"
echo ""
echo "Downstream symlinks:"
echo "  ../../output_to_input/  (for downstream subprojects)"
echo "  ai/output_to_input/     (archival with this run)"
echo "========================================================================"
echo "Completed: $(date)"
