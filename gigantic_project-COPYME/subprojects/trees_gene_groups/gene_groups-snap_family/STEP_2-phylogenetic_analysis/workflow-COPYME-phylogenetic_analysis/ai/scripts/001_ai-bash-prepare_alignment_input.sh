#!/bin/bash
# GIGANTIC STEP_2 - Script 001: Prepare Alignment Input
# AI: Claude Code | Opus 4.6 | 2026 March 10 | Purpose: Stage AGS sequences from STEP_1 for alignment
# Human: Eric Edsinger
#
# Called by: main.nf process prepare_alignment_input
# NextFlow manages: conda environment, SLURM resources
# Arguments:
#   $1 = Input AGS FASTA file (from STEP_1 output_to_input)
#   $2 = Output AGS FASTA file path

INPUT_AGS="$1"
OUTPUT_FILE="$2"

if [ -z "$INPUT_AGS" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "Usage: $0 INPUT_AGS OUTPUT_FILE"
    echo "Example: $0 path/to/16_ai-ags-species70_T1-species70-innexin_pannexin-homologs.aa 1-output/1_ai-ags-species70_T1-species70-innexin_pannexin.aa"
    exit 1
fi

if [ ! -f "$INPUT_AGS" ]; then
    echo "ERROR: Input AGS file not found: $INPUT_AGS"
    echo "Ensure STEP_1 has completed and output_to_input/STEP_1-homolog_discovery/ags_fastas/ contains results."
    exit 1
fi

cp "$INPUT_AGS" "$OUTPUT_FILE"

SEQUENCE_COUNT=$(grep -c '^>' "$OUTPUT_FILE")
echo "Staged alignment input: $OUTPUT_FILE ($SEQUENCE_COUNT sequences)"
echo "Source: $INPUT_AGS"
