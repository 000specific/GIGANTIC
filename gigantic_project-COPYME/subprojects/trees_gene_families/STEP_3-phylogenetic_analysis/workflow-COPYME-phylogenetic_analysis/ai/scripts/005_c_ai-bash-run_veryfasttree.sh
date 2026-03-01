#!/bin/bash
# GIGANTIC STEP_3 - Script 005_c: Run VeryFastTree
# AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: VeryFastTree parallelized ML phylogeny (large datasets)
# Human: Eric Edsinger
#
# VeryFastTree is a drop-in FastTree replacement optimized for parallelization.
# Best suited for datasets with >10,000 sequences where threading provides speedup.
# For typical GIGANTIC datasets (50-500 sequences), FastTree produces better trees.

# Activate conda environment
module load python
module load conda
conda activate ai_gigantic_trees_gene_families

# Parse arguments
HOMOLOG_ID=$1
THREADS=${2:-4}

if [ -z "$HOMOLOG_ID" ]; then
    echo "Usage: $0 HOMOLOG_ID [THREADS]"
    echo "Example: $0 ags-species67_T1-species67-innexin_pannexin 4"
    exit 1
fi

# Run VeryFastTree
VeryFastTree \
    -threads ${THREADS} \
    "output/4-${HOMOLOG_ID}.clipkit-smartgap" \
    > "output/5_c-${HOMOLOG_ID}.veryfasttree" \
    2> "output/5_c-${HOMOLOG_ID}-log"

echo "VeryFastTree complete: output/5_c-${HOMOLOG_ID}.veryfasttree"
