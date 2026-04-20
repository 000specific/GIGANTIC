#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 April 20 | Purpose: Set up and submit STEP_2 phylogenetic analysis for HGNC gene groups
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_gene_groups (HGNC) - STEP_2 Burst Setup & Submission
################################################################################
#
# PURPOSE:
# For each gene group with completed STEP_1 (AGS file in output_to_input/),
# create a STEP_2 workflow directory and submit a phylogenetic analysis job.
#
# Two-tier resource strategy by AGS sequence count:
#   Small (<= 2000 AGS seqs): burst QOS, 15 CPUs, 112GB, 96hr (4-day burst limit)
#   Large (>  2000 AGS seqs): standard QOS, 50 CPUs, 375GB, 336hr (2 weeks)
#
# Default tree methods: FastTree + IQ-TREE (both enabled)
#
# PREREQUISITES:
#   - STEP_1 homolog discovery complete (AGS files in output_to_input/)
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

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Paths
# ============================================================================

STEP1_OTI="${SCRIPT_DIR}/../output_to_input/gene_groups-hugo_hgnc/STEP_1-homolog_discovery"
STEP2_DIR="${SCRIPT_DIR}/STEP_2-phylogenetic_analysis"
STEP2_COPYME="${STEP2_DIR}/workflow-COPYME-phylogenetic_analysis"
CONDA_ENV="ai_gigantic_trees_gene_families"

# ============================================================================
# SLURM settings - two-tier based on AGS size
# ============================================================================
SLURM_ACCOUNT="moroz"
LARGE_AGS_THRESHOLD=2000  # AGS sequence count threshold

# Small (<= threshold): burst QOS, 15 CPUs, 112GB, 4 days (burst max)
SLURM_QOS_SMALL="moroz-b"
SLURM_MEM_SMALL="112gb"
SLURM_TIME_SMALL="96:00:00"
SLURM_CPUS_SMALL="15"

# Large (> threshold): standard QOS, 50 CPUs, 375GB, 2 weeks
SLURM_QOS_LARGE="moroz"
SLURM_MEM_LARGE="375gb"
SLURM_TIME_LARGE="336:00:00"
SLURM_CPUS_LARGE="50"

# ============================================================================
# Options
# ============================================================================
DRY_RUN=false
SETUP_ONLY=false
SUBMIT_ONLY=false
SINGLE_GENE_GROUP=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true; shift ;;
        --setup-only) SETUP_ONLY=true; shift ;;
        --submit-only) SUBMIT_ONLY=true; shift ;;
        --gene-group) SINGLE_GENE_GROUP="$2"; shift 2 ;;
        --help|-h)
            head -33 "$0" | grep -E "^#" | sed 's/^# //' | sed 's/^#//'
            exit 0 ;;
        *)
            echo -e "${RED}ERROR: Unknown option: $1${NC}"
            exit 1 ;;
    esac
done

echo "========================================================================"
echo "GIGANTIC trees_gene_groups (HGNC) - STEP_2 Burst Setup & Submission"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""
echo "Two-tier SLURM strategy (by AGS sequence count):"
echo "  Small (<= ${LARGE_AGS_THRESHOLD} seqs): ${SLURM_CPUS_SMALL} CPUs, ${SLURM_MEM_SMALL}, ${SLURM_TIME_SMALL}, qos=${SLURM_QOS_SMALL}"
echo "  Large (>  ${LARGE_AGS_THRESHOLD} seqs): ${SLURM_CPUS_LARGE} CPUs, ${SLURM_MEM_LARGE}, ${SLURM_TIME_LARGE}, qos=${SLURM_QOS_LARGE}"
echo "Tree methods: FastTree + IQ-TREE (both enabled)"
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

if [ ! -d "${STEP1_OTI}" ]; then
    echo -e "${RED}ERROR: STEP_1 output_to_input not found: ${STEP1_OTI}${NC}"
    exit 1
fi

if [ ! -d "${STEP2_COPYME}" ]; then
    echo -e "${RED}ERROR: STEP_2 COPYME not found: ${STEP2_COPYME}${NC}"
    exit 1
fi

mkdir -p "${STEP2_DIR}/slurm_logs"

# ============================================================================
# Iterate over completed STEP_1 gene groups
# ============================================================================

setup_count=0
submit_count_small=0
submit_count_large=0
skip_count=0
error_count=0
total_count=0

for STEP1_GG_DIR in "${STEP1_OTI}"/gene_group-*/; do
    [ -d "$STEP1_GG_DIR" ] || continue

    gene_group_dir_name=$(basename "$STEP1_GG_DIR")
    sanitized_name="${gene_group_dir_name#gene_group-}"
    total_count=$((total_count + 1))

    # Apply single gene group filter
    if [ -n "${SINGLE_GENE_GROUP}" ] && [ "${sanitized_name}" != "${SINGLE_GENE_GROUP}" ]; then
        continue
    fi

    echo "----------------------------------------"
    echo "Gene group: ${sanitized_name}"

    # Check AGS exists
    AGS_FILE=$(find -L "${STEP1_GG_DIR}" -name "*.aa" 2>/dev/null | head -1)
    if [ -z "${AGS_FILE}" ]; then
        echo -e "  ${YELLOW}No AGS file; skipping${NC}"
        error_count=$((error_count + 1))
        continue
    fi

    ags_seq_count=$(grep -c '^>' "${AGS_FILE}")
    echo "  AGS sequences: ${ags_seq_count}"

    # Decide tier
    if [ "$ags_seq_count" -gt "$LARGE_AGS_THRESHOLD" ] 2>/dev/null; then
        tier="large"
        slurm_qos="${SLURM_QOS_LARGE}"
        slurm_mem="${SLURM_MEM_LARGE}"
        slurm_time="${SLURM_TIME_LARGE}"
        slurm_cpus="${SLURM_CPUS_LARGE}"
    else
        tier="small"
        slurm_qos="${SLURM_QOS_SMALL}"
        slurm_mem="${SLURM_MEM_SMALL}"
        slurm_time="${SLURM_TIME_SMALL}"
        slurm_cpus="${SLURM_CPUS_SMALL}"
    fi
    echo "  Tier: ${tier}"

    # Paths for this gene group
    GG_DIR="${STEP2_DIR}/gene_group-${sanitized_name}"
    WF="${GG_DIR}/workflow-RUN_01-phylogenetic_analysis"

    # ---- SETUP ----
    if ! $SUBMIT_ONLY; then
        if [ -d "${WF}" ]; then
            echo -e "  ${YELLOW}workflow-RUN_01 exists; skipping setup${NC}"
            skip_count=$((skip_count + 1))
        else
            if $DRY_RUN; then
                echo -e "  ${BLUE}[DRY RUN] Would create: ${WF}${NC}"
                setup_count=$((setup_count + 1))
            else
                mkdir -p "${GG_DIR}"
                cp -r "${STEP2_COPYME}" "${WF}"

                CONFIG="${WF}/START_HERE-user_config.yaml"
                # Set gene family name
                sed -i "s|name: \"innexin_pannexin\"|name: \"${sanitized_name}\"|" "${CONFIG}"
                # Enable iqtree (default is false)
                sed -i 's|^  iqtree: false|  iqtree: true|' "${CONFIG}"

                echo -e "  ${GREEN}Created and configured STEP_2 workflow${NC}"
                setup_count=$((setup_count + 1))
            fi
        fi
    fi

    # ---- SUBMIT ----
    if ! $SETUP_ONLY; then
        if ! $DRY_RUN && [ ! -d "${WF}" ]; then
            echo -e "  ${YELLOW}Workflow dir not found; skipping submit${NC}"
            continue
        fi

        if $DRY_RUN; then
            echo -e "  ${BLUE}[DRY RUN] Would submit (${tier}: ${slurm_cpus} CPUs, ${slurm_mem}, ${slurm_time}, qos=${slurm_qos})${NC}"
        else
            job_name="s2_hgnc_${sanitized_name:0:50}"
            sbatch \
                --job-name="${job_name}" \
                --account="${SLURM_ACCOUNT}" \
                --qos="${slurm_qos}" \
                --mem="${slurm_mem}" \
                --time="${slurm_time}" \
                --cpus-per-task="${slurm_cpus}" \
                --output="${STEP2_DIR}/slurm_logs/step2_${sanitized_name}-%j.log" \
                --wrap="module load conda 2>/dev/null || true; conda activate ${CONDA_ENV} || { echo 'FATAL'; exit 1; }; cd ${WF} && bash RUN-workflow.sh"
        fi

        if [ "$tier" = "large" ]; then
            submit_count_large=$((submit_count_large + 1))
        else
            submit_count_small=$((submit_count_small + 1))
        fi
    fi
done

# ============================================================================
# Summary
# ============================================================================
echo ""
echo "========================================================================"
if $DRY_RUN; then
    echo -e "${BLUE}DRY RUN SUMMARY${NC}"
else
    echo -e "${GREEN}SUMMARY${NC}"
fi
echo "Total gene groups with completed STEP_1: ${total_count}"
if ! $SUBMIT_ONLY; then
    echo "Set up: ${setup_count}"
    echo "Skipped (already exist): ${skip_count}"
fi
if ! $SETUP_ONLY; then
    echo "Jobs submitted:"
    echo "  Small (burst): ${submit_count_small}"
    echo "  Large (standard): ${submit_count_large}"
    echo "  Total: $((submit_count_small + submit_count_large))"
fi
echo "Errors: ${error_count}"
echo ""
echo "SLURM logs: ${STEP2_DIR}/slurm_logs/"
echo "========================================================================"
echo ""
echo "Completed: $(date)"
