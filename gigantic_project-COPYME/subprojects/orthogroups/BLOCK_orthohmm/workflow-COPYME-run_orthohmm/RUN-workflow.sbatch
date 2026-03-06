#!/bin/bash
#SBATCH --job-name=orthohmm_orthogroups
#SBATCH --account=YOUR_ACCOUNT        # <-- EDIT: your SLURM account
#SBATCH --qos=YOUR_QOS                # <-- EDIT: your SLURM QOS
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=100            # <-- EDIT: match orthohmm.cpus in START_HERE config
#SBATCH --mem=750gb                    # <-- EDIT: match orthohmm.memory in START_HERE config
#SBATCH --time=72:00:00
#SBATCH --output=slurm_logs/orthohmm-%j.log

# AI: Claude Code | Opus 4.6 | 2026 March 06 | Purpose: SLURM wrapper for OrthoHMM pipeline
# Human: Eric Edsinger

################################################################################
# GIGANTIC Orthogroups - BLOCK OrthoHMM - SLURM Execution
################################################################################
#
# PURPOSE:
# Submit the OrthoHMM workflow as a SLURM job.
# This is a thin wrapper - all workflow logic is in RUN-workflow.sh.
#
# USAGE:
#   sbatch RUN-workflow.sbatch
#
# BEFORE RUNNING:
# 1. Edit START_HERE-user_config.yaml (cpus, memory, proteomes path)
# 2. Edit the SBATCH directives above (account, qos, cpus, mem)
# 3. Ensure cpus-per-task and mem match your START_HERE config values
#
# FOR LOCAL MACHINES:
#   bash RUN-workflow.sh
#
################################################################################

mkdir -p slurm_logs
bash RUN-workflow.sh
