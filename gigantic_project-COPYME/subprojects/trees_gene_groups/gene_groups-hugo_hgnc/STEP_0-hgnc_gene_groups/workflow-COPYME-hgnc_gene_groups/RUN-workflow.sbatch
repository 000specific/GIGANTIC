#!/bin/bash
#SBATCH --job-name=hgnc_gene_groups
#SBATCH --output=slurm_logs/hgnc_gene_groups-%j.log
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16gb
#SBATCH --time=1:00:00
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --qos=YOUR_QOS

# AI: Claude Code | Opus 4.6 | 2026 March 30 | Purpose: SLURM wrapper for STEP_0 HGNC gene group RGS generation
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_gene_groups STEP_0 - HGNC Gene Group RGS Generation (SLURM)
################################################################################
#
# ALTERNATIVE SLURM wrapper - submits RUN-workflow.sh as a SLURM job.
#
# NOTE: RUN-workflow.sh also supports SLURM auto-submit when
# execution_mode: "slurm" is set in START_HERE-user_config.yaml.
# This sbatch file is an alternative for direct sbatch submission.
#
# USAGE:
#   sbatch RUN-workflow.sbatch
#
# BEFORE RUNNING:
#   Edit the #SBATCH lines above (account, qos) for your cluster.
#
################################################################################

mkdir -p slurm_logs
bash RUN-workflow.sh
