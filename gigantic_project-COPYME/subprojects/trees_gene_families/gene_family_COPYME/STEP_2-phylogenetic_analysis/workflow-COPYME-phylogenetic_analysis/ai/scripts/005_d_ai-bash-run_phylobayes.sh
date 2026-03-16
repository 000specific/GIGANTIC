#!/bin/bash
# GIGANTIC STEP_2 - Script 005_d: Run PhyloBayes
# AI: Claude Code | Opus 4.6 | 2026 March 10 | Purpose: PhyloBayes Bayesian phylogenetic inference
# Human: Eric Edsinger
#
# PhyloBayes uses site-heterogeneous CAT-GTR models and MCMC sampling.
# Runs 2 independent chains for convergence assessment using bpcomp/tracecomp.
# Very slow (days to weeks) - use as Bayesian counterpoint to ML methods.
#
# Called by: main.nf process run_phylobayes
# NextFlow manages: conda environment (ai_gigantic_phylobayes), SLURM resources
# Arguments:
#   $1 = Input trimmed alignment file (FASTA format)
#   $2 = Output directory
#   $3 = Output tree filename (written inside output directory)
#   $4 = PhyloBayes model flags (default: "-cat -gtr")
#   $5 = Generations (default: 10000)
#   $6 = Burnin (default: 2500)
#   $7 = Every (default: 1)

INPUT_ALIGNMENT="$1"
OUTPUT_DIR="$2"
OUTPUT_TREE_NAME="$3"
MODEL_FLAGS="${4:--cat -gtr}"
GENERATIONS="${5:-10000}"
BURNIN="${6:-2500}"
EVERY="${7:-1}"

if [ -z "$INPUT_ALIGNMENT" ] || [ -z "$OUTPUT_DIR" ] || [ -z "$OUTPUT_TREE_NAME" ]; then
    echo "Usage: $0 INPUT_ALIGNMENT OUTPUT_DIR OUTPUT_TREE_NAME [MODEL_FLAGS] [GENERATIONS] [BURNIN] [EVERY]"
    exit 1
fi

if [ ! -f "$INPUT_ALIGNMENT" ]; then
    echo "ERROR: Input file not found: $INPUT_ALIGNMENT"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"

# Convert FASTA alignment to PHYLIP format (required by PhyloBayes)
python3 -c "
import sys
identifiers___sequences = {}
current_identifier = None
with open( sys.argv[1] ) as f:
    for line in f:
        line = line.strip()
        if line.startswith( '>' ):
            current_identifier = line[1:].split()[0]
            identifiers___sequences[ current_identifier ] = ''
        elif current_identifier:
            identifiers___sequences[ current_identifier ] += line
sequence_count = len( identifiers___sequences )
alignment_length = len( next( iter( identifiers___sequences.values() ) ) )
print( f'{sequence_count} {alignment_length}' )
for identifier in identifiers___sequences:
    sequence = identifiers___sequences[ identifier ]
    print( f'{identifier}  {sequence}' )
" "$INPUT_ALIGNMENT" > "${OUTPUT_DIR}/alignment.phy"

echo "Converted FASTA to PHYLIP format: ${OUTPUT_DIR}/alignment.phy"

# Run two independent MCMC chains for convergence assessment
cd "$OUTPUT_DIR"

echo "Starting PhyloBayes chain 1 (${GENERATIONS} generations)..."
pb -d alignment.phy ${MODEL_FLAGS} -x ${EVERY} ${GENERATIONS} chain1 &

echo "Starting PhyloBayes chain 2 (${GENERATIONS} generations)..."
pb -d alignment.phy ${MODEL_FLAGS} -x ${EVERY} ${GENERATIONS} chain2 &

echo "Waiting for both chains to complete..."
wait

echo "Chains complete. Assessing convergence..."

# Assess convergence between chains
bpcomp -x ${BURNIN} ${EVERY} chain1 chain2 2>&1 | tee bpcomp_report.txt
tracecomp -x ${BURNIN} ${EVERY} chain1 chain2 2>&1 | tee tracecomp_report.txt

# Check for consensus tree
if [ -f "bpcomp.con.tre" ]; then
    cp bpcomp.con.tre "$OUTPUT_TREE_NAME"
    echo "PhyloBayes complete: ${OUTPUT_DIR}/${OUTPUT_TREE_NAME}"
    echo "Convergence reports: bpcomp_report.txt, tracecomp_report.txt"
else
    echo "ERROR: PhyloBayes consensus tree not generated."
    echo "Check chain convergence in bpcomp_report.txt and tracecomp_report.txt"
    exit 1
fi

cd ..
