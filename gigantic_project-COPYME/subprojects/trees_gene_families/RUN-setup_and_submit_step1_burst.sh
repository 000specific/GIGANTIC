#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 10 | Purpose: Set up gene family directories and submit STEP_1 homolog discovery burst jobs
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_gene_families - STEP_1 Burst Setup & Submission
################################################################################
#
# PURPOSE:
# For each RGS file in research_notebook/rgs_from_before/rgs_for_trees/:
#   1. Create gene_family-[name]/ from gene_family_COPYME template (if needed)
#   2. Create workflow-RUN_1-rbh_rbf_homologs from COPYME
#   3. Copy RGS file and species_keeper_list to INPUT_user/
#   4. Update START_HERE-user_config.yaml with gene family name and RGS path
#   5. Submit SLURM job for STEP_1 homolog discovery (includes RGS validation)
#
# USAGE:
#   bash RUN-setup_and_submit_step1_burst.sh [OPTIONS]
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
TEMPLATE_DIR="${SCRIPT_DIR}/gene_family_COPYME"
RGS_SOURCE_DIR="${SCRIPT_DIR}/research_notebook/rgs_from_before/rgs_for_trees"
CONDA_ENV="ai_gigantic_trees_gene_families"

# SLURM settings for STEP_1 (BLAST-heavy homolog discovery)
SLURM_ACCOUNT="moroz"
SLURM_QOS="moroz-b"
SLURM_MEM="112gb"
SLURM_TIME="96:00:00"
SLURM_CPUS="15"

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
echo "GIGANTIC trees_gene_families - STEP_1 Burst Setup & Submission"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo "SLURM: ${SLURM_CPUS} CPUs, ${SLURM_MEM} RAM, ${SLURM_TIME}"
echo ""

if $DRY_RUN; then
    echo -e "${BLUE}DRY RUN MODE - No changes will be made${NC}"
    echo ""
fi

# Verify template exists
if [ ! -d "${TEMPLATE_DIR}" ]; then
    echo -e "${RED}ERROR: gene_family_COPYME template not found!${NC}"
    echo "Expected at: ${TEMPLATE_DIR}"
    exit 1
fi

# Verify RGS source directory
if [ ! -d "${RGS_SOURCE_DIR}" ]; then
    echo -e "${RED}ERROR: RGS source directory not found!${NC}"
    echo "Expected at: ${RGS_SOURCE_DIR}"
    exit 1
fi

# Create slurm_logs directory
mkdir -p "${SCRIPT_DIR}/slurm_logs"

# ============================================================================
# Generate species keeper list from genomesDB-species70
# ============================================================================
GENOMESDB_BLASTP="${SCRIPT_DIR}/../genomesDB-species70/output_to_input/STEP_4-create_final_species_set/species70_gigantic_T1_blastp"
SPECIES_KEEPER_LIST="/tmp/gigantic_species70_keeper_list.tsv"

if [ ! -d "${GENOMESDB_BLASTP}" ]; then
    echo -e "${RED}ERROR: genomesDB-species70 BLAST databases not found!${NC}"
    echo "Expected at: ${GENOMESDB_BLASTP}"
    echo "Run the genomesDB-species70 subproject first."
    exit 1
fi

# Extract Genus_species from proteome filenames
ls "${GENOMESDB_BLASTP}"/*.aa 2>/dev/null | while read f; do
    basename "$f" | sed 's/-T1-proteome\.aa$//' | awk -F'_' '{print $(NF-1)"_"$NF}'
done | sort -u > "${SPECIES_KEEPER_LIST}"

species_count=$(wc -l < "${SPECIES_KEEPER_LIST}")
echo "Species keeper list: ${species_count} species from genomesDB-species70"
echo ""

# ============================================================================
# Define gene families and their RGS files
# ============================================================================
# Format: gene_family_name|rgs_filename
# Skipping: wnt_hgnc_gg360-ligands (TSV table, not FASTA)
# Note: gpcr_g_protein_coupled_receptors (788 seqs) included but may need special handling

GENE_FAMILIES=(
    "aquaporin_channels|rgs_channel-human-aquaporin_channels.aa"
    "innexin_pannexin_channels|rgs_channel-human_worm_fly-innexin_pannexin_channels.aa"
    "nitric_oxide_synthases|rgs_enzyme-human-nitric_oxide_synthases.aa"
    "fgf_ligands|rgs_ligand-human-fgf_ligands.aa"
    "gh_growth_hormone_ligands|rgs_ligand-human-gh_growth_hormone_ligands.aa"
    "neuropeptide_ligands|rgs_ligand-human-neuropeptide_ligands.aa"
    "tgfb_ligands|rgs_ligand-human-tgfb_ligands.aa"
    "vegf_ligands|rgs_ligand-human-vegf_ligands.aa"
    "wnt_ligands|rgs_ligand-human-wnt_ligands.aa"
    "chrn_cholinergic_nicotinic_subunit_receptors|rgs_receptor-human-chrn_cholinergic_nicotinic_subunit_receptors.aa"
    "glra_glycine_receptors|rgs_receptor-human-glra_glycine_receptors.aa"
    "glutamate_ionotropic_receptors|rgs_receptor-human-glutamate_ionotropic_receptors.aa"
    "gpcr_g_protein_coupled_receptors|rgs_receptor-human-gpcr_g_protein_coupled_receptors.aa"
    "gucy1_soluble_guanylate_cyclase_receptors|rgs_receptor-human-gucy1_soluable_guanylate_cyclase_receptors.aa"
    "gucy2_transmembrane_guanylate_cyclase_receptors|rgs_receptor-human-gucy2_transmembrane_guanylate_cyclase_receptors.aa"
    "htr3_hydroxytryptamine_nAChR_receptors|rgs_receptor-human-htr3_hydroxytryptamine_nAChR_receptors.aa"
    "htr3_hydroxytryptamine_receptors|rgs_receptor-human-htr3_hydroxytryptamine_receptors.aa"
    "mapr_membrane_associated_progesterone_receptors|rgs_receptor-human-mapr_membrane_associated_progesterone_receptors.aa"
    "paqr_progestin_adipoq_receptors|rgs_receptor-human-paqr_progestin_adipoq_receptors.aa"
    "snare_receptors|rgs_receptor-human-snare_receptors.aa"
    "histones|rgs_structure-human-histones.aa"
    "fox_forkhead_box_tfs|rgs_tf-human-fox_forkhead_box_tfs.aa"
    "homeobox_tfs|rgs_tf-human-homeoboxe_tfs.aa"
    "nhr_nuclear_hormone_receptor_tfs|rgs_tf-human-nhr_nuclear_hormone_receptor_tfs.aa"
    "sry_box_tfs|rgs_tf-human-sry_box_tfs.aa"
    "abc_transporters|rgs_transporter-human-abc_transporters.aa"
    "p_type_atpase_transporters|rgs_transporter-human-p_type_atpase_transporters.aa"
    "rtp_receptor_transporter_protein_transporters|rgs_transporter-human-rtp_receptor_transporter_protein_transporters.aa"
    "stard_star_related_lipid_transfer_domain_containing_transporters|rgs_transporter-human-stard_star_related_lipid_transfer_domain_containing_transporters.aa"
)

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
        fi

        # Create workflow RUN_1 from COPYME
        if [ -d "${STEP1_WORKFLOW}" ]; then
            echo -e "  ${YELLOW}workflow-RUN_1 exists, skipping setup${NC}"
            skip_count=$((skip_count + 1))
        else
            if $DRY_RUN; then
                echo -e "  ${BLUE}[DRY RUN] Would create workflow-RUN_1-rbh_rbf_homologs${NC}"
            else
                # 1. Copy COPYME to RUN_1
                cp -r "${STEP1_COPYME}" "${STEP1_WORKFLOW}"

                # 2. Create INPUT_user and populate
                mkdir -p "${STEP1_WORKFLOW}/INPUT_user"

                # Copy RGS file
                cp "${RGS_SOURCE}" "${STEP1_WORKFLOW}/INPUT_user/${rgs_filename}"

                # Copy species keeper list
                cp "${SPECIES_KEEPER_LIST}" "${STEP1_WORKFLOW}/INPUT_user/species_keeper_list.tsv"

                # 3. Update config YAML - gene family name and RGS path
                CONFIG_FILE="${STEP1_WORKFLOW}/START_HERE-user_config.yaml"
                sed -i "s|name: \"innexin_pannexin\"|name: \"${gene_family}\"|" "${CONFIG_FILE}"
                sed -i "s|rgs_file: \"INPUT_user/rgs_channel-human_worm_fly-innexin_pannexin_channels.aa\"|rgs_file: \"INPUT_user/${rgs_filename}\"|" "${CONFIG_FILE}"

                echo -e "  ${GREEN}Created and configured STEP_1 workflow${NC}"
                setup_count=$((setup_count + 1))
            fi
        fi
    fi

    # ========================================================================
    # SUBMIT PHASE
    # ========================================================================
    if ! $SETUP_ONLY; then
        if [ ! -d "${STEP1_WORKFLOW}" ]; then
            echo -e "  ${YELLOW}Workflow directory not found, skipping submit${NC}"
            continue
        fi

        if $DRY_RUN; then
            echo -e "  ${BLUE}[DRY RUN] Would submit SLURM job for STEP_1${NC}"
            submit_count=$((submit_count + 1))
        else
            JOB_NAME="step1_${gene_family}"
            sbatch \
                --job-name="${JOB_NAME}" \
                --account="${SLURM_ACCOUNT}" \
                --qos="${SLURM_QOS}" \
                --mem="${SLURM_MEM}" \
                --time="${SLURM_TIME}" \
                --cpus-per-task="${SLURM_CPUS}" \
                --output="${SCRIPT_DIR}/slurm_logs/step1_${gene_family}-%j.log" \
                --wrap="module load conda 2>/dev/null || true; conda activate ${CONDA_ENV} || { echo 'ERROR: Failed to activate conda environment ${CONDA_ENV}'; exit 1; }; cd ${STEP1_WORKFLOW} && bash RUN-workflow.sh"

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
echo "Gene families: ${#GENE_FAMILIES[@]}"
if ! $SUBMIT_ONLY; then
    echo "Set up: ${setup_count}"
    echo "Skipped (already exist): ${skip_count}"
fi
if ! $SETUP_ONLY; then
    echo "Jobs submitted: ${submit_count}"
fi
echo "Errors: ${error_count}"
echo "SLURM resources per job: ${SLURM_CPUS} CPUs, ${SLURM_MEM} RAM, ${SLURM_TIME}"
echo "========================================================================"
echo ""
echo "Completed: $(date)"
