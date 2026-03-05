#!/bin/bash
#SBATCH --job-name=gigantic_trees_species
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --qos=YOUR_QOS
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=15gb
#SBATCH --time=2:00:00
#SBATCH --output=slurm_logs/trees_species-%j.log

# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: SLURM wrapper for trees_species workflow
# Human: Eric Edsinger

mkdir -p slurm_logs
bash RUN-workflow.sh
