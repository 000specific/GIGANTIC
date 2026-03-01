#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 01 | Purpose: Run DIAMOND NCBI nr search pipeline locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC One-Direction Homologs Pipeline - Local Execution
################################################################################
#
# PURPOSE:
# Run the DIAMOND NCBI nr search workflow on your local machine using NextFlow.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Edit diamond_ncbi_nr_config.yaml with your DIAMOND database path
# 2. Create INPUT_user/proteome_manifest.tsv with your species and proteome paths
#    OR place a proteome_manifest.tsv in INPUT_gigantic/ at the project root
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN-workflow.sbatch
#
# WHAT THIS DOES:
# 1. Validates proteome files exist and are valid FASTA
# 2. Splits proteomes into N parts for parallel DIAMOND search
# 3. Runs DIAMOND blastp against NCBI nr database
# 4. Combines results per species
# 5. Identifies top self/non-self hits with NCBI headers and sequences
# 6. Compiles master statistics table
#
# OUTPUT:
# Results in OUTPUT_pipeline/ (numbered subdirectories per script)
# Summary: OUTPUT_pipeline/6-output/6_ai-all_species_statistics.tsv
#
################################################################################

echo "========================================================================"
echo "GIGANTIC One-Direction Homologs Pipeline (Local)"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# Path to project-level INPUT_gigantic (relative to this workflow)
INPUT_GIGANTIC="../../../INPUT_gigantic"

# Copy proteome manifest from INPUT_gigantic if it exists
if [ -f "${INPUT_GIGANTIC}/proteome_manifest.tsv" ]; then
    MANIFEST_LINES=$(grep -v "^#" "${INPUT_GIGANTIC}/proteome_manifest.tsv" | grep -v "^$" | wc -l)
    if [ "$MANIFEST_LINES" -gt 0 ]; then
        echo "Copying proteome manifest from INPUT_gigantic/ (project-wide source)..."
        cp "${INPUT_GIGANTIC}/proteome_manifest.tsv" "INPUT_user/proteome_manifest.tsv"
        echo "  Copied manifest with ${MANIFEST_LINES} entries to INPUT_user/ for archival"
        echo ""
    fi
fi

# ============================================================================
# Activate GIGANTIC Environment
# ============================================================================
# Load conda module (required on HPC systems like HiPerGator)
module load conda 2>/dev/null || true

# Activate the one_direction_homologs environment
# This environment is created by: bash RUN-setup_environments.sh (at project root)
if conda activate ai_gigantic_one_direction_homologs 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_one_direction_homologs"
else
    # Check if nextflow is already available in PATH
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: Environment 'ai_gigantic_one_direction_homologs' not found!"
        echo ""
        echo "Please run the environment setup script first:"
        echo ""
        echo "  cd ../../../  # Go to project root"
        echo "  bash RUN-setup_environments.sh"
        echo ""
        echo "Or create this environment manually:"
        echo "  mamba env create -f ../../../conda_environments/ai_gigantic_one_direction_homologs.yml"
        echo ""
        exit 1
    fi
    echo "Using NextFlow from PATH (environment not activated)"
fi
echo ""

# Check for proteome manifest
if [ ! -f "INPUT_user/proteome_manifest.tsv" ]; then
    echo "ERROR: Proteome manifest not found!"
    echo ""
    echo "Please create a manifest at one of these locations:"
    echo ""
    echo "  RECOMMENDED (project-wide):"
    echo "    INPUT_gigantic/proteome_manifest.tsv  (at project root)"
    echo ""
    echo "  OR workflow-specific:"
    echo "    INPUT_user/proteome_manifest.tsv  (in this workflow directory)"
    echo ""
    echo "See INPUT_user/proteome_manifest_example.tsv for format."
    echo ""
    exit 1
fi

# Check for DIAMOND database in config
CONFIG_FILE="diamond_ncbi_nr_config.yaml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Configuration file not found: ${CONFIG_FILE}"
    exit 1
fi

# Show manifest summary
SPECIES_COUNT=$(grep -v "^#" INPUT_user/proteome_manifest.tsv | grep -v "^$" | tail -n +2 | wc -l)
echo "Species in manifest: ${SPECIES_COUNT}"
echo ""

# Run NextFlow pipeline
echo "Running NextFlow pipeline..."
echo ""

nextflow run ai/main.nf

EXIT_CODE=$?

echo ""

if [ $EXIT_CODE -ne 0 ]; then
    echo "========================================================================"
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "Check the logs above for error details."
    echo "========================================================================"
    echo "Completed: $(date)"
    exit $EXIT_CODE
fi

# ============================================================================
# Create symlinks for output_to_input directories
# ============================================================================
# Real files live in OUTPUT_pipeline/N-output/ (created by NextFlow above).
# Symlinks are created in two locations:
#   1. subproject/output_to_input/  (canonical, for downstream subprojects)
#   2. ai/output_to_input/          (archival, with this workflow run)
#
# Symlink targets are RELATIVE paths from the symlink location to
# the real files in OUTPUT_pipeline/.
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

# --- Subproject-level output_to_input (canonical) ---
# Symlink location: ../output_to_input/ncbi_nr_top_hits/
# Real files:       OUTPUT_pipeline/5-output/ and OUTPUT_pipeline/6-output/
# Relative from symlink to real: ../../workflow-COPYME-diamond_ncbi_nr/OUTPUT_pipeline/...

SUBPROJECT_SHARED_DIR="../output_to_input/ncbi_nr_top_hits"
mkdir -p "${SUBPROJECT_SHARED_DIR}"

# Remove any stale symlinks from previous runs
find "${SUBPROJECT_SHARED_DIR}" -type l -delete 2>/dev/null

for file_path in OUTPUT_pipeline/5-output/*_top_hits.tsv OUTPUT_pipeline/5-output/*_statistics.tsv; do
    [ -f "${file_path}" ] || continue
    file_name="$(basename "${file_path}")"
    ln -sf "../../workflow-COPYME-diamond_ncbi_nr/${file_path}" "${SUBPROJECT_SHARED_DIR}/${file_name}"
done

ln -sf "../../workflow-COPYME-diamond_ncbi_nr/OUTPUT_pipeline/6-output/6_ai-all_species_statistics.tsv" \
    "${SUBPROJECT_SHARED_DIR}/all_species_statistics.tsv"

echo "  Subproject output_to_input/ncbi_nr_top_hits/ -> symlinks created"

# --- Workflow-level ai/output_to_input (archival) ---
# Symlink location: ai/output_to_input/ncbi_nr_top_hits/
# Real files:       OUTPUT_pipeline/5-output/ and OUTPUT_pipeline/6-output/
# Relative from symlink to real: ../../OUTPUT_pipeline/...

WORKFLOW_SHARED_DIR="ai/output_to_input/ncbi_nr_top_hits"
mkdir -p "${WORKFLOW_SHARED_DIR}"

# Remove any stale symlinks from previous runs
find "${WORKFLOW_SHARED_DIR}" -type l -delete 2>/dev/null

for file_path in OUTPUT_pipeline/5-output/*_top_hits.tsv OUTPUT_pipeline/5-output/*_statistics.tsv; do
    [ -f "${file_path}" ] || continue
    file_name="$(basename "${file_path}")"
    ln -sf "../../../OUTPUT_pipeline/5-output/${file_name}" "${WORKFLOW_SHARED_DIR}/${file_name}"
done

ln -sf "../../../OUTPUT_pipeline/6-output/6_ai-all_species_statistics.tsv" \
    "${WORKFLOW_SHARED_DIR}/all_species_statistics.tsv"

echo "  Workflow ai/output_to_input/ncbi_nr_top_hits/ -> symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! Pipeline completed."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/ through 6-output/"
echo ""
echo "Downstream symlinks:"
echo "  ../output_to_input/ncbi_nr_top_hits/  (for downstream subprojects)"
echo "  ai/output_to_input/ncbi_nr_top_hits/  (archival with this run)"
echo "========================================================================"
echo "Completed: $(date)"

exit 0
