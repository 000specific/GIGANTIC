#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 01 | Purpose: Run DIAMOND blastp search for one split file against NCBI nr
# Human: Eric Edsinger

################################################################################
# 003_ai-bash-run_diamond_search.sh
################################################################################
#
# PURPOSE:
# Run DIAMOND blastp for a single split FASTA file against the NCBI nr database.
# Called by NextFlow (one process per split file) or manually for debugging.
#
# USAGE:
#   bash 003_ai-bash-run_diamond_search.sh <input_fasta> <diamond_db> <output_file> <evalue> <max_targets> <threads>
#
# ARGUMENTS:
#   input_fasta    Path to split FASTA file (from script 002)
#   diamond_db     Path to DIAMOND-formatted nr database (.dmnd)
#   output_file    Path for output TSV file
#   evalue         E-value threshold (e.g., 1e-5)
#   max_targets    Maximum target sequences per query (e.g., 10)
#   threads        Number of CPU threads (e.g., 1)
#
# OUTPUT FORMAT:
#   15-column TSV: qseqid sseqid pident length mismatch gapopen
#                  qstart qend sstart send evalue bitscore
#                  stitle full_qseq full_sseq
#
################################################################################

# Arguments
INPUT_FASTA="$1"
DIAMOND_DATABASE="$2"
OUTPUT_FILE="$3"
EVALUE="${4:-1e-5}"
MAX_TARGETS="${5:-10}"
THREADS="${6:-1}"

# Validate arguments
if [ -z "$INPUT_FASTA" ] || [ -z "$DIAMOND_DATABASE" ] || [ -z "$OUTPUT_FILE" ]; then
    echo "ERROR: Missing required arguments"
    echo "Usage: bash 003_ai-bash-run_diamond_search.sh <input_fasta> <diamond_db> <output_file> [evalue] [max_targets] [threads]"
    exit 1
fi

if [ ! -f "$INPUT_FASTA" ]; then
    echo "ERROR: Input FASTA not found: $INPUT_FASTA"
    exit 1
fi

if [ ! -f "$DIAMOND_DATABASE" ]; then
    echo "ERROR: DIAMOND database not found: $DIAMOND_DATABASE"
    exit 1
fi

# Create output directory if needed
OUTPUT_DIR=$(dirname "$OUTPUT_FILE")
mkdir -p "$OUTPUT_DIR"

echo "========================================================================"
echo "DIAMOND blastp Search"
echo "========================================================================"
echo ""
echo "Input FASTA: $INPUT_FASTA"
echo "Database: $DIAMOND_DATABASE"
echo "Output: $OUTPUT_FILE"
echo "E-value: $EVALUE"
echo "Max targets: $MAX_TARGETS"
echo "Threads: $THREADS"
echo ""
echo "Started: $(date)"
echo ""

# Count input sequences
SEQUENCE_COUNT=$(grep -c "^>" "$INPUT_FASTA")
echo "Input sequences: $SEQUENCE_COUNT"
echo ""

# Run DIAMOND blastp
# --sensitive: Use sensitive mode for better detection of distant homologs
# --outfmt 6: Tabular output with custom columns
# stitle: Full NCBI header (subject title)
# full_qseq: Full query sequence (for self/non-self comparison)
# full_sseq: Full subject sequence (for self/non-self comparison)

diamond blastp \
    --query "$INPUT_FASTA" \
    --db "$DIAMOND_DATABASE" \
    --out "$OUTPUT_FILE" \
    --evalue "$EVALUE" \
    --max-target-seqs "$MAX_TARGETS" \
    --threads "$THREADS" \
    --sensitive \
    --outfmt 6 qseqid sseqid pident length mismatch gapopen \
                qstart qend sstart send evalue bitscore \
                stitle full_qseq full_sseq

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    # Count output lines
    if [ -f "$OUTPUT_FILE" ]; then
        HIT_COUNT=$(wc -l < "$OUTPUT_FILE")
        echo "DIAMOND completed successfully."
        echo "Hits found: $HIT_COUNT"
    else
        echo "WARNING: DIAMOND completed but no output file created."
        # Create empty file so downstream scripts don't fail
        touch "$OUTPUT_FILE"
    fi
else
    echo "ERROR: DIAMOND failed with exit code $EXIT_CODE"
    exit $EXIT_CODE
fi

echo ""
echo "Completed: $(date)"
echo "========================================================================"

exit 0
