#!/bin/bash
#SBATCH --job-name=MAFFT
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=ericedsinger@whitney.ufl.edu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=40
#SBATCH --mem=280gb
#SBATCH --time=100:00:00
#SBATCH --output=slurm-003-mafft-%j.log
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --qos=YOUR_QOS

# GIGANTIC BLOCK 3 - Script 003: Run MAFFT Alignment
# AI: Claude Code | Sonnet 4.5 | 2025 November 07 03:55 | Purpose: MAFFT multiple sequence alignment
# Human: Eric Edsinger

pwd; hostname; date
echo "Running MAFFT alignment on $SLURM_CPUS_ON_NODE CPU cores"

# Activate conda environment
module load python
module load conda
conda activate mafft

# Parse arguments
HOMOLOG_ID=$1

if [ -z "$HOMOLOG_ID" ]; then
    echo "ERROR: HOMOLOG_ID not provided"
    echo "Usage: sbatch $0 HOMOLOG_ID"
    exit 1
fi

# Run MAFFT
mafft --originalseqonly --maxiterate 1000 --reorder --bl 45 --thread $SLURM_CPUS_ON_NODE \
    "output/2-${HOMOLOG_ID}.aa" > "output/3-${HOMOLOG_ID}.mafft"

echo "MAFFT alignment complete: output/3-${HOMOLOG_ID}.mafft"
date

