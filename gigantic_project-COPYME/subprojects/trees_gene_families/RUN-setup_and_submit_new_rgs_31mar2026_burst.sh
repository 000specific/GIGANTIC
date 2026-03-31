#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 31 | Purpose: Set up and submit STEP_1 burst jobs for new_rgs_31mar2026 gene families
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_gene_families - New RGS 31mar2026 Burst Setup & Submission
################################################################################
#
# PURPOSE:
# For each RGS file in research_notebook/rgs_from_before/rgs_for_trees/new_rgs_31mar2026/:
#   1. Create gene_family-[name]/ from gene_family_COPYME template (if needed)
#   2. Create workflow-RUN_1-rbh_rbf_homologs from COPYME
#   3. Copy RGS file, species_keeper_list, and rgs_species_map to INPUT_user/
#   4. Update START_HERE-user_config.yaml with gene family name, RGS path,
#      and burst resources (100 CPUs, 750GB RAM, 96hr)
#   5. Submit SLURM burst job
#
# USAGE:
#   bash RUN-setup_and_submit_new_rgs_31mar2026_burst.sh [OPTIONS]
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
NC='\033[0m'

# Script directory (subproject root)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# Paths
TEMPLATE_DIR="${SCRIPT_DIR}/gene_family_COPYME"
RGS_SOURCE_DIR="${SCRIPT_DIR}/research_notebook/rgs_from_before/rgs_for_trees/new_rgs_31mar2026"

# SLURM burst settings
SLURM_ACCOUNT="moroz"
SLURM_QOS="moroz-b"
SLURM_MEM="750gb"
SLURM_TIME="96:00:00"
SLURM_CPUS="100"

# Config values to write into START_HERE-user_config.yaml
CONFIG_CPUS="100"
CONFIG_MEMORY_GB="750"
CONFIG_TIME_HOURS="96"

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
            head -30 "$0" | grep -E "^#" | sed 's/^# //' | sed 's/^#//'
            exit 0
            ;;
        *)
            echo -e "${RED}ERROR: Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo "========================================================================"
echo "GIGANTIC trees_gene_families - New RGS 31mar2026 Burst Setup"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo "SLURM burst: ${SLURM_CPUS} CPUs, ${SLURM_MEM} RAM, ${SLURM_TIME}"
echo ""

if $DRY_RUN; then
    echo -e "${BLUE}DRY RUN MODE - No changes will be made${NC}"
    echo ""
fi

# Verify template and source directories
if [ ! -d "${TEMPLATE_DIR}" ]; then
    echo -e "${RED}ERROR: gene_family_COPYME template not found at ${TEMPLATE_DIR}${NC}"
    exit 1
fi

if [ ! -d "${RGS_SOURCE_DIR}" ]; then
    echo -e "${RED}ERROR: RGS source directory not found at ${RGS_SOURCE_DIR}${NC}"
    exit 1
fi

# Create slurm_logs directory
mkdir -p "${SCRIPT_DIR}/slurm_logs"

# ============================================================================
# Generate species keeper list from genomesDB-species70
# ============================================================================
GENOMESDB_BLASTP="${SCRIPT_DIR}/../genomesDB-species70/output_to_input/STEP_4-create_final_species_set/species70_gigantic_T1_blastp"
SPECIES_KEEPER_LIST="/tmp/gigantic_species70_keeper_list_31mar2026.tsv"

if [ ! -d "${GENOMESDB_BLASTP}" ]; then
    echo -e "${RED}ERROR: genomesDB-species70 BLAST databases not found at ${GENOMESDB_BLASTP}${NC}"
    exit 1
fi

ls "${GENOMESDB_BLASTP}"/*.aa 2>/dev/null | while read f; do
    basename "$f" | sed 's/-T1-proteome\.aa$//' | awk -F'_' '{print $(NF-1)"_"$NF}'
done | sort -u > "${SPECIES_KEEPER_LIST}"

species_count=$(wc -l < "${SPECIES_KEEPER_LIST}")
echo "Species keeper list: ${species_count} species from genomesDB-species70"
echo ""

# ============================================================================
# RGS species map (covers human, fly, worm, mouse, anemone)
# ============================================================================
RGS_SPECIES_MAP="/tmp/gigantic_rgs_species_map_31mar2026.tsv"
cat > "${RGS_SPECIES_MAP}" << 'MAPEOF'
# RGS short name to GIGANTIC Genus_species mapping
# Format: short_name<TAB>Genus_species
# Add mappings for any short names used in RGS FASTA headers
human	Homo_sapiens
mouse	Mus_musculus
fly	Drosophila_melanogaster
worm	Caenorhabditis_elegans
anemone	Nematostella_vectensis
hydra	Hydra_vulgaris
MAPEOF

echo "RGS species map created with human, mouse, fly, worm, anemone, hydra"
echo ""

# ============================================================================
# Define gene families from new_rgs_31mar2026 .aa files
# ============================================================================
# Build the list from actual files. Extract gene family name from filename:
# rgs_CATEGORY-SOURCE-DESCRIPTION.aa -> DESCRIPTION becomes the gene family name

GENE_FAMILIES=()
while IFS= read -r rgs_file; do
    rgs_filename=$(basename "${rgs_file}")

    # Extract gene family name: last dash-separated field, minus .aa extension
    # rgs_channel-human_mouse_fly_worm_anemone-transient_receptor_potential_cation_channels.aa
    #   -> transient_receptor_potential_cation_channels
    # rgs_enzyme-human_fly_worm-kinases_AGC.aa
    #   -> kinases_AGC
    gene_family_name=$(echo "${rgs_filename}" | sed 's/\.aa$//' | rev | cut -d'-' -f1 | rev)

    GENE_FAMILIES+=("${gene_family_name}|${rgs_filename}")
done < <(ls "${RGS_SOURCE_DIR}"/*.aa 2>/dev/null | sort)

echo "Gene families to process: ${#GENE_FAMILIES[@]}"
echo ""

# Track counts
setup_count=0
submit_count=0
skip_count=0
error_count=0

for entry in "${GENE_FAMILIES[@]}"; do
    IFS='|' read -r gene_family rgs_filename <<< "$entry"

    FAMILY_DIR="${SCRIPT_DIR}/gene_family-${gene_family}"
    STEP1_COPYME="${FAMILY_DIR}/STEP_1-homolog_discovery/workflow-COPYME-rbh_rbf_homologs"
    STEP1_WORKFLOW="${FAMILY_DIR}/STEP_1-homolog_discovery/workflow-RUN_1-rbh_rbf_homologs"
    RGS_SOURCE="${RGS_SOURCE_DIR}/${rgs_filename}"

    echo "----------------------------------------"
    echo "Gene family: ${gene_family}"

    # Verify RGS file exists
    if [ ! -f "${RGS_SOURCE}" ]; then
        echo -e "  ${RED}ERROR: RGS file not found: ${rgs_filename}${NC}"
        error_count=$((error_count + 1))
        continue
    fi

    seq_count=$(grep -c '^>' "${RGS_SOURCE}")
    echo "  RGS: ${rgs_filename} (${seq_count} sequences)"

    # ========================================================================
    # SETUP PHASE
    # ========================================================================
    if ! $SUBMIT_ONLY; then
        # Create gene_family directory from template if it doesn't exist
        if [ ! -d "${FAMILY_DIR}" ]; then
            if $DRY_RUN; then
                echo -e "  ${BLUE}[DRY RUN] Would create: gene_family-${gene_family}/${NC}"
            else
                cp -r "${TEMPLATE_DIR}" "${FAMILY_DIR}"
                echo -e "  ${GREEN}Created gene_family-${gene_family}/ from template${NC}"
            fi
        else
            echo -e "  ${YELLOW}gene_family-${gene_family}/ already exists${NC}"
        fi

        # Create workflow RUN_1 from COPYME
        if [ -d "${STEP1_WORKFLOW}" ]; then
            echo -e "  ${YELLOW}workflow-RUN_1 already exists, skipping setup${NC}"
            skip_count=$((skip_count + 1))
        else
            if $DRY_RUN; then
                echo -e "  ${BLUE}[DRY RUN] Would create workflow-RUN_1-rbh_rbf_homologs${NC}"
                echo -e "  ${BLUE}[DRY RUN] Would configure: ${CONFIG_CPUS} CPUs, ${CONFIG_MEMORY_GB}GB RAM, ${CONFIG_TIME_HOURS}hr${NC}"
            else
                # 1. Copy COPYME to RUN_1
                cp -r "${STEP1_COPYME}" "${STEP1_WORKFLOW}"

                # 2. Populate INPUT_user
                mkdir -p "${STEP1_WORKFLOW}/INPUT_user"
                cp "${RGS_SOURCE}" "${STEP1_WORKFLOW}/INPUT_user/${rgs_filename}"
                cp "${SPECIES_KEEPER_LIST}" "${STEP1_WORKFLOW}/INPUT_user/species_keeper_list.tsv"
                cp "${RGS_SPECIES_MAP}" "${STEP1_WORKFLOW}/INPUT_user/rgs_species_map.tsv"

                # 3. Update START_HERE-user_config.yaml
                CONFIG_FILE="${STEP1_WORKFLOW}/START_HERE-user_config.yaml"

                # Gene family name
                sed -i "s|name: \"innexin_pannexin\"|name: \"${gene_family}\"|" "${CONFIG_FILE}"

                # RGS file path
                sed -i "s|rgs_file: \"INPUT_user/rgs_channel-human_worm_fly-innexin_pannexin_channels.aa\"|rgs_file: \"INPUT_user/${rgs_filename}\"|" "${CONFIG_FILE}"

                # Burst resources: 100 CPUs, 750GB RAM, 96hr
                sed -i "s|^cpus: 50|cpus: ${CONFIG_CPUS}|" "${CONFIG_FILE}"
                sed -i "s|^memory_gb: 187|memory_gb: ${CONFIG_MEMORY_GB}|" "${CONFIG_FILE}"

                # SLURM settings
                sed -i "s|slurm_account: \"your_account\"|slurm_account: \"${SLURM_ACCOUNT}\"|" "${CONFIG_FILE}"
                sed -i "s|slurm_qos: \"your_qos\"|slurm_qos: \"${SLURM_QOS}\"|" "${CONFIG_FILE}"

                echo -e "  ${GREEN}Created and configured STEP_1 workflow (${CONFIG_CPUS} CPUs, ${CONFIG_MEMORY_GB}GB, ${CONFIG_TIME_HOURS}hr)${NC}"
                setup_count=$((setup_count + 1))
            fi
        fi
    fi

    # ========================================================================
    # SUBMIT PHASE
    # ========================================================================
    if ! $SETUP_ONLY; then
        if [ ! -d "${STEP1_WORKFLOW}" ] && ! $DRY_RUN; then
            echo -e "  ${YELLOW}Workflow directory not found, skipping submit${NC}"
            continue
        fi

        if $DRY_RUN; then
            echo -e "  ${BLUE}[DRY RUN] Would submit: sbatch --cpus=${SLURM_CPUS} --mem=${SLURM_MEM} --time=${SLURM_TIME}${NC}"
            submit_count=$((submit_count + 1))
        else
            JOB_NAME="step1_${gene_family}"

            # Truncate job name if too long for SLURM (max ~128 chars)
            if [ ${#JOB_NAME} -gt 60 ]; then
                JOB_NAME="${JOB_NAME:0:60}"
            fi

            SUBMIT_RESULT=$(sbatch \
                --job-name="${JOB_NAME}" \
                --account="${SLURM_ACCOUNT}" \
                --qos="${SLURM_QOS}" \
                --mem="${SLURM_MEM}" \
                --time="${SLURM_TIME}" \
                --cpus-per-task="${SLURM_CPUS}" \
                --output="${SCRIPT_DIR}/slurm_logs/step1_${gene_family}-%j.log" \
                --wrap="module load conda 2>/dev/null || true; conda activate ai_gigantic_trees_gene_families || { echo 'ERROR: Failed to activate conda env'; exit 1; }; cd ${STEP1_WORKFLOW} && bash RUN-workflow.sh" \
                2>&1)

            echo -e "  ${GREEN}${SUBMIT_RESULT}${NC}"
            submit_count=$((submit_count + 1))
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
echo "Gene families: ${#GENE_FAMILIES[@]}"
if ! $SUBMIT_ONLY; then
    echo "Set up: ${setup_count}"
    echo "Skipped (already exist): ${skip_count}"
fi
if ! $SETUP_ONLY; then
    echo "Jobs submitted: ${submit_count}"
fi
echo "Errors: ${error_count}"
echo "SLURM burst resources per job: ${SLURM_CPUS} CPUs, ${SLURM_MEM} RAM, ${SLURM_TIME}"
echo "========================================================================"
echo ""
echo "Monitor jobs: squeue -u \$USER"
echo "Check logs: ls -lt slurm_logs/step1_*"
echo ""
echo "Completed: $(date)"
