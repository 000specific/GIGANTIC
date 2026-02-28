#!/bin/bash
#SBATCH --job-name=IQTREE
#SBATCH --mail-type=END,FAIL
#SBATCH --mail-user=ericedsinger@whitney.ufl.edu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=40
#SBATCH --mem=280gb
#SBATCH --time=100:00:00
#SBATCH --output=slurm-005_b-iqtree-%j.log
#SBATCH --account=moroz
#SBATCH --qos=moroz

# GIGANTIC STEP_3 - Script 005_b: Run IQ-TREE
# AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: IQ-TREE ML phylogenetic inference (publication-quality)
# Human: Eric Edsinger

pwd; hostname; date
echo "Running IQ-TREE on $SLURM_CPUS_ON_NODE CPU cores"

# Activate conda environment
module load python
module load conda
conda activate ai_gigantic_trees

# Parse arguments
HOMOLOG_ID=$1

if [ -z "$HOMOLOG_ID" ]; then
    echo "ERROR: HOMOLOG_ID not provided"
    echo "Usage: sbatch $0 HOMOLOG_ID"
    exit 1
fi

# Run IQ-TREE
iqtree -s "output/4-${HOMOLOG_ID}.clipkit-smartgap" \
    -m MFP \
    --prefix "output/5_b-${HOMOLOG_ID}" \
    --rate \
    -B 2000 \
    -alrt 2000 \
    -T AUTO \
    -bnni

echo "IQ-TREE complete: output/5_b-${HOMOLOG_ID}.treefile"
date
