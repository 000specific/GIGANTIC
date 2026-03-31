#!/bin/bash
# GIGANTIC STEP_2 - Script 002: Replace Special Characters
# AI: Claude Code | Opus 4.6 | 2026 March 10 | Purpose: Remove leading/trailing dashes from sequences for alignment
# Human: Eric Edsinger
#
# Called by: main.nf process clean_sequences
# NextFlow manages: conda environment, SLURM resources
# Arguments:
#   $1 = Input FASTA file
#   $2 = Output FASTA file path

INPUT_FASTA="$1"
OUTPUT_FILE="$2"

if [ -z "$INPUT_FASTA" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "Usage: $0 INPUT_FASTA OUTPUT_FILE"
    exit 1
fi

if [ ! -f "$INPUT_FASTA" ]; then
    echo "ERROR: Input file not found: $INPUT_FASTA"
    exit 1
fi

# Remove ALL leading and trailing dashes from sequences (not headers)
# sed 's/^-*//' removes all leading dashes, 's/-*$//' removes all trailing dashes
sed '/^>/!{s/^-*//; s/-*$//}' "$INPUT_FASTA" > "$OUTPUT_FILE"

echo "Cleaned sequences: $OUTPUT_FILE"
