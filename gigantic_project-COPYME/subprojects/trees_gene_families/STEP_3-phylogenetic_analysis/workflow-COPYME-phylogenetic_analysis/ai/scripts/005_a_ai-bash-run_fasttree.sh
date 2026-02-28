#!/bin/bash
# GIGANTIC STEP_3 - Script 005_a: Run FastTree
# AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: FastTree ML phylogeny (default, recommended)
# Human: Eric Edsinger

# Activate conda environment
module load python
module load conda
conda activate fasttree

# Parse arguments
HOMOLOG_ID=$1

if [ -z "$HOMOLOG_ID" ]; then
    echo "Usage: $0 HOMOLOG_ID"
    echo "Example: $0 AGS-species67_T1-species37-innexin_pannexin"
    exit 1
fi

# Run FastTree
FastTree "output/4-${HOMOLOG_ID}.clipkit-smartgap" \
    > "output/5-${HOMOLOG_ID}.fasttree" \
    2> "output/5-${HOMOLOG_ID}-log"

echo "FastTree complete: output/5-${HOMOLOG_ID}.fasttree"

