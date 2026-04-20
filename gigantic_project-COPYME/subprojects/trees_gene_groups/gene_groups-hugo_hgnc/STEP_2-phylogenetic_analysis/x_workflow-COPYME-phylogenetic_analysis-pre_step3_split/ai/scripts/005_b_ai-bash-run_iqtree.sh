#!/bin/bash
# GIGANTIC STEP_2 - Script 005_b: Run IQ-TREE
# AI: Claude Code | Opus 4.6 | 2026 March 10 | Purpose: IQ-TREE ML phylogenetic inference (publication-quality)
# Human: Eric Edsinger
#
# Called by: main.nf process run_iqtree
# NextFlow manages: conda environment (ai_gigantic_iqtree), SLURM resources
# Arguments:
#   $1 = Input trimmed alignment file
#   $2 = Output prefix (IQ-TREE creates prefix.treefile, prefix.log, etc.)
#   $3 = Model (default: MFP)
#   $4 = Bootstrap replicates (default: 2000)
#   $5 = aLRT replicates (default: 2000)
#   $6 = Threads (default: AUTO)

INPUT_ALIGNMENT="$1"
OUTPUT_PREFIX="$2"
MODEL="${3:-MFP}"
BOOTSTRAP="${4:-2000}"
ALRT="${5:-2000}"
THREADS="${6:-AUTO}"

if [ -z "$INPUT_ALIGNMENT" ] || [ -z "$OUTPUT_PREFIX" ]; then
    echo "Usage: $0 INPUT_ALIGNMENT OUTPUT_PREFIX [MODEL] [BOOTSTRAP] [ALRT] [THREADS]"
    exit 1
fi

if [ ! -f "$INPUT_ALIGNMENT" ]; then
    echo "ERROR: Input file not found: $INPUT_ALIGNMENT"
    exit 1
fi

echo "Running IQ-TREE..."
echo "  Input: $INPUT_ALIGNMENT"
echo "  Model: $MODEL"
echo "  Bootstrap: $BOOTSTRAP"
echo "  aLRT: $ALRT"
echo "  Threads: $THREADS"

iqtree -s "$INPUT_ALIGNMENT" \
    -m "$MODEL" \
    --prefix "$OUTPUT_PREFIX" \
    --rate \
    -B "$BOOTSTRAP" \
    -alrt "$ALRT" \
    -T "$THREADS" \
    -bnni

echo "IQ-TREE complete: ${OUTPUT_PREFIX}.treefile"
