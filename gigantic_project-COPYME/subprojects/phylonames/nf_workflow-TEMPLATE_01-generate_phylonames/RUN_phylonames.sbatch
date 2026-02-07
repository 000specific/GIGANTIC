#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 06 | Purpose: Run phylonames NextFlow pipeline on SLURM
# Human: Eric Edsinger

################################################################################
# GIGANTIC Phylonames Pipeline - SLURM Execution
################################################################################
#
# PURPOSE:
# Run the phylonames workflow on a SLURM cluster using NextFlow.
#
# USAGE:
#   sbatch RUN_phylonames.sbatch
#
# BEFORE RUNNING:
# 1. Edit the SBATCH directives below (account, qos) for your cluster
# 2. Edit phylonames_config.yaml with your project settings
# 3. Edit INPUT_user/species_list.txt with your species
#
# FOR LOCAL MACHINES:
# Use the local version instead:
#   bash RUN_phylonames.sh
#
################################################################################

#SBATCH --job-name=phylonames
#SBATCH --account=YOUR_ACCOUNT        # <-- EDIT: Your cluster account
#SBATCH --qos=YOUR_QOS                # <-- EDIT: Your quality of service
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8gb
#SBATCH --time=2:00:00
#SBATCH --output=slurm_logs/phylonames-%j.log

################################################################################
# SLURM JOB EXECUTION
################################################################################

echo "========================================================================"
echo "GIGANTIC Phylonames Pipeline (SLURM)"
echo "========================================================================"
echo ""
echo "Job ID: ${SLURM_JOB_ID}"
echo "Node: ${SLURM_NODELIST}"
echo "Started: $(date)"
echo ""

# Create slurm_logs directory if it doesn't exist
mkdir -p slurm_logs

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# Load required modules (adjust for your cluster)
module load conda 2>/dev/null || true

# Activate NextFlow environment
# Adjust the environment name for your setup
if conda activate ai_nextflow 2>/dev/null; then
    echo "Activated conda environment: ai_nextflow"
elif conda activate nextflow 2>/dev/null; then
    echo "Activated conda environment: nextflow"
else
    echo "WARNING: Could not activate NextFlow conda environment"
    echo "Assuming NextFlow is available in PATH"
fi

# Check for species list
if [ ! -f "INPUT_user/species_list.txt" ]; then
    echo "ERROR: Species list not found at INPUT_user/species_list.txt"
    exit 1
fi

# Show species count
SPECIES_COUNT=$(grep -v "^#" INPUT_user/species_list.txt | grep -v "^$" | wc -l)
echo "Species in your list: ${SPECIES_COUNT}"
echo ""

# Run NextFlow pipeline
echo "Running NextFlow pipeline..."
echo ""

nextflow run main.nf

EXIT_CODE=$?

echo ""
echo "========================================================================"
if [ $EXIT_CODE -eq 0 ]; then
    echo "SUCCESS! Pipeline completed."
else
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "Check the logs above for error details."
fi
echo "========================================================================"
echo "Job completed: $(date)"

exit $EXIT_CODE
