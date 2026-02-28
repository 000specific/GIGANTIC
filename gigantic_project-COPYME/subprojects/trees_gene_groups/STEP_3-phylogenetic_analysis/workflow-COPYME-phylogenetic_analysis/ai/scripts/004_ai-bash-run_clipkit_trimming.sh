#!/bin/bash
# GIGANTIC BLOCK 3 - Script 004: Run ClipKIT Trimming
# AI: Claude Code | Sonnet 4.5 | 2025 November 07 04:00 | Purpose: Trim alignment with ClipKit smart-gap mode
# Human: Eric Edsinger

# Activate conda environment
module load python
module load conda
conda activate clipkit

# Parse arguments
HOMOLOG_ID=$1

if [ -z "$HOMOLOG_ID" ]; then
    echo "Usage: $0 HOMOLOG_ID"
    echo "Example: $0 AGS-species67_T1-species37-innexin_pannexin"
    exit 1
fi

# Run ClipKit
clipkit "output/3-${HOMOLOG_ID}.mafft" \
    -m smart-gap \
    -o "output/4-${HOMOLOG_ID}.clipkit-smartgap" \
    -l "output/4-${HOMOLOG_ID}.clipkit-smartgap.log"

echo "ClipKit trimming complete: output/4-${HOMOLOG_ID}.clipkit-smartgap"

