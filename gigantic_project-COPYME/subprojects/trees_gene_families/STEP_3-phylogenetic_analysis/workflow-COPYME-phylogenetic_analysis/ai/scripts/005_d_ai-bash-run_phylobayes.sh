#!/bin/bash
# GIGANTIC STEP_3 - Script 005_d: Run PhyloBayes
# AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: PhyloBayes Bayesian phylogenetic inference
# Human: Eric Edsinger
#
# PhyloBayes uses site-heterogeneous CAT-GTR models and MCMC sampling.
# Runs 2 independent chains for convergence assessment using bpcomp/tracecomp.
# Very slow (days to weeks) - use as Bayesian counterpoint to ML methods.
#
# Requires: phylobayes (pb), bpcomp, tracecomp
# Input: ClipKit-trimmed alignment (FASTA format, converted to PHYLIP internally)
# Output: Consensus tree in Newick format

# Activate conda environment
module load python
module load conda
conda activate ai_gigantic_trees_gene_families

# Parse arguments
HOMOLOG_ID=$1
GENERATIONS=${2:-10000}
BURNIN=${3:-2500}

if [ -z "$HOMOLOG_ID" ]; then
    echo "Usage: $0 HOMOLOG_ID [GENERATIONS] [BURNIN]"
    echo "Example: $0 ags-species67_T1-species67-innexin_pannexin 10000 2500"
    exit 1
fi

INPUT_FASTA="output/4-${HOMOLOG_ID}.clipkit-smartgap"
OUTPUT_DIR="output/5_d-output"
mkdir -p ${OUTPUT_DIR}

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
" ${INPUT_FASTA} > ${OUTPUT_DIR}/alignment.phy

echo "Converted FASTA to PHYLIP format: ${OUTPUT_DIR}/alignment.phy"

# Run two independent MCMC chains for convergence assessment
cd ${OUTPUT_DIR}

echo "Starting PhyloBayes chain 1 (${GENERATIONS} generations)..."
pb -d alignment.phy -cat -gtr -x 1 ${GENERATIONS} chain1 &

echo "Starting PhyloBayes chain 2 (${GENERATIONS} generations)..."
pb -d alignment.phy -cat -gtr -x 1 ${GENERATIONS} chain2 &

echo "Waiting for both chains to complete..."
wait

echo "Chains complete. Assessing convergence..."

# Assess convergence between chains
bpcomp -x ${BURNIN} 1 chain1 chain2 2>&1 | tee bpcomp_report.txt || true
tracecomp -x ${BURNIN} 1 chain1 chain2 2>&1 | tee tracecomp_report.txt || true

# Check for consensus tree
if [ -f "bpcomp.con.tre" ]; then
    cp bpcomp.con.tre "5_d-${HOMOLOG_ID}.phylobayes.nwk"
    echo "PhyloBayes complete: ${OUTPUT_DIR}/5_d-${HOMOLOG_ID}.phylobayes.nwk"
    echo "Convergence reports: bpcomp_report.txt, tracecomp_report.txt"
else
    echo "ERROR: PhyloBayes consensus tree not generated."
    echo "Check chain convergence in bpcomp_report.txt and tracecomp_report.txt"
    exit 1
fi

cd ..
