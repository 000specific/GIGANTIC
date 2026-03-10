#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 10 | Purpose: Set up STEP_2 phylogenetic analysis workflow directories and submit burst jobs
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_gene_families - STEP_2 Burst Setup & Submission
################################################################################
#
# PURPOSE:
# For each gene_family-[name]/ directory with completed STEP_1:
#   1. Create workflow-RUN_1-phylogenetic_analysis from COPYME
#   2. Configure START_HERE-user_config.yaml with gene family name
#   3. Submit SLURM job for STEP_2 phylogenetic analysis
#
# PREREQUISITES:
#   - STEP_1 (homolog discovery) must have completed successfully
#   - AGS FASTA files must exist in output_to_input/STEP_1-homolog_discovery/
#
# USAGE:
#   bash RUN-setup_and_submit_step2_burst.sh [OPTIONS]
#
# OPTIONS:
#   --dry-run       Show what would be done without making changes
#   --setup-only    Set up directories but don't submit jobs
#   --submit-only   Submit jobs for already-set-up directories
#   --help          Show this help message
#
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory (subproject root)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# Paths
CONDA_ENV="ai_gigantic_trees_gene_families"

# SLURM settings for STEP_2 (phylogenetic analysis - alignment + tree building)
SLURM_ACCOUNT="moroz"
SLURM_QOS="moroz-b"
SLURM_MEM="64gb"
SLURM_TIME="24:00:00"
SLURM_CPUS="8"

# Options
DRY_RUN=false
SETUP_ONLY=false
SUBMIT_ONLY=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --setup-only)
            SETUP_ONLY=true
            shift
            ;;
        --submit-only)
            SUBMIT_ONLY=true
            shift
            ;;
        --help|-h)
            head -25 "$0" | grep -E "^#" | sed 's/^# //' | sed 's/^#//'
            exit 0
            ;;
        *)
            echo -e "${RED}ERROR: Unknown option: $1${NC}"
            echo "Use --help to see available options."
            exit 1
            ;;
    esac
done

echo "========================================================================"
echo "GIGANTIC trees_gene_families - STEP_2 Burst Setup & Submission"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo "SLURM: ${SLURM_CPUS} CPUs, ${SLURM_MEM} RAM, ${SLURM_TIME}"
echo ""

if $DRY_RUN; then
    echo -e "${BLUE}DRY RUN MODE - No changes will be made${NC}"
    echo ""
fi

# Create slurm_logs directory
mkdir -p "${SCRIPT_DIR}/slurm_logs"

# Track counts
setup_count=0
submit_count=0
skip_count=0
error_count=0
no_step1_count=0

# Find all gene_family-* directories
for FAMILY_DIR in "${SCRIPT_DIR}"/gene_family-*/; do
    [ -d "$FAMILY_DIR" ] || continue

    gene_family=$(basename "$FAMILY_DIR" | sed 's/^gene_family-//')

    STEP2_COPYME="${FAMILY_DIR}/STEP_2-phylogenetic_analysis/workflow-COPYME-phylogenetic_analysis"
    STEP2_WORKFLOW="${FAMILY_DIR}/STEP_2-phylogenetic_analysis/workflow-RUN_1-phylogenetic_analysis"

    echo "----------------------------------------"
    echo "Gene family: ${gene_family}"

    # Check STEP_2 COPYME template exists
    if [ ! -d "${STEP2_COPYME}" ]; then
        echo -e "  ${RED}ERROR: STEP_2 COPYME template not found${NC}"
        error_count=$((error_count + 1))
        continue
    fi

    # Check STEP_1 completed (AGS file exists in output_to_input)
    AGS_DIR="${FAMILY_DIR}/output_to_input/STEP_1-homolog_discovery/ags_fastas/${gene_family}"
    if [ ! -d "${AGS_DIR}" ]; then
        echo -e "  ${YELLOW}STEP_1 not completed yet (no output_to_input), skipping${NC}"
        no_step1_count=$((no_step1_count + 1))
        continue
    fi

    # ========================================================================
    # SETUP PHASE
    # ========================================================================
    if ! $SUBMIT_ONLY; then
        if [ -d "${STEP2_WORKFLOW}" ]; then
            echo -e "  ${YELLOW}workflow-RUN_1 exists, skipping setup${NC}"
            skip_count=$((skip_count + 1))
        else
            if $DRY_RUN; then
                echo -e "  ${BLUE}[DRY RUN] Would create workflow-RUN_1-phylogenetic_analysis${NC}"
            else
                # 1. Copy COPYME to RUN_1
                cp -r "${STEP2_COPYME}" "${STEP2_WORKFLOW}"

                # 2. Update config YAML - gene family name
                CONFIG_FILE="${STEP2_WORKFLOW}/START_HERE-user_config.yaml"
                sed -i "s|name: \"innexin_pannexin\"|name: \"${gene_family}\"|" "${CONFIG_FILE}"

                echo -e "  ${GREEN}Created and configured STEP_2 workflow${NC}"
                setup_count=$((setup_count + 1))
            fi
        fi
    fi

    # ========================================================================
    # SUBMIT PHASE
    # ========================================================================
    if ! $SETUP_ONLY; then
        if [ ! -d "${STEP2_WORKFLOW}" ]; then
            echo -e "  ${YELLOW}Workflow directory not found, skipping submit${NC}"
            continue
        fi

        if $DRY_RUN; then
            echo -e "  ${BLUE}[DRY RUN] Would submit SLURM job for STEP_2${NC}"
            submit_count=$((submit_count + 1))
        else
            JOB_NAME="step2_${gene_family}"
            sbatch \
                --job-name="${JOB_NAME}" \
                --account="${SLURM_ACCOUNT}" \
                --qos="${SLURM_QOS}" \
                --mem="${SLURM_MEM}" \
                --time="${SLURM_TIME}" \
                --cpus-per-task="${SLURM_CPUS}" \
                --output="${SCRIPT_DIR}/slurm_logs/step2_${gene_family}-%j.log" \
                --wrap="module load conda 2>/dev/null || true; conda activate ${CONDA_ENV} || { echo 'ERROR: Failed to activate conda environment ${CONDA_ENV}'; exit 1; }; cd ${STEP2_WORKFLOW} && bash RUN-workflow.sh"

            submit_count=$((submit_count + 1))
        fi
    fi
done

# Summary
echo ""
echo "========================================================================"
if $DRY_RUN; then
    echo -e "${BLUE}DRY RUN SUMMARY${NC}"
else
    echo -e "${GREEN}SUMMARY${NC}"
fi
if ! $SUBMIT_ONLY; then
    echo "Set up: ${setup_count}"
    echo "Skipped (already exist): ${skip_count}"
fi
if ! $SETUP_ONLY; then
    echo "Jobs submitted: ${submit_count}"
fi
echo "Waiting for STEP_1: ${no_step1_count}"
echo "Errors: ${error_count}"
echo "SLURM resources per job: ${SLURM_CPUS} CPUs, ${SLURM_MEM} RAM, ${SLURM_TIME}"
echo "========================================================================"
echo ""
echo "Completed: $(date)"
