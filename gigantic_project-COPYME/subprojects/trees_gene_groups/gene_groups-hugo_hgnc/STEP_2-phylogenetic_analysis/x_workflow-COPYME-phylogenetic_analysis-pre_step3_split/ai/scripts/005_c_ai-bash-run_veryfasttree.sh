#!/bin/bash
# GIGANTIC STEP_2 - Script 005_c: Run VeryFastTree
# AI: Claude Code | Opus 4.6 | 2026 March 10 | Purpose: VeryFastTree parallelized ML phylogeny (large datasets)
# Human: Eric Edsinger
#
# VeryFastTree is a drop-in FastTree replacement optimized for parallelization.
# Best suited for datasets with >10,000 sequences where threading provides speedup.
# For typical GIGANTIC datasets (50-500 sequences), FastTree produces better trees.
#
# Called by: main.nf process run_veryfasttree
# NextFlow manages: conda environment (ai_gigantic_veryfasttree), SLURM resources
# Arguments:
#   $1 = Input trimmed alignment file
#   $2 = Output tree file path
#   $3 = Output log file path
#   $4 = Threads (default: 4)

INPUT_ALIGNMENT="$1"
OUTPUT_TREE="$2"
OUTPUT_LOG="${3:-/dev/null}"
THREADS="${4:-4}"

if [ -z "$INPUT_ALIGNMENT" ] || [ -z "$OUTPUT_TREE" ]; then
    echo "Usage: $0 INPUT_ALIGNMENT OUTPUT_TREE [OUTPUT_LOG] [THREADS]"
    exit 1
fi

if [ ! -f "$INPUT_ALIGNMENT" ]; then
    echo "ERROR: Input file not found: $INPUT_ALIGNMENT"
    exit 1
fi

echo "Running VeryFastTree..."
echo "  Input: $INPUT_ALIGNMENT"
echo "  Threads: $THREADS"

VeryFastTree \
    -threads ${THREADS} \
    "$INPUT_ALIGNMENT" \
    > "$OUTPUT_TREE" \
    2> "$OUTPUT_LOG"

echo "VeryFastTree complete: $OUTPUT_TREE"
