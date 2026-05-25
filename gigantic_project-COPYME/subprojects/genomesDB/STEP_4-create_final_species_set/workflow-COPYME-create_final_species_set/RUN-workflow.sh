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
# Activate GIGANTIC Environment (on-demand creation)
# ============================================================================
# The environment is created automatically on first run from the yml spec
# in conda_environments/. You can also pre-create all environments at once:
#   cd ../../../../ && bash RUN-setup_environments.sh
# ============================================================================

# GIGANTIC env naming convention: aiG-<subproject>-<block_or_step>-<optional_details>
# Per-BLOCK conda env. Auto-created on first run from ai/conda_environment.yml.
# mamba is preferred (much faster); conda is the fallback if mamba is missing.
# This env is SHARED across all 4 genomesDB STEPs.

ENV_NAME="aiG-genomesDB"
ENV_YML="ai/conda_environment.yml"

module load conda 2>/dev/null || true

if ! command -v conda &> /dev/null; then
    echo "ERROR: conda not found!"
    echo "On HPC (HiPerGator): module load conda"
    exit 1
fi

env_is_complete() {
    local env_prefix=$(conda env list 2>/dev/null | awk -v n="${ENV_NAME}" '$1==n {print $NF}')
    if [ -z "${env_prefix}" ]; then return 1; fi
    if [ ! -x "${env_prefix}/bin/python" ]; then return 1; fi
    return 0
}

if ! env_is_complete; then
    if conda env list 2>/dev/null | awk '{print $1}' | grep -q "^${ENV_NAME}$"; then
        echo "Removing broken/incomplete env '${ENV_NAME}'..."
        conda env remove -n "${ENV_NAME}" -y 2>&1 | tail -3
    fi
    echo "Creating conda env '${ENV_NAME}' from ${ENV_YML}..."
    if [ ! -f "${ENV_YML}" ]; then
        echo "ERROR: Environment spec not found at: ${ENV_YML}"
        exit 1
    fi
    if command -v mamba &> /dev/null; then
        mamba env create -f "${ENV_YML}" -y
    else
        conda env create -f "${ENV_YML}" -y
    fi
    if ! env_is_complete; then
        echo "ERROR: Environment creation failed -- '${ENV_NAME}' still not complete."
        exit 1
    fi
    echo "Env '${ENV_NAME}' created successfully."
fi

if conda activate "${ENV_NAME}" 2>/dev/null; then
    echo "Activated conda environment: ${ENV_NAME}"
else
    echo "WARNING: Could not activate '${ENV_NAME}'. Continuing with current environment."
fi

if ! command -v nextflow &> /dev/null; then
    module load nextflow 2>/dev/null || true
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: NextFlow not available!"
        exit 1
    fi
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

# ============================================================================
# Flatten START_HERE-user_config.yaml -> .params.json for NextFlow -params-file
# ============================================================================
# Universal GIGANTIC YAML->params pattern: pass-through json.dump (no flatten).

python3 <<'PYTHON_DUMP'
import yaml, json
with open( 'START_HERE-user_config.yaml' ) as f:
    cfg = yaml.safe_load( f )
with open( '.params.json', 'w' ) as f:
    json.dump( cfg, f, indent=2 )
PYTHON_DUMP

nextflow run ai/main.nf ${RESUME_FLAG} \
    -params-file .params.json

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
