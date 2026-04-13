#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 30 | Purpose: Run STEP_0 HGNC gene group RGS generation Nextflow pipeline
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh
# =============================================================================
# Runs the STEP_0 HGNC Gene Group RGS Generation Nextflow pipeline.
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
    echo "  cd ../../../../../  # Go to project root"
    echo "  bash RUN-setup_environments.sh"
    echo ""
    echo "Or create this environment manually:"
    echo "  mamba env create -f ../../../../../conda_environments/ai_gigantic_trees_gene_families.yml"
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

    # Read resources and SLURM settings from config
    SLURM_CPUS=$(read_config "cpus" "4")
    SLURM_MEM=$(read_config "memory_gb" "16")
    SLURM_TIME=$(read_config "time_hours" "1")
    SLURM_ACCOUNT=$(read_config "slurm_account" "")
    SLURM_QOS=$(read_config "slurm_qos" "")

    mkdir -p slurm_logs

    SBATCH_ARGS="--job-name=hgnc_gene_groups"
    SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${SLURM_CPUS}"
    SBATCH_ARGS="${SBATCH_ARGS} --mem=${SLURM_MEM}gb"
    SBATCH_ARGS="${SBATCH_ARGS} --time=${SLURM_TIME}:00:00"
    SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/hgnc_gene_groups-%j.log"

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
echo "Starting STEP_0 HGNC Gene Group RGS Generation Pipeline"
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
# Real files live in OUTPUT_pipeline/3-output/ (created by NextFlow above).
# Symlinks are organized at the subproject-root output_to_input/:
#   ../../output_to_input/STEP_0-hgnc_gene_groups/
#
# Structure:
#   output_to_input/
#   └── STEP_0-hgnc_gene_groups/
#       ├── rgs_fastas/
#       │   ├── gap_junction_proteins/ -> symlink
#       │   ├── potassium_channels/    -> symlink
#       │   └── [all other groups...]  -> symlinks
#       ├── 3_ai-rgs_generation_summary.tsv   -> symlink
#       └── 3_ai-rgs_generation_manifest.tsv  -> symlink
#
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
# ============================================================================

echo ""
echo "Creating symlinks for downstream workflows..."

WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

# --- Subproject-root output_to_input ---
# From workflow dir: 3 levels up to trees_gene_groups, then into output_to_input
SYMLINK_DIR="../../../output_to_input/gene_groups-hugo_hgnc/STEP_0-hgnc_gene_groups"
mkdir -p "${SYMLINK_DIR}/rgs_fastas"

# Clean old symlinks
find "${SYMLINK_DIR}/rgs_fastas" -type l -delete 2>/dev/null
find "${SYMLINK_DIR}" -maxdepth 1 -type l -delete 2>/dev/null

# Symlink each RGS FASTA file (flat - no subdirectories)
# Symlink location: trees_gene_groups/output_to_input/gene_groups-hugo_hgnc/STEP_0-hgnc_gene_groups/rgs_fastas/
# Target location:  trees_gene_groups/gene_groups-hugo_hgnc/STEP_0-hgnc_gene_groups/<workflow>/OUTPUT_pipeline/3-output/rgs_fastas/
if [ -d "OUTPUT_pipeline/3-output/rgs_fastas" ]; then
    for rgs_file in OUTPUT_pipeline/3-output/rgs_fastas/*.aa; do
        [ -f "$rgs_file" ] || continue
        FILENAME=$(basename "$rgs_file")

        ln -sf "../../../../gene_groups-hugo_hgnc/STEP_0-hgnc_gene_groups/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/3-output/rgs_fastas/${FILENAME}" \
            "${SYMLINK_DIR}/rgs_fastas/${FILENAME}"
    done

    RGS_COUNT=$(ls OUTPUT_pipeline/3-output/rgs_fastas/*.aa 2>/dev/null | wc -l)
    echo "  RGS FASTA symlinks created: ${RGS_COUNT} gene groups"
fi

# Symlink the summary and manifest TSVs
# Symlink location: trees_gene_groups/output_to_input/gene_groups-hugo_hgnc/STEP_0-hgnc_gene_groups/
# Target location:  trees_gene_groups/gene_groups-hugo_hgnc/STEP_0-hgnc_gene_groups/<workflow>/OUTPUT_pipeline/3-output/
for tsv_file in OUTPUT_pipeline/3-output/3_ai-rgs_generation_summary.tsv \
                OUTPUT_pipeline/3-output/3_ai-rgs_generation_manifest.tsv; do
    if [ -f "$tsv_file" ]; then
        FILENAME=$(basename "$tsv_file")
        ln -sf "../../../gene_groups-hugo_hgnc/STEP_0-hgnc_gene_groups/${WORKFLOW_DIR_NAME}/${tsv_file}" \
            "${SYMLINK_DIR}/${FILENAME}"
        echo "  ${FILENAME} symlink created"
    fi
done

echo ""
echo "========================================================================"
echo "SUCCESS! STEP_0 pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/  (downloaded HGNC data)"
echo "  OUTPUT_pipeline/2-output/  (aggregated gene sets)"
echo "  OUTPUT_pipeline/3-output/  (RGS FASTA files + manifest/summary)"
echo ""
echo "Downstream symlinks:"
echo "  ../../../output_to_input/gene_groups-hugo_hgnc/STEP_0-hgnc_gene_groups/rgs_fastas/"
echo "  ../../../output_to_input/gene_groups-hugo_hgnc/STEP_0-hgnc_gene_groups/3_ai-rgs_generation_summary.tsv"
echo "  ../../../output_to_input/gene_groups-hugo_hgnc/STEP_0-hgnc_gene_groups/3_ai-rgs_generation_manifest.tsv"
echo ""
echo "Next: Use individual RGS files in STEP_1 (validation) or STEP_2 (homolog discovery)"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
