#!/bin/bash
# GIGANTIC STEP_2 - Script 003: Run MAFFT Alignment
# AI: Claude Code | Opus 4.6 | 2026 March 10 | Purpose: MAFFT multiple sequence alignment
# Human: Eric Edsinger
#
# Called by: main.nf process run_mafft_alignment
# NextFlow manages: conda environment (ai_gigantic_mafft), SLURM resources
# Arguments:
#   $1 = Input FASTA file (cleaned sequences)
#   $2 = Output alignment file path
#   $3 = maxiterate (default: 1000)
#   $4 = bl (default: 45)
#   $5 = threads (default: 50)

INPUT_FASTA="$1"
OUTPUT_FILE="$2"
MAXITERATE="${3:-1000}"
BL="${4:-45}"
THREADS="${5:-50}"

if [ -z "$INPUT_FASTA" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "Usage: $0 INPUT_FASTA OUTPUT_FILE [MAXITERATE] [BL] [THREADS]"
    exit 1
fi

if [ ! -f "$INPUT_FASTA" ]; then
    echo "ERROR: Input file not found: $INPUT_FASTA"
    exit 1
fi

echo "Running MAFFT alignment..."
echo "  Input: $INPUT_FASTA"
echo "  maxiterate: $MAXITERATE"
echo "  bl: $BL"
echo "  threads: $THREADS"

mafft --originalseqonly --maxiterate ${MAXITERATE} \
    --reorder --bl ${BL} \
    --thread ${THREADS} \
    "$INPUT_FASTA" > "$OUTPUT_FILE"

echo "MAFFT alignment complete: $OUTPUT_FILE"
