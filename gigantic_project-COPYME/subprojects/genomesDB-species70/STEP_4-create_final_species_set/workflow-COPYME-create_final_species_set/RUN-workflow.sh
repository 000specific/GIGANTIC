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
# 5. Edit START_HERE-user_config.yaml with paths to STEP_2 and STEP_3 outputs
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN-workflow.sbatch
#
# WHAT THIS DOES:
# 1. Validates species selection against STEP_2 and STEP_3 outputs
# 2. Scans for available genome annotations (GFF/GTF) from STEP_2
# 3. Copies selected proteomes from STEP_2 with speciesN naming
# 4. Copies selected BLAST databases from STEP_3 with speciesN naming
# 5. Copies genome annotations for species that have them
# 6. Creates ../../output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/
# 7. Creates ../../output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_blastp/
# 8. Creates ../../output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_genome_annotations/
#
# OUTPUT:
# Results in OUTPUT_pipeline/1-output and 2-output/
# Final species set copied to ../../output_to_input/STEP_4-create_final_species_set/
# NOTE: Genome annotations are optional - not all species have GFF/GTF files.
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
    # Check if required tools are available in PATH
    MISSING_TOOLS=""
    if ! command -v nextflow &> /dev/null; then
        MISSING_TOOLS="${MISSING_TOOLS} nextflow"
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
#   ../../output_to_input/STEP_4-create_final_species_set/
#
# STEP_4 creates per-species directories (species*_gigantic_T1_proteomes,
# species*_gigantic_T1_blastp, species*_gigantic_genome_annotations) which
# are discovered dynamically.
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

# Determine the workflow directory name dynamically (supports COPYME and RUN_XX instances)
WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

# --- Subproject-root output_to_input (single canonical location) ---
SUBPROJECT_SHARED_DIR="../../output_to_input/STEP_4-create_final_species_set"
mkdir -p "${SUBPROJECT_SHARED_DIR}"

# Remove any stale species directory symlinks from previous runs
for old_link in "${SUBPROJECT_SHARED_DIR}"/species*_gigantic_T1_* "${SUBPROJECT_SHARED_DIR}"/species*_gigantic_genome_annotations; do
    if [ -L "$old_link" ]; then
        rm "$old_link"
    fi
done

# Create symlinks for each species directory in 2-output/
# This catches T1_proteomes, T1_blastp, and genome_annotations
for species_dir in OUTPUT_pipeline/2-output/species*_gigantic_*; do
    if [ -d "$species_dir" ] || [ -L "$species_dir" ]; then
        dir_name=$(basename "$species_dir")
        ln -sf "../../STEP_4-create_final_species_set/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/2-output/${dir_name}" \
            "${SUBPROJECT_SHARED_DIR}/${dir_name}"
    fi
done

echo "  output_to_input/STEP_4-create_final_species_set/ -> symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! STEP_4 pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/  Validated species list, count, and annotation availability"
echo "  OUTPUT_pipeline/2-output/  Final species set directories"
echo ""
echo "Downstream symlinks:"
echo "  ../../output_to_input/STEP_4-create_final_species_set/  (for downstream subprojects)"
echo ""
echo "Published directories:"
echo "  speciesN_gigantic_T1_proteomes/       Proteome files"
echo "  speciesN_gigantic_T1_blastp/          BLAST databases"
echo "  speciesN_gigantic_genome_annotations/   GFF/GTF files (subset with annotations)"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
