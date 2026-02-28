#!/bin/bash
# GIGANTIC BLOCK 3 - Script 005: Run FastTree
# AI: Claude Code | Sonnet 4.5 | 2025 November 07 04:05 | Purpose: Generate FastTree phylogeny
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

