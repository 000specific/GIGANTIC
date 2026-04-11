#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 April 01 00:30 | Purpose: Set up and submit STEP_1 homolog discovery as blocked SLURM jobs for HGNC gene groups
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_gene_groups (HGNC) - STEP_1 Burst Setup & Submission
################################################################################
#
# PURPOSE:
# Process all HGNC gene groups through STEP_1 (homolog discovery) using a
# block-based SLURM strategy: gene groups are chunked into blocks of N,
# and each block runs as a single SLURM job that processes its gene groups
# sequentially. This means ~20-25 SLURM jobs instead of ~2,000, so once
# a job gets allocated it keeps its resources and processes all groups in
# that block without returning to the queue.
#
# TWO PHASES:
#   1. SETUP: Create gene_group-[name]/workflow-RUN_01 directories from COPYME
#   2. SUBMIT: Chunk gene groups into blocks and submit each block as one SLURM job
#
# TWO TIERS (based on RGS sequence count):
#   Small (<= 50 seqs): 4 CPUs, 30GB, 96hr, blocks of 100
#   Large (> 50 seqs):  15 CPUs, 112GB, 96hr, blocks of 25
#
# USAGE:
#   bash RUN-setup_and_submit_step1_burst.sh [OPTIONS]
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

# STEP_0 outputs (RGS files and summary)
STEP0_RGS_DIR="${SCRIPT_DIR}/../output_to_input/gene_groups-hugo_hgnc/STEP_0-hgnc_gene_groups/rgs_fastas"
STEP0_SUMMARY="${SCRIPT_DIR}/../output_to_input/gene_groups-hugo_hgnc/STEP_0-hgnc_gene_groups/3_ai-rgs_generation_summary.tsv"

# STEP_1 template and target directory
STEP1_DIR="${SCRIPT_DIR}/STEP_1-homolog_discovery"
STEP1_COPYME="${STEP1_DIR}/workflow-COPYME-rbh_rbf_homologs"

# RGS species map (all HGNC gene groups use "human" as species short name)
RGS_SPECIES_MAP="${STEP1_COPYME}/INPUT_user/rgs_species_map.tsv"

# genomesDB BLAST databases (for species keeper list)
GENOMESDB_BLASTP="${SCRIPT_DIR}/../../genomesDB-species70/output_to_input/STEP_4-create_final_species_set/species70_gigantic_T1_blastp"

# Conda environment
CONDA_ENV="ai_gigantic_trees_gene_families"

# ============================================================================
# SLURM settings - two-tier block-based strategy
# ============================================================================
SLURM_ACCOUNT="moroz"
SLURM_QOS="moroz-b"

LARGE_THRESHOLD=50  # RGS sequence count threshold

# Small gene groups (<= threshold): many per block, lower resources
SLURM_MEM_SMALL="30gb"
SLURM_TIME_SMALL="96:00:00"
SLURM_CPUS_SMALL="4"
BLOCK_SIZE_SMALL=100

# Large gene groups (> threshold): fewer per block, higher resources
SLURM_MEM_LARGE="112gb"
SLURM_TIME_LARGE="96:00:00"
SLURM_CPUS_LARGE="15"
BLOCK_SIZE_LARGE=25

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
            head -36 "$0" | grep -E "^#" | sed 's/^# //' | sed 's/^#//'
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
echo "GIGANTIC trees_gene_groups (HGNC) - STEP_1 Burst Setup & Submission"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""
echo "Block-based SLURM strategy:"
echo "  Small (<= ${LARGE_THRESHOLD} seqs): ${BLOCK_SIZE_SMALL}/block, ${SLURM_CPUS_SMALL} CPUs, ${SLURM_MEM_SMALL}, ${SLURM_TIME_SMALL}"
echo "  Large (>  ${LARGE_THRESHOLD} seqs): ${BLOCK_SIZE_LARGE}/block, ${SLURM_CPUS_LARGE} CPUs, ${SLURM_MEM_LARGE}, ${SLURM_TIME_LARGE}"
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

if [ ! -f "${STEP0_SUMMARY}" ]; then
    echo -e "${RED}ERROR: STEP_0 summary TSV not found!${NC}"
    echo "Expected at: ${STEP0_SUMMARY}"
    echo "Run STEP_0 (HGNC gene group RGS generation) first."
    exit 1
fi

if [ ! -d "${STEP0_RGS_DIR}" ]; then
    echo -e "${RED}ERROR: STEP_0 RGS FASTA directory not found!${NC}"
    echo "Expected at: ${STEP0_RGS_DIR}"
    exit 1
fi

if [ ! -d "${STEP1_COPYME}" ]; then
    echo -e "${RED}ERROR: STEP_1 workflow COPYME template not found!${NC}"
    echo "Expected at: ${STEP1_COPYME}"
    exit 1
fi

if [ ! -d "${GENOMESDB_BLASTP}" ]; then
    echo -e "${RED}ERROR: genomesDB-species70 BLAST databases not found!${NC}"
    echo "Expected at: ${GENOMESDB_BLASTP}"
    echo "Run the genomesDB-species70 subproject first."
    exit 1
fi

# ============================================================================
# Generate species keeper list from genomesDB-species70
# ============================================================================
SPECIES_KEEPER_LIST="/tmp/gigantic_species70_keeper_list_$$.tsv"

ls "${GENOMESDB_BLASTP}"/*.aa 2>/dev/null | while read f; do
    basename "$f" | sed 's/-T1-proteome\.aa$//' | awk -F'_' '{print $(NF-1)"_"$NF}'
done | sort -u > "${SPECIES_KEEPER_LIST}"

species_count=$(wc -l < "${SPECIES_KEEPER_LIST}")
echo "Species keeper list: ${species_count} species from genomesDB-species70"
echo ""

# Create slurm_logs directory
mkdir -p "${STEP1_DIR}/slurm_logs"

# ============================================================================
# PHASE 1: SETUP - Create gene_group-[name]/workflow-RUN_01 directories
# ============================================================================

# Collect gene groups into small/large lists for block submission
SMALL_GENE_GROUPS=()
LARGE_GENE_GROUPS=()

setup_count=0
skip_count=0
error_count=0
total_count=0

echo "========================================================================"
echo "PHASE 1: Setup gene group workflow directories"
echo "========================================================================"
echo ""

while IFS=$'\t' read -r gene_group_id gene_group_name sanitized_name rgs_filename sequence_count; do
    total_count=$((total_count + 1))

    # Apply single gene group filter
    if [ -n "${SINGLE_GENE_GROUP}" ] && [ "${sanitized_name}" != "${SINGLE_GENE_GROUP}" ]; then
        continue
    fi

    # Paths for this gene group
    GENE_GROUP_DIR="${STEP1_DIR}/gene_group-${sanitized_name}"
    WORKFLOW_RUN="${GENE_GROUP_DIR}/workflow-RUN_01-rbh_rbf_homologs"
    RGS_SOURCE="${STEP0_RGS_DIR}/${rgs_filename}"

    # Verify RGS file exists
    if [ ! -f "${RGS_SOURCE}" ]; then
        echo -e "  ${RED}ERROR: RGS not found: ${rgs_filename}${NC}"
        error_count=$((error_count + 1))
        continue
    fi

    # Categorize into small/large
    if [ "$sequence_count" -gt "$LARGE_THRESHOLD" ] 2>/dev/null; then
        LARGE_GENE_GROUPS+=("${sanitized_name}")
    else
        SMALL_GENE_GROUPS+=("${sanitized_name}")
    fi

    # ---- SETUP ----
    if ! $SUBMIT_ONLY; then
        if [ -d "${WORKFLOW_RUN}" ]; then
            skip_count=$((skip_count + 1))
        else
            if $DRY_RUN; then
                setup_count=$((setup_count + 1))
            else
                mkdir -p "${GENE_GROUP_DIR}"
                cp -r "${STEP1_COPYME}" "${WORKFLOW_RUN}"

                mkdir -p "${WORKFLOW_RUN}/INPUT_user"
                cp -L "${RGS_SOURCE}" "${WORKFLOW_RUN}/INPUT_user/${rgs_filename}"
                cp "${SPECIES_KEEPER_LIST}" "${WORKFLOW_RUN}/INPUT_user/species_keeper_list.tsv"
                cp "${RGS_SPECIES_MAP}" "${WORKFLOW_RUN}/INPUT_user/rgs_species_map.tsv"

                CONFIG_FILE="${WORKFLOW_RUN}/START_HERE-user_config.yaml"
                sed -i "s|name: \"innexin_pannexin\"|name: \"${sanitized_name}\"|" "${CONFIG_FILE}"
                sed -i "s|rgs_file: \"INPUT_user/rgs_channel-human_worm_fly-innexin_pannexin_channels.aa\"|rgs_file: \"INPUT_user/${rgs_filename}\"|" "${CONFIG_FILE}"

                setup_count=$((setup_count + 1))
            fi
        fi
    fi

done < <(tail -n +2 "${STEP0_SUMMARY}")

# Clean up species keeper list
rm -f "${SPECIES_KEEPER_LIST}"

if ! $SUBMIT_ONLY; then
    echo "Setup: ${setup_count} new, ${skip_count} already exist, ${error_count} errors"
fi
echo "Small gene groups: ${#SMALL_GENE_GROUPS[@]}"
echo "Large gene groups: ${#LARGE_GENE_GROUPS[@]}"
echo ""

# ============================================================================
# PHASE 2: SUBMIT - Chunk into blocks and submit each block as one SLURM job
# ============================================================================

if $SETUP_ONLY; then
    echo "Setup-only mode. Exiting."
    echo ""
    echo "Completed: $(date)"
    exit 0
fi

echo "========================================================================"
echo "PHASE 2: Submit SLURM block jobs"
echo "========================================================================"
echo ""

submit_block() {
    local block_name="$1"
    local slurm_cpus="$2"
    local slurm_mem="$3"
    local slurm_time="$4"
    local tier="$5"
    shift 5
    local gene_groups=("$@")
    local count=${#gene_groups[@]}

    if [ "$count" -eq 0 ]; then
        return
    fi

    # Build the sequential runner command
    # Each gene group: cd into its workflow-RUN_01 dir, run RUN-workflow.sh, cd back
    local runner_commands="module load conda 2>/dev/null || true; conda activate ${CONDA_ENV} || { echo 'FATAL: conda env failed'; exit 1; }; "
    runner_commands+="echo '========================================'; "
    runner_commands+="echo 'BLOCK: ${block_name} (${count} gene groups)'; "
    runner_commands+="echo '========================================'; "
    runner_commands+="BLOCK_SUCCESS=0; BLOCK_FAIL=0; BLOCK_TOTAL=${count}; "

    for gene_group in "${gene_groups[@]}"; do
        local workflow_dir="${STEP1_DIR}/gene_group-${gene_group}/workflow-RUN_01-rbh_rbf_homologs"
        runner_commands+="echo ''; echo '----------------------------------------'; "
        runner_commands+="echo \"[\$(date)] Starting: ${gene_group}\"; "
        runner_commands+="if cd '${workflow_dir}' 2>/dev/null; then "
        runner_commands+="  if bash RUN-workflow.sh; then "
        runner_commands+="    echo \"[\$(date)] SUCCESS: ${gene_group}\"; "
        runner_commands+="    BLOCK_SUCCESS=\$((BLOCK_SUCCESS + 1)); "
        runner_commands+="  else "
        runner_commands+="    echo \"[\$(date)] FAILED: ${gene_group} (exit \$?)\"; "
        runner_commands+="    BLOCK_FAIL=\$((BLOCK_FAIL + 1)); "
        runner_commands+="  fi; "
        runner_commands+="else "
        runner_commands+="  echo \"[\$(date)] FAILED: ${gene_group} (directory not found)\"; "
        runner_commands+="  BLOCK_FAIL=\$((BLOCK_FAIL + 1)); "
        runner_commands+="fi; "
    done

    runner_commands+="echo ''; echo '========================================'; "
    runner_commands+="echo \"BLOCK COMPLETE: \${BLOCK_SUCCESS}/\${BLOCK_TOTAL} succeeded, \${BLOCK_FAIL} failed\"; "
    runner_commands+="echo '========================================'; "

    if $DRY_RUN; then
        echo -e "  ${BLUE}[DRY RUN] Block ${block_name}: ${count} gene groups (${tier}: ${slurm_cpus} CPUs, ${slurm_mem})${NC}"
    else
        sbatch \
            --job-name="${block_name}" \
            --account="${SLURM_ACCOUNT}" \
            --qos="${SLURM_QOS}" \
            --mem="${slurm_mem}" \
            --time="${slurm_time}" \
            --cpus-per-task="${slurm_cpus}" \
            --output="${STEP1_DIR}/slurm_logs/${block_name}-%j.log" \
            --wrap="${runner_commands}"

        echo -e "  ${GREEN}Submitted ${block_name}: ${count} gene groups (${tier})${NC}"
    fi
}

# ---- Submit small blocks ----
small_block_count=0
small_submitted=0
block_start=0

while [ "$block_start" -lt "${#SMALL_GENE_GROUPS[@]}" ]; do
    block_end=$((block_start + BLOCK_SIZE_SMALL))
    if [ "$block_end" -gt "${#SMALL_GENE_GROUPS[@]}" ]; then
        block_end=${#SMALL_GENE_GROUPS[@]}
    fi

    small_block_count=$((small_block_count + 1))
    block_name="s1_hgnc_small_block_$(printf '%02d' ${small_block_count})"
    block_slice=("${SMALL_GENE_GROUPS[@]:${block_start}:${BLOCK_SIZE_SMALL}}")

    submit_block "${block_name}" "${SLURM_CPUS_SMALL}" "${SLURM_MEM_SMALL}" "${SLURM_TIME_SMALL}" "small" "${block_slice[@]}"

    small_submitted=$((small_submitted + ${#block_slice[@]}))
    block_start=$block_end
done

# ---- Submit large blocks ----
large_block_count=0
large_submitted=0
block_start=0

while [ "$block_start" -lt "${#LARGE_GENE_GROUPS[@]}" ]; do
    block_end=$((block_start + BLOCK_SIZE_LARGE))
    if [ "$block_end" -gt "${#LARGE_GENE_GROUPS[@]}" ]; then
        block_end=${#LARGE_GENE_GROUPS[@]}
    fi

    large_block_count=$((large_block_count + 1))
    block_name="s1_hgnc_large_block_$(printf '%02d' ${large_block_count})"
    block_slice=("${LARGE_GENE_GROUPS[@]:${block_start}:${BLOCK_SIZE_LARGE}}")

    submit_block "${block_name}" "${SLURM_CPUS_LARGE}" "${SLURM_MEM_LARGE}" "${SLURM_TIME_LARGE}" "large" "${block_slice[@]}"

    large_submitted=$((large_submitted + ${#block_slice[@]}))
    block_start=$block_end
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
echo "Total gene groups: ${total_count}"
echo ""
echo "Small blocks: ${small_block_count} SLURM jobs (${small_submitted} gene groups, ${BLOCK_SIZE_SMALL}/block)"
echo "  Resources: ${SLURM_CPUS_SMALL} CPUs, ${SLURM_MEM_SMALL} RAM, ${SLURM_TIME_SMALL}"
echo ""
echo "Large blocks: ${large_block_count} SLURM jobs (${large_submitted} gene groups, ${BLOCK_SIZE_LARGE}/block)"
echo "  Resources: ${SLURM_CPUS_LARGE} CPUs, ${SLURM_MEM_LARGE} RAM, ${SLURM_TIME_LARGE}"
echo ""
echo "Total SLURM jobs: $((small_block_count + large_block_count))"
echo "Errors: ${error_count}"
echo ""
echo "SLURM logs: ${STEP1_DIR}/slurm_logs/"
echo "========================================================================"
echo ""
echo "Completed: $(date)"
