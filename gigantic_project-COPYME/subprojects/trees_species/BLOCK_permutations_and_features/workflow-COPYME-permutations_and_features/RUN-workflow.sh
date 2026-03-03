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
# 2. Edit permutations_and_features_config.yaml:
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
# Activate GIGANTIC Environment
# ============================================================================

# Load conda module (required on HPC systems like HiPerGator)
module load conda 2>/dev/null || true

# Activate the trees_species environment
if conda activate ai_gigantic_trees_species 2>/dev/null; then
    echo "Activated conda environment: ai_gigantic_trees_species"
else
    # Check if nextflow is already available in PATH
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: Environment 'ai_gigantic_trees_species' not found!"
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

# Check config file exists
if [ ! -f "permutations_and_features_config.yaml" ]; then
    echo "ERROR: Configuration file not found!"
    echo "Expected: permutations_and_features_config.yaml"
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
    for item in OUTPUT_pipeline/4-output/*evolutionary_paths*; do
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
            ln -sf "../../../../BLOCK_permutations_and_features/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/4-output/newick_trees/$(basename "$item")" \
                "${SHARED_DIR}/Species_Tree_Structures/$(basename "$item")"
        fi
    done
    # Also link topology files from 2-output and 3-output
    for item in OUTPUT_pipeline/2-output/newick_trees/*.newick OUTPUT_pipeline/3-output/newick_trees/*.newick; do
        if [ -f "$item" ]; then
            # Extract the relative path component (e.g., 2-output/newick_trees/file.newick)
            rel_path="${item#OUTPUT_pipeline/}"
            ln -sf "../../../../BLOCK_permutations_and_features/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/${rel_path}" \
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
                    ln -sf "../../../../BLOCK_permutations_and_features/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/5-output/$(basename "$dir")/$(basename "$item")" \
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
                    ln -sf "../../../../BLOCK_permutations_and_features/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/5-output/$(basename "$dir")/$(basename "$item")" \
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
echo "  OUTPUT_pipeline/4-output/  Complete trees + evolutionary paths"
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
