#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 May 05 03:45 | Purpose: One-shot STEP_2 burst with uniform per-job resources for HGNC gene groups
# Human: Eric Edsinger
#
# Submits one SLURM job per gene group with completed STEP_1 (AGS in
# output_to_input/). Per-job resources: 25 CPUs / 150 GB / 18 h on moroz-b
# burst QOS, IQ-TREE enabled alongside FastTree (matches existing burst
# convention). One sbatch per gene group; SLURM queues them.
#
# Differs from the long-standing RUN-setup_and_submit_step2_burst.sh in that
# this script applies a single uniform resource spec rather than the two-tier
# small/large by AGS size.
#
# Usage:
#   bash RUN-step2_burst_uniform_25cpu_150gb_18h.sh --dry-run
#   bash RUN-step2_burst_uniform_25cpu_150gb_18h.sh --setup-only
#   bash RUN-step2_burst_uniform_25cpu_150gb_18h.sh --submit-only
#   bash RUN-step2_burst_uniform_25cpu_150gb_18h.sh --gene-group <name>
#   bash RUN-step2_burst_uniform_25cpu_150gb_18h.sh

set -e

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
# SLURM resources (uniform per user spec on 2026-05-05)
# ============================================================================
SLURM_ACCOUNT="moroz"
SLURM_QOS="moroz-b"
SLURM_CPUS="25"
SLURM_MEM="150gb"
SLURM_TIME="18:00:00"

# ============================================================================
# Options
# ============================================================================
DRY_RUN=false
SETUP_ONLY=false
SUBMIT_ONLY=false
SINGLE_GENE_GROUP=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)     DRY_RUN=true;     shift ;;
        --setup-only)  SETUP_ONLY=true;  shift ;;
        --submit-only) SUBMIT_ONLY=true; shift ;;
        --gene-group)  SINGLE_GENE_GROUP="$2"; shift 2 ;;
        --help|-h)
            head -22 "$0" | grep -E "^#" | sed 's/^# //;s/^#//'
            exit 0 ;;
        *)
            echo "ERROR: unknown option: $1" >&2
            exit 1 ;;
    esac
done

echo "========================================================================"
echo "STEP_2 burst (uniform 25 CPU / 150 GB / 18 h, moroz-b)"
echo "========================================================================"
echo "Started: $(date)"
echo ""
echo "Per-job resources:"
echo "  cpus = ${SLURM_CPUS}"
echo "  mem  = ${SLURM_MEM}"
echo "  time = ${SLURM_TIME}"
echo "  qos  = ${SLURM_QOS}"
echo "  acct = ${SLURM_ACCOUNT}"
echo "Tree methods: FastTree + IQ-TREE"
[ -n "${SINGLE_GENE_GROUP}" ] && echo "Filter: --gene-group ${SINGLE_GENE_GROUP}"
${DRY_RUN} && echo "MODE: DRY-RUN (no changes)"
echo ""

# ============================================================================
# Validate prerequisites
# ============================================================================

if [ ! -d "${STEP1_OTI}" ]; then
    echo "ERROR: STEP_1 output_to_input not found: ${STEP1_OTI}" >&2
    exit 1
fi

if [ ! -d "${STEP2_COPYME}" ]; then
    echo "ERROR: STEP_2 COPYME not found: ${STEP2_COPYME}" >&2
    exit 1
fi

mkdir -p "${STEP2_DIR}/slurm_logs"

# ============================================================================
# Iterate over completed STEP_1 gene groups
# ============================================================================

setup_count=0
submit_count=0
skip_count=0
error_count=0
total_count=0

for STEP1_GG_DIR in "${STEP1_OTI}"/gene_group-*/; do
    [ -d "${STEP1_GG_DIR}" ] || continue

    gene_group_dir_name=$(basename "${STEP1_GG_DIR}")
    sanitized_name="${gene_group_dir_name#gene_group-}"
    total_count=$((total_count + 1))

    if [ -n "${SINGLE_GENE_GROUP}" ] && [ "${sanitized_name}" != "${SINGLE_GENE_GROUP}" ]; then
        continue
    fi

    AGS_FILE=$(find -L "${STEP1_GG_DIR}" -maxdepth 1 -name "*.aa" 2>/dev/null | head -1)
    if [ -z "${AGS_FILE}" ]; then
        echo "  [no-AGS]  ${sanitized_name}"
        error_count=$((error_count + 1))
        continue
    fi

    GG_DIR="${STEP2_DIR}/gene_group-${sanitized_name}"
    WF="${GG_DIR}/workflow-RUN_01-phylogenetic_analysis"

    # ---- SETUP ----
    if ! ${SUBMIT_ONLY}; then
        if [ -d "${WF}" ]; then
            skip_count=$((skip_count + 1))
        else
            if ${DRY_RUN}; then
                setup_count=$((setup_count + 1))
            else
                mkdir -p "${GG_DIR}"
                cp -r "${STEP2_COPYME}" "${WF}"

                CONFIG="${WF}/START_HERE-user_config.yaml"
                # Set gene family name
                sed -i "s|name: \"innexin_pannexin\"|name: \"${sanitized_name}\"|" "${CONFIG}"
                # Enable iqtree (default is false)
                sed -i 's|^  iqtree: false|  iqtree: true|' "${CONFIG}"
                setup_count=$((setup_count + 1))
            fi
        fi
    fi

    # ---- SUBMIT ----
    if ! ${SETUP_ONLY}; then
        if ! ${DRY_RUN} && [ ! -d "${WF}" ]; then
            echo "  [no-workflow] ${sanitized_name}"
            error_count=$((error_count + 1))
            continue
        fi

        if ${DRY_RUN}; then
            submit_count=$((submit_count + 1))
        else
            job_name="s2u_hgnc_${sanitized_name:0:50}"
            sbatch \
                --job-name="${job_name}" \
                --account="${SLURM_ACCOUNT}" \
                --qos="${SLURM_QOS}" \
                --mem="${SLURM_MEM}" \
                --time="${SLURM_TIME}" \
                --cpus-per-task="${SLURM_CPUS}" \
                --output="${STEP2_DIR}/slurm_logs/step2_${sanitized_name}-%j.log" \
                --wrap="module load conda 2>/dev/null || true; conda activate ${CONDA_ENV} || { echo 'FATAL: conda activate failed'; exit 1; }; cd ${WF} && bash RUN-workflow.sh" \
                > /dev/null
            submit_count=$((submit_count + 1))
        fi
    fi
done

# ============================================================================
# Summary
# ============================================================================

echo ""
echo "========================================================================"
${DRY_RUN} && echo "DRY-RUN SUMMARY" || echo "SUMMARY"
echo "========================================================================"
echo "Total gene groups with completed STEP_1: ${total_count}"
${SUBMIT_ONLY} || echo "Set up:        ${setup_count}"
${SUBMIT_ONLY} || echo "Skipped:       ${skip_count} (workflow-RUN_01 already exists)"
${SETUP_ONLY}  || echo "Submitted:     ${submit_count}"
echo "Errors:        ${error_count}"
echo "SLURM logs:    ${STEP2_DIR}/slurm_logs/"
echo "Completed:     $(date)"
