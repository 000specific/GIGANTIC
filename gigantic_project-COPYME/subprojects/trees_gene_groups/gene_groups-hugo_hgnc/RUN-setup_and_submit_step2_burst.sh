#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 31 15:45 | Purpose: Set up STEP_2 phylogenetic analysis workflow directories and submit burst jobs for HGNC gene groups
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_gene_groups (HGNC) - STEP_2 Burst Setup & Submission
################################################################################
#
# PURPOSE:
# For each gene_group-[name]/ directory with completed STEP_1:
#   1. Create gene_group-[name]/ directory inside STEP_2-phylogenetic_analysis/
#   2. Copy workflow-COPYME-phylogenetic_analysis -> workflow-RUN_01-phylogenetic_analysis
#   3. Configure START_HERE-user_config.yaml with gene group name
#   4. Submit SLURM job for STEP_2 phylogenetic analysis
#
# PREREQUISITES:
#   - STEP_1 (homolog discovery) must have completed successfully
#   - AGS FASTA files must exist in output_to_input/gene_groups-hugo_hgnc/STEP_1-homolog_discovery/
#
# USAGE:
#   bash RUN-setup_and_submit_step2_burst.sh [OPTIONS]
#
# OPTIONS:
#   --dry-run         Show what would be done without making changes
#   --setup-only      Set up directories but don't submit jobs
#   --submit-only     Submit jobs for already-set-up directories
#   --gene-group NAME Process only this specific gene group (sanitized name)
#   --help            Show this help message
#
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory (gene_groups-hugo_hgnc/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Paths
# ============================================================================

# STEP_1 completed outputs (AGS files)
STEP1_OTI="${SCRIPT_DIR}/../output_to_input/gene_groups-hugo_hgnc/STEP_1-homolog_discovery"

# STEP_2 template and target directory
STEP2_DIR="${SCRIPT_DIR}/STEP_2-phylogenetic_analysis"
STEP2_COPYME="${STEP2_DIR}/workflow-COPYME-phylogenetic_analysis"

# Conda environment
CONDA_ENV="ai_gigantic_trees_gene_families"

# ============================================================================
# SLURM settings for STEP_2 (phylogenetic analysis - alignment + tree building)
# ============================================================================
SLURM_ACCOUNT="moroz"
SLURM_QOS="moroz-b"
SLURM_MEM="64gb"
SLURM_TIME="96:00:00"
SLURM_CPUS="8"

# ============================================================================
# Options
# ============================================================================
DRY_RUN=false
SETUP_ONLY=false
SUBMIT_ONLY=false
SINGLE_GENE_GROUP=""

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
        --gene-group)
            SINGLE_GENE_GROUP="$2"
            shift 2
            ;;
        --help|-h)
            head -30 "$0" | grep -E "^#" | sed 's/^# //' | sed 's/^#//'
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
echo "GIGANTIC trees_gene_groups (HGNC) - STEP_2 Burst Setup & Submission"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo "SLURM: ${SLURM_CPUS} CPUs, ${SLURM_MEM} RAM, ${SLURM_TIME}"
if [ -n "${SINGLE_GENE_GROUP}" ]; then
    echo "Filter: single gene group '${SINGLE_GENE_GROUP}'"
fi
echo ""

if $DRY_RUN; then
    echo -e "${BLUE}DRY RUN MODE - No changes will be made${NC}"
    echo ""
fi

# ============================================================================
# Validate prerequisites
# ============================================================================

if [ ! -d "${STEP2_COPYME}" ]; then
    echo -e "${RED}ERROR: STEP_2 workflow COPYME template not found!${NC}"
    echo "Expected at: ${STEP2_COPYME}"
    exit 1
fi

if [ ! -d "${STEP1_OTI}" ]; then
    echo -e "${RED}ERROR: STEP_1 output_to_input directory not found!${NC}"
    echo "Expected at: ${STEP1_OTI}"
    echo "STEP_1 must complete before running STEP_2."
    exit 1
fi

# Create slurm_logs directory at the STEP_2 level
mkdir -p "${STEP2_DIR}/slurm_logs"

# ============================================================================
# Iterate over completed STEP_1 gene groups
# ============================================================================
# Look for gene_group-* directories in the STEP_1 output_to_input that contain
# AGS FASTA files (indicating STEP_1 completed successfully).

# Track counts
setup_count=0
submit_count=0
skip_count=0
error_count=0
no_ags_count=0
total_count=0

for STEP1_GENE_GROUP_DIR in "${STEP1_OTI}"/gene_group-*/; do
    [ -d "$STEP1_GENE_GROUP_DIR" ] || continue

    gene_group_dir_name=$(basename "$STEP1_GENE_GROUP_DIR")
    sanitized_name="${gene_group_dir_name#gene_group-}"
    total_count=$((total_count + 1))

    # Apply single gene group filter
    if [ -n "${SINGLE_GENE_GROUP}" ] && [ "${sanitized_name}" != "${SINGLE_GENE_GROUP}" ]; then
        continue
    fi

    echo "----------------------------------------"
    echo "Gene group: ${sanitized_name}"

    # Check AGS file exists (STEP_1 completed)
    AGS_FILE=$(find -L "${STEP1_GENE_GROUP_DIR}" -name "*.aa" 2>/dev/null | head -1)
    if [ -z "${AGS_FILE}" ]; then
        echo -e "  ${YELLOW}No AGS file found in output_to_input, skipping${NC}"
        no_ags_count=$((no_ags_count + 1))
        continue
    fi

    ags_seq_count=$(grep -c '^>' "${AGS_FILE}")
    echo "  AGS sequences: ${ags_seq_count}"

    # --- Paths for this gene group ---
    GENE_GROUP_DIR="${STEP2_DIR}/${gene_group_dir_name}"
    WORKFLOW_RUN="${GENE_GROUP_DIR}/workflow-RUN_01-phylogenetic_analysis"

    # ====================================================================
    # SETUP PHASE
    # ====================================================================
    if ! $SUBMIT_ONLY; then
        if [ -d "${WORKFLOW_RUN}" ]; then
            echo -e "  ${YELLOW}workflow-RUN_01 exists, skipping setup${NC}"
            skip_count=$((skip_count + 1))
        else
            if $DRY_RUN; then
                echo -e "  ${BLUE}[DRY RUN] Would create: ${gene_group_dir_name}/workflow-RUN_01-phylogenetic_analysis${NC}"
                setup_count=$((setup_count + 1))
            else
                # 1. Create gene_group directory and copy workflow template
                mkdir -p "${GENE_GROUP_DIR}"
                cp -r "${STEP2_COPYME}" "${WORKFLOW_RUN}"

                # 2. Update config YAML - gene family name
                CONFIG_FILE="${WORKFLOW_RUN}/START_HERE-user_config.yaml"
                sed -i "s|name: \"innexin_pannexin\"|name: \"${sanitized_name}\"|" "${CONFIG_FILE}"

                echo -e "  ${GREEN}Created and configured STEP_2 workflow${NC}"
                setup_count=$((setup_count + 1))
            fi
        fi
    fi

    # ====================================================================
    # SUBMIT PHASE
    # ====================================================================
    if ! $SETUP_ONLY; then
        if ! $DRY_RUN && [ ! -d "${WORKFLOW_RUN}" ]; then
            echo -e "  ${YELLOW}Workflow directory not found, skipping submit${NC}"
            continue
        fi

        if $DRY_RUN; then
            echo -e "  ${BLUE}[DRY RUN] Would submit SLURM job for STEP_2${NC}"
            submit_count=$((submit_count + 1))
        else
            JOB_NAME="s2_hgnc_${sanitized_name}"
            # Truncate job name to 64 chars (SLURM limit)
            JOB_NAME="${JOB_NAME:0:64}"

            sbatch \
                --job-name="${JOB_NAME}" \
                --account="${SLURM_ACCOUNT}" \
                --qos="${SLURM_QOS}" \
                --mem="${SLURM_MEM}" \
                --time="${SLURM_TIME}" \
                --cpus-per-task="${SLURM_CPUS}" \
                --output="${STEP2_DIR}/slurm_logs/step2_${sanitized_name}-%j.log" \
                --wrap="module load conda 2>/dev/null || true; conda activate ${CONDA_ENV} || { echo 'ERROR: Failed to activate conda environment ${CONDA_ENV}'; exit 1; }; cd ${WORKFLOW_RUN} && bash RUN-workflow.sh"

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
echo "STEP_1 completed gene groups found: ${total_count}"
if ! $SUBMIT_ONLY; then
    echo "Set up: ${setup_count}"
    echo "Skipped (already exist): ${skip_count}"
fi
if ! $SETUP_ONLY; then
    echo "Jobs submitted: ${submit_count}"
fi
echo "No AGS file: ${no_ags_count}"
echo "Errors: ${error_count}"
echo "SLURM resources per job: ${SLURM_CPUS} CPUs, ${SLURM_MEM} RAM, ${SLURM_TIME}"
echo ""
echo "SLURM logs: ${STEP2_DIR}/slurm_logs/"
echo "========================================================================"
echo ""
echo "Completed: $(date)"
