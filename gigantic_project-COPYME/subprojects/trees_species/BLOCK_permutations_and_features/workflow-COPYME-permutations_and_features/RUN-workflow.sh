#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Run permutations and features workflow locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_species - Permutations and Features (Local)
################################################################################
#
# PURPOSE:
# Generate species tree topology permutations and extract phylogenetic features
# (paths, blocks, parent-child relationships, clade-species mappings) for
# downstream origin-conservation-loss (OCL) analyses.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Place your species tree (Newick format) in INPUT_user/species_tree.newick
# 2. Edit START_HERE-user_config.yaml:
#    - Set species_set_name (e.g., "species71")
#    - List unresolved_clades for permutation (or leave empty for single tree)
# 3. Optionally provide clade_names.tsv in INPUT_user/
#
# FOR SLURM CLUSTERS:
# Use the SLURM version instead:
#   sbatch RUN-workflow.sbatch
#
# WHAT THIS DOES:
# 1. Extracts tree components (fixed outgroups, major clades, clade registry)
# 2. Generates N topology permutations for unresolved clades
# 3. Assigns permanent clade IDs to each permuted topology
# 4. Builds complete species trees by grafting subtrees onto topologies
# 5. Extracts parent-child and parent-sibling relationships
# 6. Generates phylogenetic blocks (Parent::Child transitions)
# 7. Integrates all clade data into comprehensive master table
# 8. Creates tree visualizations (PDF/SVG)
# 9. Generates clade-to-species membership mappings
# 10. Creates output_to_input/ symlinks for downstream subprojects
#
# OUTPUT:
# Results in OUTPUT_pipeline/1-output through 9-output/
# Downstream symlinks in ../../output_to_input/BLOCK_permutations_and_features/
#
################################################################################

echo "========================================================================"
echo "GIGANTIC trees_species - Permutations and Features Pipeline (Local)"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Read execution mode from START_HERE-user_config.yaml
# ============================================================================
# Uses grep to parse flat YAML keys (no Python dependency required).

read_config() {
    local value=$(grep "^${1}:" START_HERE-user_config.yaml 2>/dev/null | head -1 | sed 's/^[^:]*: *//' | sed 's/^"//;s/"$//')
    echo "${value:-$2}"
}

EXECUTION_MODE=$(read_config "execution_mode" "local")

# ============================================================================
# SLURM submission (if execution_mode is "slurm" and not already inside a job)
# ============================================================================
# Self-submits as a SLURM job so heavy work (conda env creation, NextFlow
# pipeline) runs on a compute node — never on the login node.

if [ "${EXECUTION_MODE}" == "slurm" ] && [ -z "${SLURM_JOB_ID}" ]; then
    echo "Execution mode: SLURM (submitting job)"
    echo ""

    SLURM_CPUS=$(read_config "cpus" "1")
    SLURM_MEM=$(read_config "memory_gb" "4")
    SLURM_TIME=$(read_config "time_hours" "1")
    SLURM_ACCOUNT=$(read_config "slurm_account" "")
    SLURM_QOS=$(read_config "slurm_qos" "")

    mkdir -p slurm_logs

    SBATCH_ARGS="--job-name=permutations_and_features"
    SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${SLURM_CPUS}"
    SBATCH_ARGS="${SBATCH_ARGS} --mem=${SLURM_MEM}gb"
    SBATCH_ARGS="${SBATCH_ARGS} --time=${SLURM_TIME}:00:00"
    SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/permutations_and_features-%j.log"

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
    exit 0
fi

if [ -n "${SLURM_JOB_ID}" ]; then
    echo "Running inside SLURM job ${SLURM_JOB_ID}"
else
    echo "Execution mode: local"
fi
echo ""

# ============================================================================
# Activate GIGANTIC Environment (on-demand creation)
# ============================================================================
# This workflow requires:
#   - conda environment: aiG-trees_species-permutations_and_features (Python, PyYAML, ete3, PyQt5)
#   - NextFlow: from conda env OR system module
#
# The environment is created automatically on first run from the yml spec
# colocated at ai/conda_environment.yml. mamba is preferred (much faster);
# conda is the fallback if mamba is not available.
#
# NextFlow availability:
#   - If installed in conda env: used automatically
#   - If not in conda env: falls back to "module load nextflow" (HPC systems)
#   - If neither available: exits with error and instructions
# ============================================================================

ENV_NAME="aiG-trees_species-permutations_and_features"
ENV_YML="ai/conda_environment.yml"

# Specific to GIGANTIC development for GitHub
# Load conda module (required on HPC systems like HiPerGator)
module load conda 2>/dev/null || true

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "ERROR: conda not found!"
    echo ""
    echo "On HPC (HiPerGator): module load conda"
    echo "Otherwise: install conda from https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Create environment on-demand if it does not exist
if ! conda env list 2>/dev/null | grep -q "^${ENV_NAME} "; then
    echo "Environment '${ENV_NAME}' not found. Creating on-demand..."
    echo ""
    if [ ! -f "${ENV_YML}" ]; then
        echo "ERROR: Environment spec not found at: ${ENV_YML}"
        echo "Make sure you are running from a valid GIGANTIC workflow directory."
        exit 1
    fi
    if command -v mamba &> /dev/null; then
        mamba env create -f "${ENV_YML}" -y
        CREATE_EXIT=$?
    else
        conda env create -f "${ENV_YML}" -y
        CREATE_EXIT=$?
    fi
    if [ $CREATE_EXIT -ne 0 ]; then
        echo ""
        echo "ERROR: Failed to create conda environment '${ENV_NAME}' (exit code $CREATE_EXIT)"
        echo "Check the error messages above and verify the spec at: ${ENV_YML}"
        echo ""
        echo "If a partial env was left behind, remove it before retrying:"
        echo "  mamba env remove -n ${ENV_NAME} -y"
        exit 1
    fi
    echo ""
    echo "Environment '${ENV_NAME}' created successfully."
    echo ""
fi

# Activate the environment
if conda activate "${ENV_NAME}" 2>/dev/null; then
    echo "Activated conda environment: ${ENV_NAME}"
else
    echo "WARNING: Could not activate '${ENV_NAME}'. Continuing with current environment."
fi

# Ensure NextFlow is available (conda env or system module)
if ! command -v nextflow &> /dev/null; then
    echo "NextFlow not found in conda env. Trying system module..."
    # Specific to GIGANTIC development for GitHub
    module load nextflow 2>/dev/null || true
    if ! command -v nextflow &> /dev/null; then
        echo ""
        echo "ERROR: NextFlow not available!"
        echo ""
        echo "Options to resolve:"
        echo "  1. Install nextflow in conda env: conda install -n ${ENV_NAME} -c bioconda nextflow"
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

# Check INPUT_user directory exists
if [ ! -d "INPUT_user" ]; then
    echo "ERROR: INPUT_user/ directory not found!"
    echo "  Create it and add your species tree Newick file."
    exit 1
fi
echo "  [OK] INPUT_user/ directory found"

# Check species tree file exists
if [ ! -f "INPUT_user/species_tree.newick" ]; then
    echo "ERROR: Species tree not found!"
    echo "  Expected: INPUT_user/species_tree.newick"
    echo "  Place your Newick-format species tree in INPUT_user/"
    exit 1
fi
echo "  [OK] Species tree found: INPUT_user/species_tree.newick"

echo ""

# ============================================================================
# Run NextFlow Pipeline
# ============================================================================

echo "Running NextFlow pipeline..."
echo ""

# Optionally resume from cached work/ if user enabled it in config
RESUME=$(read_config "resume" "false")
RESUME_FLAG=""
if [ "${RESUME}" == "true" ]; then
    RESUME_FLAG="-resume"
    echo "  resume: enabled (using NextFlow work/ cache)"
fi

# Parallelism mode selects the NextFlow profile from ai/nextflow.config:
#   "slurm" -> process.executor = 'slurm' (each task is its own sbatch)
#   "local" -> process.executor = 'local' (tasks run in parallel here)
PARALLELISM_MODE=$(read_config "parallelism_mode" "local")
case "${PARALLELISM_MODE}" in
    slurm) PROFILE_FLAG="-profile slurm" ;;
    local) PROFILE_FLAG="-profile standard" ;;
    *)
        echo "ERROR: unknown parallelism_mode: '${PARALLELISM_MODE}'"
        echo "Valid values: 'slurm' | 'local' (see START_HERE-user_config.yaml)"
        exit 1
        ;;
esac
echo "  parallelism_mode: ${PARALLELISM_MODE} (nextflow ${PROFILE_FLAG})"

# Pipe SLURM account/QOS from START_HERE-user_config.yaml into nextflow.config
# via --param CLI args so nextflow.config never needs hand-edited duplicates.
# Re-read here because the outer SLURM_ACCOUNT/SLURM_QOS shell vars (if set)
# only exist in the self-submitting branch above, not when re-invoked by sbatch.
NEXTFLOW_SLURM_ACCOUNT=$(read_config "slurm_account" "")
NEXTFLOW_SLURM_QOS=$(read_config "slurm_qos" "")
NEXTFLOW_PARAMS=""
if [ -n "${NEXTFLOW_SLURM_ACCOUNT}" ]; then
    NEXTFLOW_PARAMS="${NEXTFLOW_PARAMS} --slurm_account=${NEXTFLOW_SLURM_ACCOUNT}"
fi
if [ -n "${NEXTFLOW_SLURM_QOS}" ]; then
    NEXTFLOW_PARAMS="${NEXTFLOW_PARAMS} --slurm_qos=${NEXTFLOW_SLURM_QOS}"
fi

nextflow run ai/main.nf ${RESUME_FLAG} ${PROFILE_FLAG} ${NEXTFLOW_PARAMS}

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
# Symlinks are created in ONE location at the subproject root:
#   ../../output_to_input/BLOCK_permutations_and_features/
#
# Downstream subprojects (orthogroups_X_ocl, annotations_X_ocl) read from here.
# ============================================================================

echo ""
echo "Creating symlinks for downstream subprojects..."

# Determine the workflow directory name dynamically
# (supports both COPYME templates and RUN_XX instances)
WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

# --- Subproject-root output_to_input/BLOCK_permutations_and_features/ ---
SHARED_DIR="../../output_to_input/BLOCK_permutations_and_features"
mkdir -p "${SHARED_DIR}"

# Remove any stale symlinks from previous runs
for old_link in "${SHARED_DIR}"/Species_*; do
    if [ -L "$old_link" ]; then
        rm "$old_link"
    fi
done

# Create symlinks for each output category in 4-output through 9-output
# Phylogenetic Paths (from 4-output)
if [ -d "OUTPUT_pipeline/4-output" ]; then
    for item in OUTPUT_pipeline/4-output/*phylogenetic_paths*; do
        if [ -f "$item" ]; then
            mkdir -p "${SHARED_DIR}/Species_Phylogenetic_Paths"
            ln -sf "../../../BLOCK_permutations_and_features/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/4-output/$(basename "$item")" \
                "${SHARED_DIR}/Species_Phylogenetic_Paths/$(basename "$item")"
        fi
    done
fi

# Species Tree Structures (from 4-output newick_trees/)
if [ -d "OUTPUT_pipeline/4-output/newick_trees" ]; then
    mkdir -p "${SHARED_DIR}/Species_Tree_Structures"
    for item in OUTPUT_pipeline/4-output/newick_trees/*.newick; do
        if [ -f "$item" ]; then
            ln -sf "../../../BLOCK_permutations_and_features/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/4-output/newick_trees/$(basename "$item")" \
                "${SHARED_DIR}/Species_Tree_Structures/$(basename "$item")"
        fi
    done
    # Also link topology files from 2-output and 3-output
    for item in OUTPUT_pipeline/2-output/newick_trees/*.newick OUTPUT_pipeline/3-output/newick_trees/*.newick; do
        if [ -f "$item" ]; then
            # Extract the relative path component (e.g., 2-output/newick_trees/file.newick)
            rel_path="${item#OUTPUT_pipeline/}"
            ln -sf "../../../BLOCK_permutations_and_features/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/${rel_path}" \
                "${SHARED_DIR}/Species_Tree_Structures/$(basename "$item")"
        fi
    done
fi

# Parent Sibling Sets (from 5-output)
if [ -d "OUTPUT_pipeline/5-output" ]; then
    for dir in OUTPUT_pipeline/5-output/*Parent_Sibling_Sets; do
        if [ -d "$dir" ]; then
            mkdir -p "${SHARED_DIR}/Species_Parent_Sibling_Sets"
            for item in "$dir"/*.tsv; do
                if [ -f "$item" ]; then
                    ln -sf "../../../BLOCK_permutations_and_features/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/5-output/$(basename "$dir")/$(basename "$item")" \
                        "${SHARED_DIR}/Species_Parent_Sibling_Sets/$(basename "$item")"
                fi
            done
        fi
    done
fi

# Parent Child Relationships (from 5-output)
if [ -d "OUTPUT_pipeline/5-output" ]; then
    for dir in OUTPUT_pipeline/5-output/*Parent_Child_Relationships; do
        if [ -d "$dir" ]; then
            mkdir -p "${SHARED_DIR}/Species_Parent_Child_Relationships"
            for item in "$dir"/*.tsv; do
                if [ -f "$item" ]; then
                    ln -sf "../../../BLOCK_permutations_and_features/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/5-output/$(basename "$dir")/$(basename "$item")" \
                        "${SHARED_DIR}/Species_Parent_Child_Relationships/$(basename "$item")"
                fi
            done
        fi
    done
fi

# Phylogenetic Blocks (from 6-output)
if [ -d "OUTPUT_pipeline/6-output" ]; then
    for item in OUTPUT_pipeline/6-output/*phylogenetic_blocks*; do
        if [ -f "$item" ]; then
            mkdir -p "${SHARED_DIR}/Species_Phylogenetic_Blocks"
            ln -sf "../../../BLOCK_permutations_and_features/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/6-output/$(basename "$item")" \
                "${SHARED_DIR}/Species_Phylogenetic_Blocks/$(basename "$item")"
        fi
    done
fi

# Clade Species Mappings (from 9-output)
if [ -d "OUTPUT_pipeline/9-output" ]; then
    for item in OUTPUT_pipeline/9-output/*clade_species_mappings*; do
        if [ -f "$item" ]; then
            mkdir -p "${SHARED_DIR}/Species_Clade_Species_Mappings"
            ln -sf "../../../BLOCK_permutations_and_features/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/9-output/$(basename "$item")" \
                "${SHARED_DIR}/Species_Clade_Species_Mappings/$(basename "$item")"
        fi
    done
fi

echo "  output_to_input/BLOCK_permutations_and_features/ -> symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! trees_species permutations and features pipeline complete."
echo ""
echo "Research outputs (real files):"
echo "  OUTPUT_pipeline/1-output/  Tree components (outgroups, major clades)"
echo "  OUTPUT_pipeline/2-output/  Topology skeletons (permutations)"
echo "  OUTPUT_pipeline/3-output/  Annotated topologies (with clade IDs)"
echo "  OUTPUT_pipeline/4-output/  Complete trees + phylogenetic paths"
echo "  OUTPUT_pipeline/5-output/  Parent-child/sibling relationships"
echo "  OUTPUT_pipeline/6-output/  Phylogenetic blocks"
echo "  OUTPUT_pipeline/7-output/  Integrated clade data (master table)"
echo "  OUTPUT_pipeline/8-output/  Tree visualizations (PDF/SVG)"
echo "  OUTPUT_pipeline/9-output/  Clade-species mappings"
echo ""
echo "Downstream symlinks:"
echo "  ../../output_to_input/BLOCK_permutations_and_features/ (for OCL subprojects)"
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
