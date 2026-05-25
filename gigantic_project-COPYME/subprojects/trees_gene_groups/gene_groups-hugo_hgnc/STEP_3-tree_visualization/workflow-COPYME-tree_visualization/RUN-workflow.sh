#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 May 24 | Purpose: Single user-runnable entry point for STEP_3 tree visualization (orchestrator across all gene groups)
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh - STEP_3 Tree Visualization Orchestrator
# =============================================================================
# Single user-runnable script. Invoke from a workflow-RUN_NN-tree_visualization/
# copy of this COPYME:
#     bash RUN-workflow.sh
#
# Reads START_HERE-user_config.yaml. Always orchestrator mode (creates and
# dispatches per-gene-group RUN_01 sub-runs at the STEP_3 parent level).
#
# Pipeline:
#   1. Create/heal per-workflow conda env once on the login node (if missing or broken)
#   2. For each gene group in gene_group_source_tsv with STEP_2 tree newick output:
#        - Set up gene_group-X/workflow-RUN_01-tree_visualization/ from this COPYME
#        - Customize per-gene-group YAML
#        - Skip if STEP_2 hasn't produced newicks for that gene group
#   3. Dispatch per execution_mode (local | slurm-standard | slurm-burst)
#
# STEP_3 rendering is soft-fail by design (render failure -> placeholder + exit 0).
# =============================================================================

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# =============================================================================
# Read flat top-level YAML keys
# =============================================================================
read_config() {
    local key="$1"
    local default="$2"
    local value=$(grep "^${key}:" START_HERE-user_config.yaml 2>/dev/null | head -1 | sed 's/^[^:]*: *//' | sed 's/^"//;s/"$//' | sed 's/ *#.*$//')
    echo "${value:-$default}"
}

EXECUTION_MODE=$(read_config "execution_mode" "local")
STEP0_SUMMARY=$(read_config "gene_group_source_tsv" "")
STEP2_OUTPUT_TO_INPUT=$(read_config "step2_output_to_input_dir" "")
LARGE_THRESHOLD=$(read_config "large_threshold" "50")

# Optional override manifest (empty = visualize all gene groups with STEP_2 newicks)
GENE_GROUPS_MANIFEST=$(read_config "gene_groups_manifest" "")

SLURM_ACCOUNT=$(read_config "slurm_account" "")
SLURM_QOS_STANDARD=$(read_config "slurm_qos_standard" "")
SLURM_QOS_BURST=$(read_config "slurm_qos_burst" "")

SMALL_CPUS=$(read_config "small_cpus" "2")
SMALL_MEM=$(read_config "small_memory_gb" "8")
SMALL_TIME=$(read_config "small_time_hours" "2")
SMALL_TIME_BURST=$(read_config "small_time_hours_burst" "12")
SMALL_BURST_BLOCK=$(read_config "small_burst_block_size" "50")

LARGE_CPUS=$(read_config "large_cpus" "2")
LARGE_MEM=$(read_config "large_memory_gb" "16")
LARGE_TIME=$(read_config "large_time_hours" "4")
LARGE_TIME_BURST=$(read_config "large_time_hours_burst" "24")
LARGE_BURST_BLOCK=$(read_config "large_burst_block_size" "20")

ENV_NAME="aiG-trees_gene_groups-visualization"
ENV_YML="ai/conda_environment.yml"

# =============================================================================
# Sanity-check inputs
# =============================================================================
if [ ! -f "${STEP0_SUMMARY}" ]; then
    echo "ERROR: STEP_0 summary TSV not found: ${STEP0_SUMMARY}" >&2
    exit 1
fi
if [ ! -d "${STEP2_OUTPUT_TO_INPUT}" ]; then
    echo "ERROR: STEP_2 output_to_input dir not found: ${STEP2_OUTPUT_TO_INPUT}" >&2
    echo "Run STEP_2 first." >&2
    exit 1
fi
if [ ! -f "${ENV_YML}" ]; then
    echo "ERROR: conda env spec not found: ${ENV_YML}" >&2
    exit 1
fi

# =============================================================================
# Create/heal conda env once on the login node
# =============================================================================
module load conda 2>/dev/null || true

if ! type conda &>/dev/null; then
    echo "ERROR: conda is not available. On HiPerGator: 'module load conda'." >&2
    exit 1
fi

# Self-heal pattern: detect broken env (dir exists but bin/python missing) and rebuild
ENV_PREFIX=$(conda env list 2>/dev/null | awk -v n="${ENV_NAME}" '$1==n {print $NF}')
if [ -n "${ENV_PREFIX}" ] && [ -d "${ENV_PREFIX}" ] && [ ! -x "${ENV_PREFIX}/bin/python" ]; then
    echo "Conda env '${ENV_NAME}' is broken (no bin/python). Removing and rebuilding..."
    conda env remove -n "${ENV_NAME}" -y 2>/dev/null || rm -rf "${ENV_PREFIX}"
    ENV_PREFIX=""
fi

if ! conda env list 2>/dev/null | grep -q "^${ENV_NAME} "; then
    echo "Conda env '${ENV_NAME}' not found. Creating once from ${ENV_YML}..."
    if command -v mamba &>/dev/null; then
        mamba env create -f "${ENV_YML}" -y
    else
        conda env create -f "${ENV_YML}" -y
    fi
    echo "Env '${ENV_NAME}' created."
else
    echo "Conda env '${ENV_NAME}' already exists. Skipping creation."
fi

# =============================================================================
# Phase 1: setup gene_group-X/workflow-RUN_01-tree_visualization dirs
# =============================================================================
STEP3_DIR="$(dirname "${SCRIPT_DIR}")"
mkdir -p "${STEP3_DIR}/slurm_logs"

# Build optional gene-groups whitelist (empty = visualize all gene groups with newicks).
# Default (YAML key empty OR manifest's first data line is 'all'): no filter.
# Override: TSV with column 'sanitized_name'; each value must match a row in
# STEP0_SUMMARY or orchestrator fails-fast.
GENE_GROUPS_WHITELIST=""
if [ -n "${GENE_GROUPS_MANIFEST}" ]; then
    GENE_GROUPS_MANIFEST_PATH="${SCRIPT_DIR}/${GENE_GROUPS_MANIFEST}"
    if [ ! -f "${GENE_GROUPS_MANIFEST_PATH}" ]; then
        echo "ERROR: gene_groups_manifest not found: ${GENE_GROUPS_MANIFEST_PATH}" >&2
        echo "  (resolved from YAML key gene_groups_manifest = '${GENE_GROUPS_MANIFEST}')" >&2
        exit 1
    fi
    WHITELIST_TMP="${STEP3_DIR}/.gene_groups_whitelist_$$.tsv"
    grep -vE '^\s*(#|$)' "${GENE_GROUPS_MANIFEST_PATH}" \
        | awk 'NR==1 && tolower($1) == "sanitized_name" {next} {print $1}' \
        | sort -u > "${WHITELIST_TMP}"
    if [ ! -s "${WHITELIST_TMP}" ]; then
        echo "ERROR: gene_groups_manifest is empty (no data rows): ${GENE_GROUPS_MANIFEST_PATH}" >&2
        rm -f "${WHITELIST_TMP}"
        exit 1
    fi
    if [ "$(wc -l < "${WHITELIST_TMP}")" = "1" ] && [ "$(cat "${WHITELIST_TMP}")" = "all" ]; then
        echo "Gene-groups manifest: 'all' sentinel — visualizing every entry of gene_group_source_tsv"
        rm -f "${WHITELIST_TMP}"
    else
        ALL_SANITIZED="${STEP3_DIR}/.all_sanitized_$$.tsv"
        tail -n +2 "${STEP0_SUMMARY}" | awk -F'\t' '{print $3}' | sort -u > "${ALL_SANITIZED}"
        MISSING_GG=$(comm -23 "${WHITELIST_TMP}" "${ALL_SANITIZED}")
        rm -f "${ALL_SANITIZED}"
        if [ -n "${MISSING_GG}" ]; then
            echo "ERROR: gene_groups_manifest names not found in gene_group_source_tsv:" >&2
            echo "${MISSING_GG}" | sed 's/^/  /' >&2
            rm -f "${WHITELIST_TMP}"
            exit 1
        fi
        GENE_GROUPS_WHITELIST="${WHITELIST_TMP}"
        whitelist_count=$(wc -l < "${GENE_GROUPS_WHITELIST}")
        echo "Gene-groups manifest: ${whitelist_count} gene groups whitelisted (from ${GENE_GROUPS_MANIFEST})"
    fi
fi

SMALL_GG=()
LARGE_GG=()

setup_count=0
skip_count=0
no_trees_count=0
total_count=0
filtered_count=0

while IFS=$'\t' read -r gene_group_id gene_group_name sanitized_name rgs_filename sequence_count; do
    total_count=$((total_count + 1))

    # Apply gene-groups whitelist if active
    if [ -n "${GENE_GROUPS_WHITELIST}" ]; then
        if ! grep -qx "${sanitized_name}" "${GENE_GROUPS_WHITELIST}"; then
            filtered_count=$((filtered_count + 1))
            continue
        fi
    fi

    # STEP_2 must have produced at least one newick for this gene group
    NEWICK_DIR="${STEP2_OUTPUT_TO_INPUT}/gene_group-${sanitized_name}"
    if [ ! -d "${NEWICK_DIR}" ] || ! ls "${NEWICK_DIR}"/*.fasttree "${NEWICK_DIR}"/*.treefile "${NEWICK_DIR}"/*.veryfasttree "${NEWICK_DIR}"/*.phylobayes.nwk &>/dev/null; then
        no_trees_count=$((no_trees_count + 1))
        continue
    fi

    DEST="${STEP3_DIR}/gene_group-${sanitized_name}/workflow-RUN_01-tree_visualization"

    if [ "$sequence_count" -gt "$LARGE_THRESHOLD" ] 2>/dev/null; then
        LARGE_GG+=("${sanitized_name}")
    else
        SMALL_GG+=("${sanitized_name}")
    fi

    if [ -d "${DEST}" ]; then
        skip_count=$((skip_count + 1))
        continue
    fi

    mkdir -p "${STEP3_DIR}/gene_group-${sanitized_name}"
    cp -r "${SCRIPT_DIR}" "${DEST}"

    CONFIG_FILE="${DEST}/START_HERE-user_config.yaml"
    sed -i "s|^  name: \"PLACEHOLDER\"|  name: \"${sanitized_name}\"|" "${CONFIG_FILE}"

    setup_count=$((setup_count + 1))
done < <(tail -n +2 "${STEP0_SUMMARY}")

rm -f "${GENE_GROUPS_WHITELIST}"

echo ""
if [ -n "${GENE_GROUPS_MANIFEST}" ]; then
    echo "Setup: ${setup_count} new, ${skip_count} already exist, ${filtered_count} filtered by manifest, ${no_trees_count} skipped (no STEP_2 newicks)"
else
    echo "Setup: ${setup_count} new, ${skip_count} already exist, ${no_trees_count} skipped (no STEP_2 newicks)"
fi
echo "Small gene groups (<= ${LARGE_THRESHOLD} RGS seqs): ${#SMALL_GG[@]}"
echo "Large gene groups (>  ${LARGE_THRESHOLD} RGS seqs): ${#LARGE_GG[@]}"
echo ""

if [ "${#SMALL_GG[@]}" -gt 0 ]; then
    SMALL_GG=($(printf '%s\n' "${SMALL_GG[@]}" | shuf))
fi
if [ "${#LARGE_GG[@]}" -gt 0 ]; then
    LARGE_GG=($(printf '%s\n' "${LARGE_GG[@]}" | shuf))
fi

# =============================================================================
# Phase 2: dispatch per execution_mode
# =============================================================================
# Per-gene-group render command (no nextflow; pure python via toytree)
render_cmd() {
    local dest="$1"
    echo "cd '${dest}' && python3 ai/scripts/001_ai-python-render_trees.py && python3 ai/scripts/002_ai-python-write_run_log.py"
}

case "${EXECUTION_MODE}" in
    local)
        echo "Execution mode: local (sequential)"
        conda activate "${ENV_NAME}" 2>/dev/null || true
        for gg in "${SMALL_GG[@]}" "${LARGE_GG[@]}"; do
            DEST="${STEP3_DIR}/gene_group-${gg}/workflow-RUN_01-tree_visualization"
            echo ""
            echo "[$(date)] Rendering locally: ${gg}"
            ( cd "${DEST}" && python3 ai/scripts/001_ai-python-render_trees.py && python3 ai/scripts/002_ai-python-write_run_log.py ) \
                || echo "  FAILED: ${gg}"
        done
        ;;

    slurm-standard)
        echo "Execution mode: slurm-standard (QOS=${SLURM_QOS_STANDARD})"
        for tier in small large; do
            if [ "$tier" = "small" ]; then
                arr=("${SMALL_GG[@]}")
                cpus="${SMALL_CPUS}"; mem="${SMALL_MEM}"; time_h="${SMALL_TIME}"
            else
                arr=("${LARGE_GG[@]}")
                cpus="${LARGE_CPUS}"; mem="${LARGE_MEM}"; time_h="${LARGE_TIME}"
            fi
            for gg in "${arr[@]}"; do
                DEST="${STEP3_DIR}/gene_group-${gg}/workflow-RUN_01-tree_visualization"
                wrap="module load conda 2>/dev/null || true; conda activate ${ENV_NAME}; $(render_cmd "${DEST}")"
                sbatch \
                    --job-name="s3_${tier}_${gg}" \
                    --account="${SLURM_ACCOUNT}" \
                    --qos="${SLURM_QOS_STANDARD}" \
                    --cpus-per-task="${cpus}" \
                    --mem="${mem}gb" \
                    --time="${time_h}:00:00" \
                    --output="${STEP3_DIR}/slurm_logs/s3_${tier}_${gg}-%j.log" \
                    --wrap="${wrap}"
            done
        done
        ;;

    slurm-burst)
        echo "Execution mode: slurm-burst (chunked, QOS=${SLURM_QOS_BURST})"
        for tier in small large; do
            if [ "$tier" = "small" ]; then
                arr=("${SMALL_GG[@]}")
                cpus="${SMALL_CPUS}"; mem="${SMALL_MEM}"; time_h="${SMALL_TIME_BURST}"; block="${SMALL_BURST_BLOCK}"
            else
                arr=("${LARGE_GG[@]}")
                cpus="${LARGE_CPUS}"; mem="${LARGE_MEM}"; time_h="${LARGE_TIME_BURST}"; block="${LARGE_BURST_BLOCK}"
            fi

            n=${#arr[@]}
            i=0
            block_n=0
            while [ "$i" -lt "$n" ]; do
                end=$((i + block))
                [ "$end" -gt "$n" ] && end="$n"
                block_n=$((block_n + 1))
                block_name="s3_${tier}_blk_$(printf '%02d' ${block_n})"

                runner="module load conda 2>/dev/null || true; conda activate ${ENV_NAME}; "
                j=$i
                while [ "$j" -lt "$end" ]; do
                    gg="${arr[$j]}"
                    DEST="${STEP3_DIR}/gene_group-${gg}/workflow-RUN_01-tree_visualization"
                    runner+="echo '----------'; echo \"[\$(date)] Rendering: ${gg}\"; "
                    runner+="( $(render_cmd "${DEST}") ) || echo \"FAILED: ${gg}\"; "
                    j=$((j + 1))
                done

                sbatch \
                    --job-name="${block_name}" \
                    --account="${SLURM_ACCOUNT}" \
                    --qos="${SLURM_QOS_BURST}" \
                    --cpus-per-task="${cpus}" \
                    --mem="${mem}gb" \
                    --time="${time_h}:00:00" \
                    --output="${STEP3_DIR}/slurm_logs/${block_name}-%j.log" \
                    --wrap="${runner}"

                i="$end"
            done
        done
        ;;

    *)
        echo "ERROR: Invalid execution_mode: ${EXECUTION_MODE}" >&2
        exit 1
        ;;
esac

echo ""
echo "========================================================================"
echo "Dispatch complete: $(date)"
echo "========================================================================"
