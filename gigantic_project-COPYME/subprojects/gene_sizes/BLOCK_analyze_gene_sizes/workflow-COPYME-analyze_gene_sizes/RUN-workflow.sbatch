#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: SLURM wrapper for gene_sizes analysis workflow
# Human: Eric Edsinger

################################################################################
# GIGANTIC gene_sizes - Analyze Gene Sizes (SLURM)
################################################################################
#
# PURPOSE:
# SLURM wrapper that submits RUN-workflow.sh as a cluster job.
# Edit the SBATCH headers below for your cluster account and resources.
#
# USAGE:
#   sbatch RUN-workflow.sbatch
#
# BEFORE RUNNING:
# 1. Edit --account and --qos for your cluster
# 2. Ensure gene_sizes_config.yaml is configured
# 3. Provide per-species gene structure TSV files in INPUT_user/
# 4. Copy GIGANTIC species list to INPUT_user/gigantic_species_list.txt
#
################################################################################

#SBATCH --job-name=gigantic_gene_sizes
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --qos=YOUR_QOS
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16gb
#SBATCH --time=4:00:00
#SBATCH --output=slurm_logs/gene_sizes-%j.log

# Create slurm logs directory
mkdir -p slurm_logs

echo "SLURM Job ID: ${SLURM_JOB_ID}"
echo "Running on: $(hostname)"
echo "Started: $(date)"
echo ""

# Run the workflow
bash RUN-workflow.sh

EXIT_CODE=$?

echo ""
echo "SLURM job completed with exit code: ${EXIT_CODE}"
echo "Finished: $(date)"

exit $EXIT_CODE
