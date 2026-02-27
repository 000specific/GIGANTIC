#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 26 | Purpose: SLURM job for BUSCO proteome evaluation
# Human: Eric Edsinger

#SBATCH --job-name=genomesDB_BUSCO
#SBATCH --account=moroz
#SBATCH --qos=moroz
#SBATCH --mem=64gb
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=25
#SBATCH --output=slurm_logs/BUSCO_evaluation-%j.log

# =============================================================================
# GIGANTIC genomesDB - STEP_2 BUSCO Evaluation (SLURM)
# =============================================================================
#
# Runs BUSCO proteome completeness evaluation for all species.
# Uses 5 parallel BUSCO jobs, each with 5 CPUs (25 total).
#
# Usage:
#   cd workflow-RUN_01-standardize_evaluate_build_gigantic_genomesdb/
#   sbatch SLURM-004-busco_evaluation.sbatch
#
# =============================================================================

set -e

# Change to the directory where sbatch was invoked
# NOTE: We use SLURM_SUBMIT_DIR instead of BASH_SOURCE[0] because SLURM
# copies the script to a spool directory before execution, which breaks
# the BASH_SOURCE pattern. SLURM_SUBMIT_DIR is set to the original directory.
cd "${SLURM_SUBMIT_DIR}"

# Create log directory
mkdir -p slurm_logs

echo "========================================================================"
echo "GIGANTIC BUSCO Proteome Evaluation"
echo "========================================================================"
echo "SLURM Job ID: ${SLURM_JOB_ID}"
echo "Running on: $(hostname)"
echo "CPUs allocated: ${SLURM_CPUS_PER_TASK}"
echo "Working directory: $(pwd)"
echo "Start time: $(date)"
echo ""

# Load conda and activate environment
module load conda
conda activate ai_gigantic_genomesdb

# Verify BUSCO is available
echo "Checking BUSCO..."
busco --version
echo ""

# Run BUSCO evaluation script
# --parallel 5: Run 5 BUSCO jobs simultaneously
# Each BUSCO job will use 5 CPUs (5 x 5 = 25 CPUs total)
python3 ai/scripts/004_ai-python-run_busco_proteome_evaluation.py \
    --lineage-manifest INPUT_user/busco_lineages.txt \
    --input-proteomes OUTPUT_pipeline/1-output/gigantic_proteomes \
    --output-dir OUTPUT_pipeline/4-output \
    --parallel 5 \
    --cpus-per-job 5

echo ""
echo "========================================================================"
echo "BUSCO evaluation complete"
echo "End time: $(date)"
echo "SLURM Job ID: ${SLURM_JOB_ID}"
echo "========================================================================"
