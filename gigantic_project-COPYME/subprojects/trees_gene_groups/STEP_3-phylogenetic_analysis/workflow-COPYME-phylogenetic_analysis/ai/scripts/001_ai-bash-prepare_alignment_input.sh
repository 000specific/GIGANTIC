#!/bin/bash
# GIGANTIC BLOCK 3 - Script 001: Prepare Alignment Input
# AI: Claude Code | Sonnet 4.5 | 2025 November 07 03:45 | Purpose: Prepare input for sequence alignment
# Human: Eric Edsinger

# Parse arguments
GENE_FAMILY=$1
PROJECT_DB=$2
BLOCK2_OUTPUT=$3

if [ -z "$GENE_FAMILY" ] || [ -z "$PROJECT_DB" ] || [ -z "$BLOCK2_OUTPUT" ]; then
    echo "Usage: $0 GENE_FAMILY PROJECT_DB BLOCK2_OUTPUT"
    echo "Example: $0 innexin_pannexin species67_T1-species37 ../block_2-homologs/job_1/output"
    exit 1
fi

# Copy homolog file from Block 2 (script 016 output)
HOMOLOG_FILE="${BLOCK2_OUTPUT}/16-output/16_ai-AGS-${PROJECT_DB}-${GENE_FAMILY}-homologs.aa"
OUTPUT_FILE="output/1-AGS-${PROJECT_DB}-${GENE_FAMILY}.aa"

if [ ! -f "$HOMOLOG_FILE" ]; then
    echo "ERROR: Homolog file not found: $HOMOLOG_FILE"
    exit 1
fi

mkdir -p input output
cp "$HOMOLOG_FILE" input/
cp "$HOMOLOG_FILE" "$OUTPUT_FILE"

echo "Prepared alignment input: $OUTPUT_FILE"
echo "Copied from: $HOMOLOG_FILE"

