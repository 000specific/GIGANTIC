#!/bin/bash
# GIGANTIC STEP_2 - Script 005_a: Run FastTree
# AI: Claude Code | Opus 4.6 | 2026 March 10 | Purpose: FastTree ML phylogeny (default, recommended)
# Human: Eric Edsinger
#
# Called by: main.nf process run_fasttree
# NextFlow manages: conda environment (ai_gigantic_fasttree), SLURM resources
# Arguments:
#   $1 = Input trimmed alignment file
#   $2 = Output tree file path
#   $3 = Output log file path

INPUT_ALIGNMENT="$1"
OUTPUT_TREE="$2"
OUTPUT_LOG="${3:-/dev/null}"

if [ -z "$INPUT_ALIGNMENT" ] || [ -z "$OUTPUT_TREE" ]; then
    echo "Usage: $0 INPUT_ALIGNMENT OUTPUT_TREE [OUTPUT_LOG]"
    exit 1
fi

if [ ! -f "$INPUT_ALIGNMENT" ]; then
    echo "ERROR: Input file not found: $INPUT_ALIGNMENT"
    exit 1
fi

echo "Running FastTree..."
echo "  Input: $INPUT_ALIGNMENT"

FastTree "$INPUT_ALIGNMENT" \
    > "$OUTPUT_TREE" \
    2> "$OUTPUT_LOG"

echo "FastTree complete: $OUTPUT_TREE"
