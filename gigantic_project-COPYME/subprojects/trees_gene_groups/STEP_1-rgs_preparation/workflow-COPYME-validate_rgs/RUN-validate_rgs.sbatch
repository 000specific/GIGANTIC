#!/bin/bash
#SBATCH --job-name=STEP1_validate_rgs
#SBATCH --output=slurm_logs/validate_rgs-%j.log
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8gb
#SBATCH --time=1:00:00
#SBATCH --account=moroz
#SBATCH --qos=moroz

# AI: Claude Code | Opus 4.6 | 2026 February 27 | Purpose: SLURM wrapper for STEP_1 RGS validation
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_gene_families STEP_1 - RGS Validation (SLURM)
################################################################################
#
# PURPOSE:
# Submit the STEP_1 RGS validation workflow as a SLURM job.
#
# USAGE:
#   sbatch RUN-validate_rgs.sbatch
#
################################################################################

mkdir -p slurm_logs
bash RUN-validate_rgs.sh
