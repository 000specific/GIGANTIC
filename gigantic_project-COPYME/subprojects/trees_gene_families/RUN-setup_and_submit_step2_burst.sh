#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 09 | Purpose: Set up STEP_2 workflow directories and submit burst jobs
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_gene_families - STEP_2 Burst Setup & Submission
################################################################################
#
# PURPOSE:
# For each gene_family-[name]/ directory:
#   1. Create workflow-RUN_1-rbh_rbf_homologs from COPYME
#   2. Create INPUT_user/ with species_keeper_list.tsv and RGS file
#   3. Update START_HERE-user_config.yaml with gene family name
#   4. Submit SLURM job for STEP_2 homolog discovery
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
RGS_SOURCE_DIR="${SCRIPT_DIR}/research_notebook/rgs_from_before/rgs_for_trees"
CONDA_ENV="ai_gigantic_trees_gene_families"

# SLURM settings for STEP_2 (BLAST-heavy)
SLURM_ACCOUNT="moroz"
SLURM_QOS="moroz-b"
SLURM_MEM="112gb"
SLURM_TIME="24:00:00"
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
# Gene family mapping (same as STEP_1)
# ============================================================================
declare -A GENE_FAMILY_RGS
GENE_FAMILY_RGS=(
    ["aquaporin_channels"]="rgs_channel-human-aquaporin_channels.aa"
    ["innexin_pannexin_channels"]="rgs_channel-human-innexin_pannexin_channels.aa"
    ["nitric_oxide_synthases"]="rgs_enzyme-human-nitric_oxide_synthases.aa"
    ["fgf_ligands"]="rgs_ligand-human-fgf_ligands.aa"
    ["gh_growth_hormone_ligands"]="rgs_ligand-human-gh_growth_hormone_ligands.aa"
    ["neuropeptide_ligands"]="rgs_ligand-human-neuropeptide_ligands.aa"
    ["tgfb_ligands"]="rgs_ligand-human-tgfb_ligands.aa"
    ["vegf_ligands"]="rgs_ligand-human-vegf_ligands.aa"
    ["wnt_ligands"]="rgs_ligand-human-wnt_ligands.aa"
    ["chrn_cholinergic_nicotinic_subunit_receptors"]="rgs_receptor-human-chrn_cholinergic_nicotinic_subunit_receptors.aa"
    ["glra_glycine_receptors"]="rgs_receptor-human-glra_glycine_receptors.aa"
    ["glutamate_ionotropic_receptors"]="rgs_receptor-human-glutamate_ionotropic_receptors.aa"
    ["gpcr_g_protein_coupled_receptors"]="rgs_receptor-human-gpcr_g_protein_coupled_receptors.aa"
    ["gucy1_soluble_guanylate_cyclase_receptors"]="rgs_receptor-human-gucy1_soluable_guanylate_cyclase_receptors.aa"
    ["gucy2_transmembrane_guanylate_cyclase_receptors"]="rgs_receptor-human-gucy2_transmembrane_guanylate_cyclase_receptors.aa"
    ["htr3_hydroxytryptamine_nAChR_receptors"]="rgs_receptor-human-htr3_hydroxytryptamine_nAChR_receptors.aa"
    ["htr3_hydroxytryptamine_receptors"]="rgs_receptor-human-htr3_hydroxytryptamine_receptors"
    ["mapr_membrane_associated_progesterone_receptors"]="rgs_receptor-human-mapr_membrane_associated_progesterone_receptors.aa"
    ["paqr_progestin_adipoq_receptors"]="rgs_receptor-human-paqr_progestin_adipoq_receptors.aa"
    ["snare_receptors"]="rgs_receptor-human-snare_receptors.aa"
    ["histones"]="rgs_structure-human-histones.aa"
    ["fox_forkhead_box_tfs"]="rgs_tf-human-fox_forkhead_box_tfs.aa"
    ["homeobox_tfs"]="rgs_tf-human-homeoboxe_tfs.aa"
    ["nhr_nuclear_hormone_receptor_tfs"]="rgs_tf-human-nhr_nuclear_hormone_receptor_tfs.aa"
    ["sry_box_tfs"]="rgs_tf-sry_box_tfs.aa"
    ["abc_transporters"]="rgs_transporter-human-abc_transporters.aa"
    ["p_type_atpase_transporters"]="rgs_transporter-human-p_type_atpase_transporters.aa"
    ["rtp_receptor_transporter_protein_transporters"]="rgs_transporter-human-rtp_receptor_transporter_protein_transporters.aa"
    ["stard_star_related_lipid_transfer_domain_containing_transporters"]="rgs_transporter-human-stard_star_related_lipid_transfer_domain_containing_transporters.aa"
)

# Track counts
setup_count=0
submit_count=0
skip_count=0
error_count=0

for gene_family in $(echo "${!GENE_FAMILY_RGS[@]}" | tr ' ' '\n' | sort); do
    rgs_filename="${GENE_FAMILY_RGS[$gene_family]}"

    FAMILY_DIR="${SCRIPT_DIR}/gene_family-${gene_family}"
    STEP2_COPYME="${FAMILY_DIR}/STEP_2-homolog_discovery/workflow-COPYME-rbh_rbf_homologs"
    STEP2_WORKFLOW="${FAMILY_DIR}/STEP_2-homolog_discovery/workflow-RUN_1-rbh_rbf_homologs"
    RGS_SOURCE="${RGS_SOURCE_DIR}/${rgs_filename}"

    echo "----------------------------------------"
    echo "Gene family: ${gene_family}"

    # Verify gene_family directory exists
    if [ ! -d "${FAMILY_DIR}" ]; then
        echo -e "  ${RED}ERROR: gene_family directory not found (run STEP_1 setup first)${NC}"
        error_count=$((error_count + 1))
        continue
    fi

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
        if [ -d "${STEP2_WORKFLOW}" ]; then
            echo -e "  ${YELLOW}workflow-RUN_1 exists, skipping setup${NC}"
            skip_count=$((skip_count + 1))
        else
            if $DRY_RUN; then
                echo -e "  ${BLUE}[DRY RUN] Would create workflow-RUN_1-rbh_rbf_homologs${NC}"
            else
                # 1. Copy COPYME to RUN_1
                cp -r "${STEP2_COPYME}" "${STEP2_WORKFLOW}"

                # 2. Create INPUT_user and populate
                mkdir -p "${STEP2_WORKFLOW}/INPUT_user"

                # Copy RGS file
                cp "${RGS_SOURCE}" "${STEP2_WORKFLOW}/INPUT_user/${rgs_filename}"

                # Copy species keeper list
                cp "${SPECIES_KEEPER_LIST}" "${STEP2_WORKFLOW}/INPUT_user/species_keeper_list.tsv"

                # 3. Update config YAML - gene family name and RGS path
                CONFIG_FILE="${STEP2_WORKFLOW}/START_HERE-user_config.yaml"
                sed -i "s|name: \"innexin_pannexin\"|name: \"${gene_family}\"|" "${CONFIG_FILE}"
                sed -i "s|rgs_file: \"INPUT_user/rgs_channel-human_worm_fly-innexin_pannexin_channels.aa\"|rgs_file: \"INPUT_user/${rgs_filename}\"|" "${CONFIG_FILE}"

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
echo "Gene families: ${#GENE_FAMILY_RGS[@]}"
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
