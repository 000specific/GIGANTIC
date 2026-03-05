#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Run annotations OCL analysis workflow locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC annotations_X_ocl - Origin-Conservation-Loss Analysis (Local)
################################################################################
#
# PURPOSE:
# Run the OCL pipeline to create annotation groups (annogroups), determine
# their phylogenetic origins, quantify conservation and loss patterns, and
# validate results across phylogenetic tree structures.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Edit START_HERE-user_config.yaml to set:
#    - run_label (e.g., "Species71_pfam")
#    - annotation_database (pfam, gene3d, deeploc, etc.)
#    - annogroup_subtypes (single, combo, zero)
#    - Input paths to upstream subprojects
# 2. Edit INPUT_user/structure_manifest.tsv with structure IDs to analyze
# 3. Verify upstream subprojects have completed (trees_species, annotations_hmms)
#
# COPYME PATTERN:
# This is a workflow-COPYME template. Each database exploration gets its own copy:
#   cp -r workflow-COPYME-ocl_analysis workflow-RUN_01-ocl_analysis
#   cd workflow-RUN_01-ocl_analysis
#   # Edit START_HERE-user_config.yaml for this specific database
#   bash RUN-workflow.sh
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN-workflow.sbatch
#
# WHAT THIS DOES:
# 1. Runs 5 scripts per structure (parallel across structures):
#    001: Create annotation groups (annogroups) from annotation files
#    002: Determine annogroup origins (MRCA algorithm)
#    003: Quantify conservation and loss (TEMPLATE_03 dual-metric)
#    004: Generate comprehensive OCL summaries (per-subtype + all-subtypes)
#    005: Validate results (strict fail-fast)
# 2. Creates output_to_input symlinks for downstream subprojects
#
# OUTPUT:
# Results in OUTPUT_pipeline/structure_NNN/1-output/ through 5-output/
# Downstream symlinks in ../../output_to_input/BLOCK_ocl_analysis/{run_label}/
#
################################################################################

echo "========================================================================"
echo "GIGANTIC Annotations OCL Pipeline (Local)"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Read Configuration
# ============================================================================

if [ ! -f "START_HERE-user_config.yaml" ]; then
    echo "ERROR: Configuration file not found!"
    echo "Expected: START_HERE-user_config.yaml"
    exit 1
fi

# Extract configuration values
RUN_LABEL=$(python3 -c "import yaml; print(yaml.safe_load(open('START_HERE-user_config.yaml'))['run_label'])")
ANNOTATION_DATABASE=$(python3 -c "import yaml; print(yaml.safe_load(open('START_HERE-user_config.yaml'))['annotation_database'])")
SPECIES_SET=$(python3 -c "import yaml; print(yaml.safe_load(open('START_HERE-user_config.yaml'))['species_set_name'])")

echo "Configuration:"
echo "  Run Label           : ${RUN_LABEL}"
echo "  Species Set         : ${SPECIES_SET}"
echo "  Annotation Database : ${ANNOTATION_DATABASE}"
echo ""

# ============================================================================
# Activate GIGANTIC Environment
# ============================================================================

# Load conda module (required on HPC systems like HiPerGator)
module load conda 2>/dev/null || true

# Activate the OCL environment
if conda activate ai_gigantic_annotations_X_ocl 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_annotations_X_ocl"
else
    # Check if nextflow is already available in PATH
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: Environment 'ai_gigantic_annotations_X_ocl' not found!"
        echo ""
        echo "Please run the environment setup script first:"
        echo ""
        echo "  cd ../../../../  # Go to project root"
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

# Check INPUT_user directory exists
if [ ! -d "INPUT_user" ]; then
    echo "ERROR: INPUT_user/ directory not found!"
    echo "  Create it and add structure_manifest.tsv."
    exit 1
fi
echo "  [OK] INPUT_user/ directory found"

# Check structure manifest exists
MANIFEST=$(python3 -c "import yaml; print(yaml.safe_load(open('START_HERE-user_config.yaml'))['inputs']['structure_manifest'])")
if [ ! -f "${MANIFEST}" ]; then
    echo "ERROR: Structure manifest not found: ${MANIFEST}"
    echo "  Create the manifest with structure IDs to analyze."
    exit 1
fi
echo "  [OK] Structure manifest found: ${MANIFEST}"

# Count structures to process
STRUCTURE_COUNT=$(tail -n +2 "${MANIFEST}" | grep -v '^$' | wc -l)
echo "  [OK] Structures to process: ${STRUCTURE_COUNT}"

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
# Real files live in OUTPUT_pipeline/structure_NNN/4-output/ (created by pipeline).
# Symlinks go to ../../output_to_input/BLOCK_ocl_analysis/{run_label}/
# Each structure gets a symlink: structure_NNN -> real 4-output summary file.
#
# The run_label provides namespacing so different database explorations coexist:
#   output_to_input/BLOCK_ocl_analysis/Species71_pfam/structure_001/
#   output_to_input/BLOCK_ocl_analysis/Species71_gene3d/structure_001/
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

SHARED_DIR="../../output_to_input/BLOCK_ocl_analysis/${RUN_LABEL}"
mkdir -p "${SHARED_DIR}"

# Remove any stale symlinks from previous runs
for old_link in "${SHARED_DIR}"/structure_*; do
    if [ -L "$old_link" ]; then
        rm "$old_link"
    fi
done

# Create symlinks for each structure directory
for structure_dir in OUTPUT_pipeline/structure_*; do
    if [ -d "$structure_dir" ]; then
        structure_name=$(basename "$structure_dir")
        summary_file="${structure_dir}/4-output/4_ai-annogroups-complete_ocl_summary-all_types.tsv"

        if [ -f "$summary_file" ]; then
            # Create structure subdirectory in shared location
            mkdir -p "${SHARED_DIR}/${structure_name}"
            # Symlink the complete OCL summary (primary downstream file)
            # Use workflow-relative path for portability
            ln -sf "../../../BLOCK_ocl_analysis/workflow-COPYME-ocl_analysis/OUTPUT_pipeline/${structure_name}/4-output/4_ai-annogroups-complete_ocl_summary-all_types.tsv" \
                "${SHARED_DIR}/${structure_name}/4_ai-annogroups-complete_ocl_summary-all_types.tsv"
        fi
    fi
done

SYMLINK_COUNT=$(find "${SHARED_DIR}" -name "*.tsv" -type l 2>/dev/null | wc -l)
echo "  output_to_input/BLOCK_ocl_analysis/${RUN_LABEL}/ -> ${SYMLINK_COUNT} symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! Annotations OCL pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/structure_NNN/1-output/  Annogroups + annogroup map"
echo "  OUTPUT_pipeline/structure_NNN/2-output/  Annogroup origins"
echo "  OUTPUT_pipeline/structure_NNN/3-output/  Conservation/loss patterns"
echo "  OUTPUT_pipeline/structure_NNN/4-output/  Comprehensive OCL summaries"
echo "  OUTPUT_pipeline/structure_NNN/5-output/  Validation reports"
echo ""
echo "Downstream symlinks:"
echo "  ../../output_to_input/BLOCK_ocl_analysis/${RUN_LABEL}/"
echo ""
echo "Run Label: ${RUN_LABEL}"
echo "Annotation Database: ${ANNOTATION_DATABASE}"
echo "Structures processed: ${STRUCTURE_COUNT}"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
