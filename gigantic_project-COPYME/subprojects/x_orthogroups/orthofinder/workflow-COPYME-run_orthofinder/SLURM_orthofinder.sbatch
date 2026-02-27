#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 26 | Purpose: SLURM wrapper for OrthoFinder
# Human: Eric Edsinger

#SBATCH --job-name=orthofinder
#SBATCH --mail-type=ALL
#SBATCH --mail-user=YOUR_EMAIL@ufl.edu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=128
#SBATCH --mem=500gb
#SBATCH --time=120:00:00
#SBATCH --output=slurm_logs/orthofinder-%j.log
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --qos=YOUR_QOS

################################################################################
# GIGANTIC OrthoFinder Workflow - SLURM Wrapper
################################################################################
#
# BEFORE RUNNING:
# 1. Edit --mail-user with your email
# 2. Edit --account with your SLURM account
# 3. Edit --qos with your QOS
#
# USAGE:
#   sbatch SLURM_orthofinder.sbatch
#
# RESOURCES:
#   - 128 CPUs (one full node)
#   - 500 GB RAM
#   - 120 hours (5 days) - adjust based on species count
#
# ESTIMATED TIME:
#   - 67 species: ~4-7 days with diamond_ultra_sens
#   - Fewer species will be faster
#
################################################################################

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create slurm logs directory
mkdir -p "${SCRIPT_DIR}/slurm_logs"

# Print job info
echo "========================================================================"
echo "SLURM Job Information"
echo "========================================================================"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "CPUs: $SLURM_CPUS_ON_NODE"
echo "Start: $(date)"
echo "========================================================================"
echo ""

# Run the workflow
bash "${SCRIPT_DIR}/RUN_orthofinder.sh"

echo ""
echo "========================================================================"
echo "Job Complete: $(date)"
echo "========================================================================"
