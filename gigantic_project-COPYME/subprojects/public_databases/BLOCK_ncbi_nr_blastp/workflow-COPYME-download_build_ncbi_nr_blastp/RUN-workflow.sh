#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 09 | Purpose: Run NCBI nr BLAST protein database build Nextflow pipeline
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh
# =============================================================================
# Downloads the NCBI nr protein FASTA and builds a BLAST protein database
# using makeblastdb for downstream BLASTp homology searches.
#
# PURPOSE:
#   Download NCBI nr FASTA, decompress, build BLAST protein database,
#   validate, and create symlinks for downstream subprojects.
#
# USAGE:
#   bash RUN-workflow.sh
#
# FOR SLURM CLUSTERS:
#   sbatch RUN-workflow.sbatch
#
# BEFORE RUNNING:
#   1. Edit START_HERE-user_config.yaml
#   2. Ensure sufficient disk space (~300 GB)
#   3. Ensure sufficient memory (~100 GB for makeblastdb)
#
# WHAT THIS DOES:
#   1. Downloads NCBI nr.gz from NCBI FTP (~100 GB compressed)
#   2. Decompresses and builds BLAST protein database with makeblastdb
#   3. Validates database with blastdbcmd -info
#   4. Writes timestamped run log
#   5. Creates symlinks in output_to_input/BLOCK_ncbi_nr_blastp/
# =============================================================================

set -e

echo "========================================================================"
echo "Starting NCBI nr BLAST Protein Database Pipeline"
echo "========================================================================"

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Activate GIGANTIC Environment
# ============================================================================

module load conda 2>/dev/null || true

if conda activate ai_gigantic_public_databases 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_public_databases"
else
    echo "Environment 'ai_gigantic_public_databases' not found."
    echo "Attempting to create it..."
    echo ""

    if command -v mamba &> /dev/null; then
        echo "Creating environment with mamba..."
        mamba create -n ai_gigantic_public_databases -y \
            -c conda-forge -c bioconda \
            nextflow blast wget python
        conda activate ai_gigantic_public_databases
        echo "Created and activated conda environment: ai_gigantic_public_databases"
    elif command -v conda &> /dev/null; then
        echo "Creating environment with conda..."
        conda create -n ai_gigantic_public_databases -y \
            -c conda-forge -c bioconda \
            nextflow blast wget python
        conda activate ai_gigantic_public_databases
        echo "Created and activated conda environment: ai_gigantic_public_databases"
    else
        if ! command -v nextflow &> /dev/null; then
            echo "ERROR: Cannot create environment and nextflow is not available!"
            echo ""
            echo "Please create the environment manually:"
            echo "  mamba create -n ai_gigantic_public_databases -c conda-forge -c bioconda nextflow blast wget python -y"
            echo ""
            exit 1
        fi
        echo "Using NextFlow from PATH (environment not activated)"
    fi
fi
echo ""

# ============================================================================
# Check for Nextflow
# ============================================================================

if ! command -v nextflow &> /dev/null; then
    echo "ERROR: nextflow command not found!"
    echo "Please ensure nextflow is installed in your conda environment."
    exit 1
fi

# ============================================================================
# Run Nextflow Pipeline
# ============================================================================

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
    echo "========================================================================"
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "========================================================================"
    exit $EXIT_CODE
fi

# ============================================================================
# Create symlinks for output_to_input directory
# ============================================================================
# Real files live in OUTPUT_pipeline/N-output/ (created by NextFlow above).
# Symlinks are created in ONE location at the subproject root:
#   ../../output_to_input/BLOCK_ncbi_nr_blastp/
#
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

# --- Subproject-root output_to_input (single canonical location) ---
SUBPROJECT_SHARED_DIR="../../output_to_input/BLOCK_ncbi_nr_blastp"
mkdir -p "${SUBPROJECT_SHARED_DIR}"
find "${SUBPROJECT_SHARED_DIR}" -type l -delete 2>/dev/null || true

# --- Create relative symlinks for BLAST database files ---
# Real files: OUTPUT_pipeline/2-output/nr.*
RESULT_DIR="OUTPUT_pipeline/2-output"
SYMLINK_COUNT=0

for database_file in ${RESULT_DIR}/nr.p*; do
    if [ -f "$database_file" ]; then
        filename="$(basename "$database_file")"
        ln -sf "../../BLOCK_ncbi_nr_blastp/${WORKFLOW_DIR_NAME}/${database_file}" "${SUBPROJECT_SHARED_DIR}/${filename}"
        SYMLINK_COUNT=$((SYMLINK_COUNT + 1))
    fi
done

echo "  Created ${SYMLINK_COUNT} symlinks in output_to_input/BLOCK_ncbi_nr_blastp/"

if [ $SYMLINK_COUNT -eq 0 ]; then
    echo "  WARNING: No BLAST database files found in ${RESULT_DIR}/"
    echo "  The pipeline may have produced no outputs."
fi

echo ""
echo "========================================================================"
echo "SUCCESS! NCBI nr BLAST Protein Database Pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/"
echo ""
echo "Downstream symlinks:"
echo "  output_to_input/BLOCK_ncbi_nr_blastp/  (subproject root)"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
