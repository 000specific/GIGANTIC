#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 26 | Purpose: Run OrthoFinder on proteomes
# Human: Eric Edsinger

################################################################################
# GIGANTIC OrthoFinder Workflow - Run OrthoFinder
################################################################################
#
# PURPOSE:
# Run OrthoFinder with high-quality settings (diamond_ultra_sens) using a
# user-provided species tree.
#
# USAGE:
#   bash RUN_orthofinder.sh
#   OR
#   sbatch SLURM_orthofinder.sbatch
#
# INPUTS (in INPUT_user/):
#   - speciesNN_species_tree.newick  - Species tree in Newick format (NN = species count)
#   - proteomes/                     - Directory containing .fasta or .fa proteome files
#                                      (or symlinks to proteomes)
#
# OUTPUTS (in OUTPUT_pipeline/):
#   - orthofinder_results/           - Full OrthoFinder output directory
#
# ORTHOFINDER SETTINGS:
#   -t 128          : 128 threads for sequence search
#   -a 128          : 128 threads for analysis
#   -X              : Don't add species names to sequence IDs (already in GIGANTIC format)
#   -s              : Use provided species tree
#   -S diamond_ultra_sens : Ultra-sensitive DIAMOND search (high quality, slower)
#   -T fasttree     : Use FastTree for gene trees
#
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory (workflow root)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
INPUT_DIR="${SCRIPT_DIR}/INPUT_user"
OUTPUT_DIR="${SCRIPT_DIR}/OUTPUT_pipeline"

echo "========================================================================"
echo "GIGANTIC OrthoFinder Workflow"
echo "========================================================================"
echo ""
echo "Workflow directory: $SCRIPT_DIR"
echo "Input directory: $INPUT_DIR"
echo "Output directory: $OUTPUT_DIR"
echo ""

################################################################################
# Validate inputs
################################################################################

echo -e "${YELLOW}Validating inputs...${NC}"

# Find species tree
SPECIES_TREE=$(find "$INPUT_DIR" -maxdepth 1 -name "species*_species_tree.newick" 2>/dev/null | head -1)

if [ -z "$SPECIES_TREE" ]; then
    echo -e "${RED}ERROR: No species tree found!${NC}"
    echo "Expected: INPUT_user/speciesNN_species_tree.newick"
    echo "Example: INPUT_user/species67_species_tree.newick"
    exit 1
fi

echo "  Species tree: $(basename "$SPECIES_TREE")"

# Extract species count from filename
SPECIES_COUNT=$(basename "$SPECIES_TREE" | grep -oP 'species\K\d+')
echo "  Species count (from filename): $SPECIES_COUNT"

# Check proteomes directory
PROTEOMES_DIR="${INPUT_DIR}/proteomes"

if [ ! -d "$PROTEOMES_DIR" ]; then
    echo -e "${RED}ERROR: Proteomes directory not found!${NC}"
    echo "Expected: INPUT_user/proteomes/"
    echo "This directory should contain .fasta or .fa proteome files"
    exit 1
fi

# Count proteome files
PROTEOME_COUNT=$(find "$PROTEOMES_DIR" -maxdepth 1 \( -name "*.fasta" -o -name "*.fa" -o -name "*.faa" -o -name "*.pep" \) | wc -l)

if [ "$PROTEOME_COUNT" -eq 0 ]; then
    echo -e "${RED}ERROR: No proteome files found in $PROTEOMES_DIR${NC}"
    echo "Expected .fasta, .fa, .faa, or .pep files"
    exit 1
fi

echo "  Proteomes found: $PROTEOME_COUNT"

# Verify species count matches
if [ -n "$SPECIES_COUNT" ] && [ "$PROTEOME_COUNT" -ne "$SPECIES_COUNT" ]; then
    echo -e "${YELLOW}WARNING: Species count mismatch!${NC}"
    echo "  Tree filename suggests: $SPECIES_COUNT species"
    echo "  Proteomes found: $PROTEOME_COUNT"
    echo ""
    read -p "Continue anyway? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Aborting."
        exit 1
    fi
fi

echo ""
echo -e "${GREEN}Inputs validated.${NC}"
echo ""

################################################################################
# Check for existing output
################################################################################

ORTHOFINDER_OUTPUT="${OUTPUT_DIR}/orthofinder_results"

if [ -d "$ORTHOFINDER_OUTPUT" ]; then
    echo -e "${YELLOW}WARNING: Previous OrthoFinder output exists!${NC}"
    echo "Directory: $ORTHOFINDER_OUTPUT"
    echo ""
    echo "Options:"
    echo "  1. Remove and start fresh"
    echo "  2. Abort (keep existing)"
    read -p "Choice (1 or 2): " choice

    if [ "$choice" == "1" ]; then
        echo "Removing previous output..."
        rm -rf "$ORTHOFINDER_OUTPUT"
    else
        echo "Aborting to preserve existing output."
        exit 0
    fi
fi

################################################################################
# Run OrthoFinder
################################################################################

echo "========================================================================"
echo "Running OrthoFinder"
echo "========================================================================"
echo ""
echo "Command:"
echo "  orthofinder -t 128 -a 128 -X \\"
echo "    -s $SPECIES_TREE \\"
echo "    -S diamond_ultra_sens -T fasttree \\"
echo "    -f $PROTEOMES_DIR \\"
echo "    -o $ORTHOFINDER_OUTPUT"
echo ""
echo "Start time: $(date)"
echo ""

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Run OrthoFinder
orthofinder \
    -t 128 \
    -a 128 \
    -X \
    -s "$SPECIES_TREE" \
    -S diamond_ultra_sens \
    -T fasttree \
    -f "$PROTEOMES_DIR" \
    -o "$ORTHOFINDER_OUTPUT"

echo ""
echo "End time: $(date)"
echo ""

################################################################################
# Summary
################################################################################

echo "========================================================================"
echo -e "${GREEN}OrthoFinder Complete${NC}"
echo "========================================================================"
echo ""
echo "Output directory: $ORTHOFINDER_OUTPUT"
echo ""
echo "Key output files:"
echo "  Orthogroups/Orthogroups.tsv           - All orthogroups (OGs)"
echo "  Orthogroups/Orthogroups_UnassignedGenes.tsv - Singletons"
echo "  Phylogenetic_Hierarchical_Orthogroups/N0.tsv - HOGs at root level"
echo "  Species_Tree/                         - Species tree files"
echo ""

# Show output structure
if [ -d "$ORTHOFINDER_OUTPUT" ]; then
    echo "Output structure:"
    ls -la "$ORTHOFINDER_OUTPUT"
fi

echo ""
echo "========================================================================"
