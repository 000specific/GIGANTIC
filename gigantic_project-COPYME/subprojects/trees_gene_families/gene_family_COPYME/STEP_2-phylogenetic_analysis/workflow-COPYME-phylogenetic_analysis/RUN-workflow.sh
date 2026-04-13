#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 10 | Purpose: Run STEP_2 phylogenetic analysis Nextflow pipeline
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh
# =============================================================================
# Runs the STEP_2 phylogenetic analysis Nextflow pipeline.
# Supports both local and SLURM execution via START_HERE-user_config.yaml.
#
# Usage:
#   bash RUN-workflow.sh
#
# Set execution_mode in START_HERE-user_config.yaml:
#   "local" - runs directly on this machine
#   "slurm" - submits as a SLURM job with resources from config
# =============================================================================

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Activate Environment
# ============================================================================

module load conda 2>/dev/null || true

if conda activate ai_gigantic_trees_gene_families 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_trees_gene_families"
else
    echo "WARNING: Environment 'ai_gigantic_trees_gene_families' not found."
    echo ""
    echo "Please run the environment setup script first:"
    echo "  cd ../../../../  # Go to project root"
    echo "  bash RUN-setup_environments.sh"
    echo ""
    echo "Or create this environment manually:"
    echo "  mamba env create -f ../../../../conda_environments/ai_gigantic_trees_gene_families.yml"
    echo ""
    exit 1
fi

# Ensure NextFlow is available (conda env or system module)
if ! command -v nextflow &> /dev/null; then
    echo "NextFlow not found in conda env. Trying system module..."
    module load nextflow 2>/dev/null || true
    if ! command -v nextflow &> /dev/null; then
        echo ""
        echo "ERROR: NextFlow not available!"
        echo ""
        echo "Options to resolve:"
        echo "  1. Install nextflow in conda env: conda install -n ai_gigantic_trees_gene_families -c bioconda nextflow"
        echo "  2. Load system module: module load nextflow"
        echo "  3. Install globally: https://www.nextflow.io/docs/latest/install.html"
        exit 1
    fi
    echo "Using NextFlow from system module"
else
    echo "NextFlow available"
fi
echo ""

# ============================================================================
# Read execution mode from START_HERE-user_config.yaml
# ============================================================================
# Uses grep to parse flat YAML keys (no Python dependency required).

read_config() {
    # Read a flat YAML key from START_HERE-user_config.yaml (no Python dependency)
    local value=$(grep "^${1}:" START_HERE-user_config.yaml 2>/dev/null | head -1 | sed 's/^[^:]*: *//' | sed 's/^"//;s/"$//')
    echo "${value:-$2}"
}

EXECUTION_MODE=$(read_config "execution_mode" "local")

# ============================================================================
# SLURM submission (if execution_mode is "slurm" and not already inside a job)
# ============================================================================

if [ "${EXECUTION_MODE}" == "slurm" ] && [ -z "${SLURM_JOB_ID}" ]; then
    echo "Execution mode: SLURM (submitting job)"
    echo ""

    # Read SLURM settings from config
    # The workflow SLURM job needs enough resources for the largest tool process
    # and enough time for all processes combined (slurm_time_hours = total + 10%)
    SLURM_CPUS=$(read_config "slurm_cpus" "50")
    SLURM_MEM=$(read_config "slurm_memory_gb" "350")
    SLURM_TIME=$(read_config "slurm_time_hours" "198")
    SLURM_ACCOUNT=$(read_config "slurm_account" "")
    SLURM_QOS=$(read_config "slurm_qos" "")

    mkdir -p slurm_logs

    SBATCH_ARGS="--job-name=phylogenetic_analysis"
    SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${SLURM_CPUS}"
    SBATCH_ARGS="${SBATCH_ARGS} --mem=${SLURM_MEM}gb"
    SBATCH_ARGS="${SBATCH_ARGS} --time=${SLURM_TIME}:00:00"
    SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/phylogenetic_analysis-%j.log"

    if [ -n "${SLURM_ACCOUNT}" ]; then
        SBATCH_ARGS="${SBATCH_ARGS} --account=${SLURM_ACCOUNT}"
    fi
    if [ -n "${SLURM_QOS}" ]; then
        SBATCH_ARGS="${SBATCH_ARGS} --qos=${SLURM_QOS}"
    fi

    echo "Submitting with: sbatch ${SBATCH_ARGS}"
    sbatch ${SBATCH_ARGS} --wrap="bash $(realpath $0)"

    echo ""
    echo "Job submitted. Check slurm_logs/ for output."
    conda deactivate 2>/dev/null || true
    exit 0
fi

# ============================================================================
# Run Nextflow pipeline (local execution or inside SLURM job)
# ============================================================================

if [ -n "${SLURM_JOB_ID}" ]; then
    echo "Running inside SLURM job ${SLURM_JOB_ID}"
else
    echo "Execution mode: local"
fi

# Validate prerequisites
echo "Validating prerequisites..."
echo ""

if [ ! -f "START_HERE-user_config.yaml" ]; then
    echo "ERROR: Configuration file not found!"
    echo "Expected: START_HERE-user_config.yaml"
    exit 1
fi
echo "  [OK] Configuration file found"
echo ""

echo "========================================================================"
echo "Starting STEP_2 Phylogenetic Analysis Pipeline"
echo "========================================================================"

# Optionally resume from cached work/ if user enabled it in config
RESUME=$(read_config "resume" "false")
RESUME_FLAG=""
if [ "${RESUME}" == "true" ]; then
    RESUME_FLAG="-resume"
    echo "  resume: enabled (using NextFlow work/ cache)"
fi

nextflow run ai/main.nf ${RESUME_FLAG} \
    -c ai/nextflow.config

EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "========================================================================"
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "========================================================================"
    exit $EXIT_CODE
fi

# ============================================================================
# Create symlinks for output_to_input (subproject root)
# ============================================================================
# Real files live in OUTPUT_pipeline/N-output/ (created by NextFlow above).
# Symlinks are organized by gene family at the subproject-root output_to_input/:
#   ../../../output_to_input/<gene_family>/STEP_2-phylogenetic_analysis/
#
# Structure:
#   output_to_input/
#   ├── nitric_oxide_synthases/
#   │   ├── STEP_1-homolog_discovery/      <- created by STEP_1
#   │   └── STEP_2-phylogenetic_analysis/  <- created here
#   └── innexin_pannexin/
#       ├── STEP_1-homolog_discovery/
#       └── STEP_2-phylogenetic_analysis/
#
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
# ============================================================================

echo ""
echo "Creating symlinks for downstream workflows..."

# Extract gene family name from config
GENE_FAMILY=$(grep -A5 "^gene_family:" START_HERE-user_config.yaml | grep "name:" | head -1 | sed 's/.*: *"\([^"]*\)".*/\1/')
WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"
GENE_FAMILY_DIR="$(basename "$(dirname "$(dirname "${SCRIPT_DIR}")")")"

# --- Subproject-root output_to_input ---
SYMLINK_DIR="../../../output_to_input/${GENE_FAMILY}/STEP_2-phylogenetic_analysis"
mkdir -p "${SYMLINK_DIR}"
find "${SYMLINK_DIR}" -type l -delete 2>/dev/null

# Symlink alignment files
for mafft_file in OUTPUT_pipeline/3-output/*.mafft; do
    if [ -f "$mafft_file" ]; then
        filename=$(basename "$mafft_file")
        ln -sf "../../../${GENE_FAMILY_DIR}/STEP_2-phylogenetic_analysis/${WORKFLOW_DIR_NAME}/${mafft_file}" \
            "${SYMLINK_DIR}/${filename}"
    fi
done

# Symlink trimmed alignment files
for trimmed_file in OUTPUT_pipeline/4-output/*.clipkit-smartgap; do
    if [ -f "$trimmed_file" ]; then
        filename=$(basename "$trimmed_file")
        ln -sf "../../../${GENE_FAMILY_DIR}/STEP_2-phylogenetic_analysis/${WORKFLOW_DIR_NAME}/${trimmed_file}" \
            "${SYMLINK_DIR}/${filename}"
    fi
done

# Symlink tree files (from 5_a-output, 5_b-output, 5_c-output, 5_d-output)
for tree_dir in OUTPUT_pipeline/5_a-output OUTPUT_pipeline/5_b-output OUTPUT_pipeline/5_c-output OUTPUT_pipeline/5_d-output; do
    if [ -d "$tree_dir" ]; then
        for tree_file in "$tree_dir"/*.fasttree "$tree_dir"/*.treefile "$tree_dir"/*.veryfasttree "$tree_dir"/*.phylobayes.nwk; do
            if [ -f "$tree_file" ]; then
                filename=$(basename "$tree_file")
                ln -sf "../../../${GENE_FAMILY_DIR}/STEP_2-phylogenetic_analysis/${WORKFLOW_DIR_NAME}/${tree_file}" \
                    "${SYMLINK_DIR}/${filename}"
            fi
        done
    fi
done

echo "  output_to_input/${GENE_FAMILY}/STEP_2-phylogenetic_analysis/ -> symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! STEP_2 pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/ through 7-output/"
echo ""
echo "Downstream symlinks:"
echo "  ../../../output_to_input/${GENE_FAMILY}/STEP_2-phylogenetic_analysis/"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
