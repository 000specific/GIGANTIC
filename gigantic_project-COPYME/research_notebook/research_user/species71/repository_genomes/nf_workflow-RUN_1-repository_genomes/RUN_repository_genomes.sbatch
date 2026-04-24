#!/bin/bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Run repository genomes pipeline on SLURM
# Human: Eric Edsinger

################################################################################
# Repository Genomes Pipeline - SLURM Execution
################################################################################
#
# USAGE:
#   sbatch RUN_repository_genomes.sbatch
#
# BEFORE RUNNING:
# 1. Edit the SBATCH directives below (account, qos) for your cluster
#
# FOR LOCAL MACHINES:
#   bash RUN_repository_genomes.sh
#
################################################################################

#SBATCH --job-name=repository_genomes
#SBATCH --account=moroz
#SBATCH --qos=moroz
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=30gb
#SBATCH --time=8:00:00
#SBATCH --output=slurm_logs/repository_genomes-%j.log

################################################################################
# SLURM JOB EXECUTION
################################################################################

echo "========================================================================"
echo "Repository Genomes Pipeline (SLURM)"
echo "========================================================================"
echo ""
echo "Job ID: ${SLURM_JOB_ID}"
echo "Node: ${SLURM_NODELIST}"
echo "Started: $(date)"
echo ""

# Create slurm_logs directory if it doesn't exist
mkdir -p slurm_logs

# Change to the directory where sbatch was invoked
cd "${SLURM_SUBMIT_DIR}"
echo "Working directory: $(pwd)"

# Load required modules (adjust for your cluster)
module load conda 2>/dev/null || true
module load gffread 2>/dev/null || true

# Activate NextFlow environment
if conda activate ai_nextflow 2>/dev/null; then
    echo "Activated conda environment: ai_nextflow"
elif conda activate nextflow 2>/dev/null; then
    echo "Activated conda environment: nextflow"
else
    echo "WARNING: Could not activate NextFlow conda environment"
    echo "Assuming NextFlow is available in PATH"
fi

echo "NextFlow: $(which nextflow 2>/dev/null || echo 'NOT FOUND')"
echo "python3:  $(which python3 2>/dev/null || echo 'NOT FOUND')"
echo "gffread:  $(which gffread 2>/dev/null || echo 'NOT FOUND')"
echo "CWD after conda: $(pwd)"
echo ""

# Ensure NextFlow can initialize
mkdir -p .nextflow

# Run NextFlow pipeline
echo "Running NextFlow pipeline..."
echo ""

nextflow run ai/main.nf

EXIT_CODE=$?

echo ""

echo "========================================================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "SUCCESS! Pipeline completed."
    echo ""
    echo "T1 proteomes: OUTPUT_pipeline/3-output/T1_proteomes/"
    echo ""
    echo "Species processed:"
    ls OUTPUT_pipeline/3-output/T1_proteomes/*.aa 2>/dev/null | while read f; do
        echo "  $(basename $f): $(grep -c '^>' $f) proteins"
    done
else
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "Check the logs above for error details."
fi
echo "========================================================================"
echo "Job completed: $(date)"

exit $EXIT_CODE
