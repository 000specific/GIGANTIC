#!/bin/bash
#SBATCH --job-name=STEP3_phylogenetic_analysis
#SBATCH --output=slurm_logs/phylogenetic_analysis-%j.log
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=100
#SBATCH --mem=700gb
#SBATCH --time=100:00:00
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --qos=YOUR_QOS

# AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: SLURM wrapper for STEP_3 phylogenetic analysis
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_gene_families STEP_3 - Phylogenetic Analysis (SLURM)
################################################################################
#
# PURPOSE:
# Submit the STEP_3 phylogenetic analysis workflow as a SLURM job.
# This is a thin wrapper that calls the local runner script.
#
# USAGE:
#   sbatch RUN-workflow.sbatch
#
# BEFORE RUNNING:
# 1. Edit the --account and --qos lines above to match your SLURM account
# 2. Ensure STEP_2 has completed
# 3. Edit phylogenetic_analysis_config.yaml with your settings
#
# NOTE: MAFFT, IQ-TREE, and PhyloBayes may need significant resources.
# Default: 100 CPUs, 700 GB RAM, 100 hours. Adjust as needed.
#
################################################################################

# Create log directory
mkdir -p slurm_logs

# Run the local runner script
bash RUN-workflow.sh
