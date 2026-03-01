#!/bin/bash
#SBATCH --job-name=broccoli_orthogroups
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --qos=YOUR_QOS
#SBATCH --mem=8gb
#SBATCH --cpus-per-task=1
#SBATCH --time=96:00:00
#SBATCH --output=slurm_logs/broccoli-%j.log

# AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: SLURM wrapper for Broccoli pipeline
# Human: Eric Edsinger

module load conda
conda activate ai_gigantic_orthogroups
module load nextflow

mkdir -p slurm_logs
bash RUN-workflow.sh
