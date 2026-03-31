#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 31 14:55 | Purpose: Set up gene group directories and submit STEP_1 homolog discovery burst jobs for HGNC gene groups
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_gene_groups (HGNC) - STEP_1 Burst Setup & Submission
################################################################################
#
# PURPOSE:
# For each RGS file produced by STEP_0 (HGNC gene group RGS generation):
#   1. Create gene_group-[name]/ directory inside STEP_1-homolog_discovery/
#   2. Copy workflow-COPYME-rbh_rbf_homologs -> workflow-RUN_01-rbh_rbf_homologs
#   3. Copy RGS file, species_keeper_list, and rgs_species_map to INPUT_user/
#   4. Update START_HERE-user_config.yaml with gene group name and RGS path
#   5. Submit SLURM job for STEP_1 homolog discovery
#
# INPUT:
# Reads the STEP_0 summary TSV to iterate over all HGNC gene groups.
# RGS FASTA files are accessed via output_to_input symlinks from STEP_0.
#
# USAGE:
#   bash RUN-setup_and_submit_step1_burst.sh [OPTIONS]
#
# OPTIONS:
#   --dry-run         Show what would be done without making changes
#   --setup-only      Set up directories but don't submit jobs
#   --submit-only     Submit jobs for already-set-up directories
#   --max-seqs N      Only process gene groups with <= N sequences (default: all)
#   --min-seqs N      Only process gene groups with >= N sequences (default: 1)
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
# SLURM settings for STEP_1 (BLAST-heavy homolog discovery)
# ============================================================================
SLURM_ACCOUNT="moroz"
SLURM_QOS="moroz-b"
SLURM_MEM="112gb"
SLURM_TIME="96:00:00"
SLURM_CPUS="15"

# ============================================================================
# Options
# ============================================================================
DRY_RUN=false
SETUP_ONLY=false
SUBMIT_ONLY=false
MAX_SEQS=0       # 0 = no limit
MIN_SEQS=1
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
        --max-seqs)
            MAX_SEQS="$2"
            shift 2
            ;;
        --min-seqs)
            MIN_SEQS="$2"
            shift 2
            ;;
        --gene-group)
            SINGLE_GENE_GROUP="$2"
            shift 2
            ;;
        --help|-h)
            head -33 "$0" | grep -E "^#" | sed 's/^# //' | sed 's/^#//'
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
echo "SLURM: ${SLURM_CPUS} CPUs, ${SLURM_MEM} RAM, ${SLURM_TIME}"
if [ "$MAX_SEQS" -gt 0 ] 2>/dev/null; then
    echo "Filter: max ${MAX_SEQS} sequences per gene group"
fi
if [ "$MIN_SEQS" -gt 1 ] 2>/dev/null; then
    echo "Filter: min ${MIN_SEQS} sequences per gene group"
fi
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

# Extract Genus_species from proteome filenames
ls "${GENOMESDB_BLASTP}"/*.aa 2>/dev/null | while read f; do
    basename "$f" | sed 's/-T1-proteome\.aa$//' | awk -F'_' '{print $(NF-1)"_"$NF}'
done | sort -u > "${SPECIES_KEEPER_LIST}"

species_count=$(wc -l < "${SPECIES_KEEPER_LIST}")
echo "Species keeper list: ${species_count} species from genomesDB-species70"
echo ""

# Create slurm_logs directory at the STEP_1 level
mkdir -p "${STEP1_DIR}/slurm_logs"

# ============================================================================
# Read STEP_0 summary and process gene groups
# ============================================================================

# Track counts
setup_count=0
submit_count=0
skip_count=0
error_count=0
filter_count=0
total_count=0

# Read the summary TSV (skip header line)
# Use process substitution to avoid subshell (so counter variables persist)
while IFS=$'\t' read -r gene_group_id gene_group_name sanitized_name rgs_filename sequence_count; do
    total_count=$((total_count + 1))

    # --- Apply filters ---
    if [ -n "${SINGLE_GENE_GROUP}" ] && [ "${sanitized_name}" != "${SINGLE_GENE_GROUP}" ]; then
        continue
    fi

    if [ "$MAX_SEQS" -gt 0 ] 2>/dev/null && [ "$sequence_count" -gt "$MAX_SEQS" ] 2>/dev/null; then
        filter_count=$((filter_count + 1))
        continue
    fi

    if [ "$sequence_count" -lt "$MIN_SEQS" ] 2>/dev/null; then
        filter_count=$((filter_count + 1))
        continue
    fi

    # --- Paths for this gene group ---
    GENE_GROUP_DIR="${STEP1_DIR}/gene_group-${sanitized_name}"
    WORKFLOW_RUN="${GENE_GROUP_DIR}/workflow-RUN_01-rbh_rbf_homologs"
    RGS_SOURCE="${STEP0_RGS_DIR}/${rgs_filename}"

    echo "----------------------------------------"
    echo "Gene group: ${sanitized_name} (${gene_group_id}, ${sequence_count} seqs)"

    # Verify RGS file exists
    if [ ! -f "${RGS_SOURCE}" ]; then
        echo -e "  ${RED}ERROR: RGS file not found: ${rgs_filename}${NC}"
        error_count=$((error_count + 1))
        continue
    fi

    # ====================================================================
    # SETUP PHASE
    # ====================================================================
    if ! $SUBMIT_ONLY; then
        if [ -d "${WORKFLOW_RUN}" ]; then
            echo -e "  ${YELLOW}workflow-RUN_01 exists, skipping setup${NC}"
            skip_count=$((skip_count + 1))
        else
            if $DRY_RUN; then
                echo -e "  ${BLUE}[DRY RUN] Would create: gene_group-${sanitized_name}/workflow-RUN_01-rbh_rbf_homologs${NC}"
                setup_count=$((setup_count + 1))
            else
                # 1. Create gene_group directory and copy workflow template
                mkdir -p "${GENE_GROUP_DIR}"
                cp -r "${STEP1_COPYME}" "${WORKFLOW_RUN}"

                # 2. Populate INPUT_user
                mkdir -p "${WORKFLOW_RUN}/INPUT_user"

                # Copy RGS file (follow symlink to get real file)
                cp -L "${RGS_SOURCE}" "${WORKFLOW_RUN}/INPUT_user/${rgs_filename}"

                # Copy species keeper list
                cp "${SPECIES_KEEPER_LIST}" "${WORKFLOW_RUN}/INPUT_user/species_keeper_list.tsv"

                # Copy RGS species map (HGNC RGS headers use "human" as short name)
                cp "${RGS_SPECIES_MAP}" "${WORKFLOW_RUN}/INPUT_user/rgs_species_map.tsv"

                # 3. Update config YAML
                CONFIG_FILE="${WORKFLOW_RUN}/START_HERE-user_config.yaml"
                sed -i "s|name: \"innexin_pannexin\"|name: \"${sanitized_name}\"|" "${CONFIG_FILE}"
                sed -i "s|rgs_file: \"INPUT_user/rgs_channel-human_worm_fly-innexin_pannexin_channels.aa\"|rgs_file: \"INPUT_user/${rgs_filename}\"|" "${CONFIG_FILE}"

                echo -e "  ${GREEN}Created and configured STEP_1 workflow${NC}"
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
            echo -e "  ${BLUE}[DRY RUN] Would submit SLURM job for STEP_1${NC}"
            submit_count=$((submit_count + 1))
        else
            JOB_NAME="s1_hgnc_${sanitized_name}"
            # Truncate job name to 64 chars (SLURM limit)
            JOB_NAME="${JOB_NAME:0:64}"

            sbatch \
                --job-name="${JOB_NAME}" \
                --account="${SLURM_ACCOUNT}" \
                --qos="${SLURM_QOS}" \
                --mem="${SLURM_MEM}" \
                --time="${SLURM_TIME}" \
                --cpus-per-task="${SLURM_CPUS}" \
                --output="${STEP1_DIR}/slurm_logs/step1_${sanitized_name}-%j.log" \
                --wrap="module load conda 2>/dev/null || true; conda activate ${CONDA_ENV} || { echo 'ERROR: Failed to activate conda environment ${CONDA_ENV}'; exit 1; }; cd ${WORKFLOW_RUN} && bash RUN-workflow.sh"

            submit_count=$((submit_count + 1))
        fi
    fi

done < <(tail -n +2 "${STEP0_SUMMARY}")

# Clean up species keeper list
rm -f "${SPECIES_KEEPER_LIST}"

# Summary
echo ""
echo "========================================================================"
if $DRY_RUN; then
    echo -e "${BLUE}DRY RUN SUMMARY${NC}"
else
    echo -e "${GREEN}SUMMARY${NC}"
fi
echo "Total gene groups in STEP_0: ${total_count}"
echo "Filtered out: ${filter_count}"
if ! $SUBMIT_ONLY; then
    echo "Set up: ${setup_count}"
    echo "Skipped (already exist): ${skip_count}"
fi
if ! $SETUP_ONLY; then
    echo "Jobs submitted: ${submit_count}"
fi
echo "Errors: ${error_count}"
echo "SLURM resources per job: ${SLURM_CPUS} CPUs, ${SLURM_MEM} RAM, ${SLURM_TIME}"
echo ""
echo "SLURM logs: ${STEP1_DIR}/slurm_logs/"
echo "========================================================================"
echo ""
echo "Completed: $(date)"
