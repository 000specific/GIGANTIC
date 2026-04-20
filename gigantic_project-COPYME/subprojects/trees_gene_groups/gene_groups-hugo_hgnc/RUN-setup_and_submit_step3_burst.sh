#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 April 20 | Purpose: Set up and submit STEP_3 tree visualization for HGNC gene groups
# Human: Eric Edsinger

################################################################################
# GIGANTIC trees_gene_groups (HGNC) - STEP_3 Burst Setup & Submission
################################################################################
#
# PURPOSE:
# For each gene group with completed STEP_2 (tree newick files in output_to_input/),
# create a STEP_3 workflow directory and run the tree visualization (PDF + SVG).
#
# STEP_3 is lightweight (seconds to minutes per gene group) so runs LOCALLY
# by default (no SLURM needed). If preferred, can submit as a single batch job
# instead by passing --slurm.
#
# PREREQUISITES:
#   - STEP_2 complete (tree newick files in output_to_input/gene_groups-hugo_hgnc/STEP_2-*/)
#   - conda env 'aiG-trees_gene_groups-visualization' (auto-created on first run)
#
# USAGE:
#   bash RUN-setup_and_submit_step3_burst.sh [OPTIONS]
#
# OPTIONS:
#   --dry-run         Show what would be done without making changes
#   --setup-only      Set up directories but don't run
#   --run-only        Run already-set-up directories (no setup)
#   --gene-group NAME Process only this specific gene group (sanitized name)
#   --slurm           Submit each as a SLURM job (default: run locally)
#   --help            Show this help message
#
################################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Paths
# ============================================================================

STEP2_OTI="${SCRIPT_DIR}/../output_to_input/gene_groups-hugo_hgnc/STEP_2-phylogenetic_analysis"
STEP3_DIR="${SCRIPT_DIR}/STEP_3-tree_visualization"
STEP3_COPYME="${STEP3_DIR}/workflow-COPYME-tree_visualization"
CONDA_ENV="aiG-trees_gene_groups-visualization"

# ============================================================================
# SLURM (if --slurm used; STEP_3 is usually fast enough to run locally)
# ============================================================================
SLURM_ACCOUNT="moroz"
SLURM_QOS="moroz-b"
SLURM_MEM="8gb"
SLURM_TIME="2:00:00"
SLURM_CPUS="2"

# ============================================================================
# Options
# ============================================================================
DRY_RUN=false
SETUP_ONLY=false
RUN_ONLY=false
SINGLE_GENE_GROUP=""
USE_SLURM=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true; shift ;;
        --setup-only) SETUP_ONLY=true; shift ;;
        --run-only) RUN_ONLY=true; shift ;;
        --gene-group) SINGLE_GENE_GROUP="$2"; shift 2 ;;
        --slurm) USE_SLURM=true; shift ;;
        --help|-h)
            head -34 "$0" | grep -E "^#" | sed 's/^# //' | sed 's/^#//'
            exit 0 ;;
        *)
            echo -e "${RED}ERROR: Unknown option: $1${NC}"
            exit 1 ;;
    esac
done

echo "========================================================================"
echo "GIGANTIC trees_gene_groups (HGNC) - STEP_3 Burst Setup & Run"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""
if $USE_SLURM; then
    echo "Execution: SLURM (${SLURM_CPUS} CPUs, ${SLURM_MEM}, ${SLURM_TIME}, qos=${SLURM_QOS})"
else
    echo "Execution: LOCAL (sequential, usually fast)"
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

if [ ! -d "${STEP2_OTI}" ]; then
    echo -e "${RED}ERROR: STEP_2 output_to_input not found: ${STEP2_OTI}${NC}"
    exit 1
fi

if [ ! -d "${STEP3_COPYME}" ]; then
    echo -e "${RED}ERROR: STEP_3 COPYME not found: ${STEP3_COPYME}${NC}"
    exit 1
fi

mkdir -p "${STEP3_DIR}/slurm_logs"

# ============================================================================
# Iterate over completed STEP_2 gene groups
# ============================================================================

setup_count=0
run_count=0
skip_count=0
no_trees_count=0
total_count=0

for STEP2_GG_DIR in "${STEP2_OTI}"/gene_group-*/; do
    [ -d "$STEP2_GG_DIR" ] || continue

    gene_group_dir_name=$(basename "$STEP2_GG_DIR")
    sanitized_name="${gene_group_dir_name#gene_group-}"
    total_count=$((total_count + 1))

    # Apply single gene group filter
    if [ -n "${SINGLE_GENE_GROUP}" ] && [ "${sanitized_name}" != "${SINGLE_GENE_GROUP}" ]; then
        continue
    fi

    echo "----------------------------------------"
    echo "Gene group: ${sanitized_name}"

    # Check at least one tree file exists
    tree_count=$(ls "${STEP2_GG_DIR}"/*.fasttree "${STEP2_GG_DIR}"/*.treefile "${STEP2_GG_DIR}"/*.veryfasttree "${STEP2_GG_DIR}"/*.phylobayes.nwk 2>/dev/null | wc -l)
    if [ "$tree_count" -eq 0 ]; then
        echo -e "  ${YELLOW}No tree newicks found; skipping${NC}"
        no_trees_count=$((no_trees_count + 1))
        continue
    fi
    echo "  Tree files found: ${tree_count}"

    # Paths for this gene group
    GG_DIR="${STEP3_DIR}/gene_group-${sanitized_name}"
    WF="${GG_DIR}/workflow-RUN_01-tree_visualization"

    # ---- SETUP ----
    if ! $RUN_ONLY; then
        if [ -d "${WF}" ]; then
            echo -e "  ${YELLOW}workflow-RUN_01 exists; skipping setup${NC}"
            skip_count=$((skip_count + 1))
        else
            if $DRY_RUN; then
                echo -e "  ${BLUE}[DRY RUN] Would create: ${WF}${NC}"
                setup_count=$((setup_count + 1))
            else
                mkdir -p "${GG_DIR}"
                cp -r "${STEP3_COPYME}" "${WF}"

                CONFIG="${WF}/START_HERE-user_config.yaml"
                sed -i "s|name: \"innexin_pannexin\"|name: \"${sanitized_name}\"|" "${CONFIG}"

                echo -e "  ${GREEN}Created and configured STEP_3 workflow${NC}"
                setup_count=$((setup_count + 1))
            fi
        fi
    fi

    # ---- RUN ----
    if ! $SETUP_ONLY; then
        if ! $DRY_RUN && [ ! -d "${WF}" ]; then
            echo -e "  ${YELLOW}Workflow dir not found; skipping run${NC}"
            continue
        fi

        if $DRY_RUN; then
            if $USE_SLURM; then
                echo -e "  ${BLUE}[DRY RUN] Would submit SLURM job${NC}"
            else
                echo -e "  ${BLUE}[DRY RUN] Would run locally${NC}"
            fi
            run_count=$((run_count + 1))
        else
            if $USE_SLURM; then
                job_name="s3_hgnc_${sanitized_name:0:50}"
                sbatch \
                    --job-name="${job_name}" \
                    --account="${SLURM_ACCOUNT}" \
                    --qos="${SLURM_QOS}" \
                    --mem="${SLURM_MEM}" \
                    --time="${SLURM_TIME}" \
                    --cpus-per-task="${SLURM_CPUS}" \
                    --output="${STEP3_DIR}/slurm_logs/step3_${sanitized_name}-%j.log" \
                    --wrap="cd ${WF} && bash RUN-workflow.sh"
                echo -e "  ${GREEN}Submitted SLURM job${NC}"
            else
                # Run locally (STEP_3 is lightweight)
                (cd "${WF}" && bash RUN-workflow.sh) 2>&1 | tail -5
                echo -e "  ${GREEN}Completed${NC}"
            fi
            run_count=$((run_count + 1))
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
echo "Total gene groups with STEP_2 output: ${total_count}"
echo "No tree files: ${no_trees_count}"
if ! $RUN_ONLY; then
    echo "Set up: ${setup_count}"
    echo "Skipped (already exist): ${skip_count}"
fi
if ! $SETUP_ONLY; then
    echo "Runs: ${run_count}"
fi
echo ""
echo "========================================================================"
echo ""
echo "Completed: $(date)"
