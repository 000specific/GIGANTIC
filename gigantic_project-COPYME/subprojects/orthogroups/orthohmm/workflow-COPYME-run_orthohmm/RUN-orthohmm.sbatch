#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 27 | Purpose: SLURM wrapper for OrthoHMM workflow
# Human: Eric Edsinger

#SBATCH --job-name=orthohmm_workflow
#SBATCH --account=moroz
#SBATCH --qos=moroz
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=100
#SBATCH --mem=700gb
#SBATCH --time=200:00:00
#SBATCH --output=slurm_logs/orthohmm_workflow-%j.log

# =============================================================================
# GIGANTIC Orthogroups - OrthoHMM Workflow (SLURM)
# =============================================================================
#
# SLURM wrapper for running the OrthoHMM workflow on HiPerGator.
#
# Resource estimates (for ~70 species, ~1.5M proteins total):
#   - CPUs: 100 (OrthoHMM is parallelizable)
#   - Memory: 700GB (large HMM databases and intermediate files)
#   - Time: 200 hours (OrthoHMM is computationally intensive)
#
# Adjust resources based on your species count and proteome sizes.
#
# Usage:
#   cd workflow-COPYME-run_orthohmm/
#   sbatch RUN-orthohmm.sbatch
#
# =============================================================================

echo "========================================================================"
echo "GIGANTIC Orthogroups OrthoHMM Workflow (SLURM)"
echo "========================================================================"
echo ""
echo "Job ID: ${SLURM_JOB_ID}"
echo "Node: ${SLURMD_NODENAME}"
echo "CPUs: ${SLURM_CPUS_PER_TASK}"
echo "Memory: ${SLURM_MEM_PER_NODE}"
echo "Started: $(date)"
echo ""

# Create log directory if it doesn't exist
mkdir -p slurm_logs

# Load conda
module load conda

# Activate the orthogroups environment
conda activate ai_gigantic_orthogroups

# Verify environment
echo "Conda environment: ${CONDA_DEFAULT_ENV}"
echo "NextFlow version: $(nextflow -version 2>&1 | head -1 || echo 'version check failed')"
echo "OrthoHMM version: $(orthohmm --version 2>&1 || echo 'version check failed')"
echo ""

# Run the workflow (NextFlow handles resource allocation internally)
bash RUN-orthohmm.sh

EXIT_CODE=$?

echo ""
echo "========================================================================"
echo "Job completed: $(date)"
echo "Exit code: ${EXIT_CODE}"
echo "========================================================================"

exit $EXIT_CODE
