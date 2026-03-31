#!/bin/bash
# GIGANTIC STEP_2 - Script 004: Run ClipKit Trimming
# AI: Claude Code | Opus 4.6 | 2026 March 10 | Purpose: Trim alignment with ClipKit
# Human: Eric Edsinger
#
# Called by: main.nf process run_clipkit_trimming
# NextFlow manages: conda environment (ai_gigantic_clipkit), SLURM resources
# Arguments:
#   $1 = Input alignment file
#   $2 = Output trimmed file path
#   $3 = ClipKit mode (default: smart-gap)

INPUT_ALIGNMENT="$1"
OUTPUT_FILE="$2"
MODE="${3:-smart-gap}"

if [ -z "$INPUT_ALIGNMENT" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "Usage: $0 INPUT_ALIGNMENT OUTPUT_FILE [MODE]"
    exit 1
fi

if [ ! -f "$INPUT_ALIGNMENT" ]; then
    echo "ERROR: Input file not found: $INPUT_ALIGNMENT"
    exit 1
fi

echo "Running ClipKit trimming..."
echo "  Input: $INPUT_ALIGNMENT"
echo "  Mode: $MODE"

clipkit "$INPUT_ALIGNMENT" \
    -m "$MODE" \
    -o "$OUTPUT_FILE" \
    -l

echo "ClipKit trimming complete: $OUTPUT_FILE"
