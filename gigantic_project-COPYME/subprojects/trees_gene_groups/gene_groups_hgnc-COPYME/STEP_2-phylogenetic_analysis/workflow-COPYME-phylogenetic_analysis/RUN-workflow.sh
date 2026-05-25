#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 May 24 | Purpose: Single user-runnable entry point for STEP_2 phylogenetic analysis (orchestrator across all gene groups)
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh - STEP_2 Phylogenetic Analysis Orchestrator
# =============================================================================
# Single user-runnable script. Invoke from a workflow-RUN_NN-phylogenetic_analysis/
# copy of this COPYME:
#     bash RUN-workflow.sh
#
# Reads START_HERE-user_config.yaml. Always orchestrator mode (creates and
# dispatches per-gene-group RUN_01 sub-runs at the STEP_2 parent level).
#
# Pipeline:
#   1. Create per-workflow conda env once on the login node (if missing)
#   2. For each gene group in gene_group_source_tsv with a STEP_1 AGS file:
#        - Set up gene_group-X/${PARENT_RUN_NAME}/ from this COPYME
#        - Customize per-gene-group YAML
#        - Categorize small/large by RGS sequence count from STEP_0 summary
#        - Skip gene groups whose AGS doesn't exist yet (STEP_1 not done for them)
#   3. Dispatch per execution_mode:
#        local          - sequential nextflow runs
#        slurm-standard - 1 sbatch per gene group, standard QOS
#        slurm-burst    - chunk into blocks, 1 sbatch per block, burst QOS
# =============================================================================

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# Multi-trial: per-gene-group sub-runs are named after THIS parent dir's basename.
# So workflow-RUN_1-syt_vamp_stx_trp/ at STEP_2 root creates
#   gene_group-X/workflow-RUN_1-syt_vamp_stx_trp/ per gene group.
# This lets multiple STEP_2 trials coexist without colliding.
PARENT_RUN_NAME="$( basename "${SCRIPT_DIR}" )"

# Fail-fast if invoked from the template (workflow-COPYME-*). Force the user to
# make a workflow-RUN_<N>-<label>/ sibling and run from there.
if [[ "${PARENT_RUN_NAME}" == workflow-COPYME-* ]]; then
    echo "ERROR: RUN-workflow.sh was invoked from the template '${PARENT_RUN_NAME}'." >&2
    echo "  Templates are not runnable directly. Make a copy and run from it:" >&2
    echo "    cp -r ${PARENT_RUN_NAME} workflow-RUN_1-<your-label>" >&2
    echo "    # Edit workflow-RUN_1-<your-label>/START_HERE-user_config.yaml as needed" >&2
    echo "    bash workflow-RUN_1-<your-label>/RUN-workflow.sh" >&2
    exit 1
fi

export NXF_OFFLINE=true

# =============================================================================
# Read flat top-level YAML keys
# =============================================================================
read_config() {
    local key="$1"
    local default="$2"
    # Order matters: strip comment BEFORE stripping quotes. Otherwise inline
    # comments containing quotes (e.g.,  key: "x"  # e.g. "y") confuse the
    # outer-quote strip and leak the comment's closing quote into the value.
    local value=$(grep "^${key}:" START_HERE-user_config.yaml 2>/dev/null | head -1 | sed 's/^[^:]*: *//' | sed 's/[[:space:]]*#.*$//' | sed 's/^"//;s/"$//')
    echo "${value:-$default}"
}

EXECUTION_MODE=$(read_config "execution_mode" "local")
STEP0_SUMMARY=$(read_config "gene_group_source_tsv" "")
STEP1_OUTPUT_TO_INPUT=$(read_config "step1_output_to_input_dir" "")
LARGE_THRESHOLD=$(read_config "large_threshold" "50")
RESUME=$(read_config "resume" "false")

# Optional override manifest (empty = process all gene groups with STEP_1 AGS)
GENE_GROUPS_MANIFEST=$(read_config "gene_groups_manifest" "")

SLURM_ACCOUNT=$(read_config "slurm_account" "")
SLURM_QOS_STANDARD=$(read_config "slurm_qos_standard" "")
SLURM_QOS_BURST=$(read_config "slurm_qos_burst" "")

SMALL_CPUS=$(read_config "small_cpus" "4")
SMALL_MEM=$(read_config "small_memory_gb" "16")
SMALL_TIME=$(read_config "small_time_hours" "12")
SMALL_TIME_BURST=$(read_config "small_time_hours_burst" "96")
SMALL_BURST_BLOCK=$(read_config "small_burst_block_size" "10")

LARGE_CPUS=$(read_config "large_cpus" "16")
LARGE_MEM=$(read_config "large_memory_gb" "64")
LARGE_TIME=$(read_config "large_time_hours" "24")
LARGE_TIME_BURST=$(read_config "large_time_hours_burst" "168")
LARGE_BURST_BLOCK=$(read_config "large_burst_block_size" "3")

ENV_NAME="aiG-trees_gene_groups-phylogenetic_analysis"
ENV_YML="ai/conda_environment.yml"

# =============================================================================
# Sanity-check inputs
# =============================================================================
if [ ! -f "${STEP0_SUMMARY}" ]; then
    echo "ERROR: STEP_0 summary TSV not found: ${STEP0_SUMMARY}" >&2
    exit 1
fi
if [ ! -d "${STEP1_OUTPUT_TO_INPUT}" ]; then
    echo "ERROR: STEP_1 output_to_input dir not found: ${STEP1_OUTPUT_TO_INPUT}" >&2
    echo "Run STEP_1 first." >&2
    exit 1
fi
if [ ! -f "${ENV_YML}" ]; then
    echo "ERROR: conda env spec not found: ${ENV_YML}" >&2
    exit 1
fi

# =============================================================================
# Create conda env once on the login node
# =============================================================================
module load conda 2>/dev/null || true

if ! type conda &>/dev/null; then
    echo "ERROR: conda is not available. On HiPerGator: 'module load conda'." >&2
    exit 1
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
# Phase 1: setup gene_group-X/${PARENT_RUN_NAME} dirs
# =============================================================================
STEP2_DIR="$(dirname "${SCRIPT_DIR}")"
mkdir -p "${STEP2_DIR}/slurm_logs"

# Build optional gene-groups whitelist (empty = process all from STEP0_SUMMARY).
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
    WHITELIST_TMP="${STEP2_DIR}/.gene_groups_whitelist_$$.tsv"
    grep -vE '^\s*(#|$)' "${GENE_GROUPS_MANIFEST_PATH}" \
        | awk 'NR==1 && tolower($1) == "sanitized_name" {next} {print $1}' \
        | sort -u > "${WHITELIST_TMP}"
    if [ ! -s "${WHITELIST_TMP}" ]; then
        echo "ERROR: gene_groups_manifest is empty (no data rows): ${GENE_GROUPS_MANIFEST_PATH}" >&2
        rm -f "${WHITELIST_TMP}"
        exit 1
    fi
    if [ "$(wc -l < "${WHITELIST_TMP}")" = "1" ] && [ "$(cat "${WHITELIST_TMP}")" = "all" ]; then
        echo "Gene-groups manifest: 'all' sentinel — processing every entry of gene_group_source_tsv"
        rm -f "${WHITELIST_TMP}"
    else
        ALL_SANITIZED="${STEP2_DIR}/.all_sanitized_$$.tsv"
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
no_ags_count=0
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

    AGS_DIR="${STEP1_OUTPUT_TO_INPUT}/gene_group-${sanitized_name}"
    if [ ! -d "${AGS_DIR}" ] || ! ls "${AGS_DIR}"/*.aa &>/dev/null; then
        no_ags_count=$((no_ags_count + 1))
        continue
    fi

    DEST="${STEP2_DIR}/gene_group-${sanitized_name}/${PARENT_RUN_NAME}"

    if [ "$sequence_count" -gt "$LARGE_THRESHOLD" ] 2>/dev/null; then
        LARGE_GG+=("${sanitized_name}")
    else
        SMALL_GG+=("${sanitized_name}")
    fi

    if [ -d "${DEST}" ]; then
        skip_count=$((skip_count + 1))
        continue
    fi

    mkdir -p "${STEP2_DIR}/gene_group-${sanitized_name}"
    cp -r "${SCRIPT_DIR}" "${DEST}"

    CONFIG_FILE="${DEST}/START_HERE-user_config.yaml"
    sed -i "s|^  name: \"PLACEHOLDER\"|  name: \"${sanitized_name}\"|" "${CONFIG_FILE}"

    # Flatten the per-RUN_01 YAML to .params.json for nextflow -params-file
    # (nextflow 26.x strict config parser disallows Groovy imports in nextflow.config)
    DEST="${DEST}" CONFIG_FILE="${CONFIG_FILE}" python3 - <<'PYTHON_FLATTEN'
import os, yaml, json
from pathlib import Path
dest = Path(os.environ['DEST']).resolve()
cfg_path = Path(os.environ['CONFIG_FILE'])
with open(cfg_path) as f:
    cfg = yaml.safe_load(f)

gf = cfg.get('gene_family', {}) or {}
inp = cfg.get('input', {}) or {}
proj = cfg.get('project', {}) or {}
tm = cfg.get('tree_methods', {}) or {}
phy = cfg.get('phylogenetics', {}) or {}
res = cfg.get('resources', {}) or {}
out = cfg.get('output', {}) or {}

def res_tier(name, key, default):
    return (res.get(name, {}) or {}).get(key, default)

flat = {
    'gene_family':         gf.get('name'),
    'output_dir':          out.get('base_dir', 'OUTPUT_pipeline'),
    'output_to_input_dir': inp.get('output_to_input_dir', '../../../../output_to_input'),
    'project_name':        proj.get('name', 'gene_groups'),
    'project_database':    proj.get('database', 'speciesN_T1-speciesN'),

    # Tree-method toggles
    'run_fasttree':     bool(tm.get('fasttree', True)),
    'run_iqtree':       bool(tm.get('iqtree', False)),
    'run_veryfasttree': bool(tm.get('veryfasttree', False)),
    'run_phylobayes':   bool(tm.get('phylobayes', False)),

    # MAFFT
    'mafft_maxiterate': int((phy.get('mafft', {}) or {}).get('maxiterate', 1000)),
    'mafft_bl':         int((phy.get('mafft', {}) or {}).get('bl', 45)),
    'mafft_threads':    int((phy.get('mafft', {}) or {}).get('threads', 50)),

    # ClipKit
    'clipkit_mode': (phy.get('clipkit', {}) or {}).get('mode', 'smart-gap'),

    # IQ-TREE
    'iqtree_model':     (phy.get('iqtree', {}) or {}).get('model', 'MFP'),
    'iqtree_bootstrap': int((phy.get('iqtree', {}) or {}).get('bootstrap', 2000)),
    'iqtree_alrt':      int((phy.get('iqtree', {}) or {}).get('alrt', 2000)),
    'iqtree_threads':   str((phy.get('iqtree', {}) or {}).get('threads', 'AUTO')),

    # VeryFastTree
    'veryfasttree_threads': int((phy.get('veryfasttree', {}) or {}).get('threads', 4)),

    # PhyloBayes
    'phylobayes_model':       (phy.get('phylobayes', {}) or {}).get('model', '-cat -gtr'),
    'phylobayes_generations': int((phy.get('phylobayes', {}) or {}).get('generations', 10000)),
    'phylobayes_burnin':      int((phy.get('phylobayes', {}) or {}).get('burnin', 2500)),
    'phylobayes_every':       int((phy.get('phylobayes', {}) or {}).get('every', 1)),

    # Per-tool resources (for nextflow.config process labels)
    'mafft_cpus':        int(res_tier('mafft', 'cpus', 50)),
    'mafft_memory_gb':   int(res_tier('mafft', 'memory_gb', 350)),
    'mafft_time_hours':  int(res_tier('mafft', 'time_hours', 168)),
    'clipkit_cpus':       int(res_tier('clipkit', 'cpus', 4)),
    'clipkit_memory_gb':  int(res_tier('clipkit', 'memory_gb', 16)),
    'clipkit_time_hours': int(res_tier('clipkit', 'time_hours', 4)),
    'fasttree_cpus':       int(res_tier('fasttree', 'cpus', 4)),
    'fasttree_memory_gb':  int(res_tier('fasttree', 'memory_gb', 16)),
    'fasttree_time_hours': int(res_tier('fasttree', 'time_hours', 4)),
    'iqtree_cpus':       int(res_tier('iqtree', 'cpus', 50)),
    'iqtree_memory_gb':  int(res_tier('iqtree', 'memory_gb', 350)),
    'iqtree_time_hours': int(res_tier('iqtree', 'time_hours', 168)),
    'veryfasttree_cpus':       int(res_tier('veryfasttree', 'cpus', 4)),
    'veryfasttree_memory_gb':  int(res_tier('veryfasttree', 'memory_gb', 16)),
    'veryfasttree_time_hours': int(res_tier('veryfasttree', 'time_hours', 4)),
    'phylobayes_cpus':       int(res_tier('phylobayes', 'cpus', 4)),
    'phylobayes_memory_gb':  int(res_tier('phylobayes', 'memory_gb', 32)),
    'phylobayes_time_hours': int(res_tier('phylobayes', 'time_hours', 336)),
}
with open(dest / '.params.json', 'w') as f:
    json.dump(flat, f, indent=2)
PYTHON_FLATTEN

    setup_count=$((setup_count + 1))
done < <(tail -n +2 "${STEP0_SUMMARY}")

rm -f "${GENE_GROUPS_WHITELIST}"

echo ""
if [ -n "${GENE_GROUPS_MANIFEST}" ]; then
    echo "Setup: ${setup_count} new, ${skip_count} already exist, ${filtered_count} filtered by manifest, ${no_ags_count} skipped (no STEP_1 AGS)"
else
    echo "Setup: ${setup_count} new, ${skip_count} already exist, ${no_ags_count} skipped (no STEP_1 AGS)"
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
RESUME_FLAG=""
if [ "${RESUME}" == "true" ]; then
    RESUME_FLAG="-resume"
fi

nextflow_run_cmd() {
    local dest="$1"
    echo "cd '${dest}' && nextflow run ai/main.nf ${RESUME_FLAG} -c ai/nextflow.config -params-file .params.json"
}

# =============================================================================
# Post-pipeline publish to output_to_input/
# After each per-gene-group nextflow run succeeds, symlink the tree newicks
# from OUTPUT_pipeline/5_*-output/ → output_to_input/<instance>/STEP_2-phylogenetic_analysis/${PARENT_RUN_NAME}/gene_group-<gg>/
# The ${PARENT_RUN_NAME} segment isolates this trial's outputs from other STEP_2
# trials (e.g., a different gene-group set, or different tree methods).
# STEP_3 selects which trial to consume via the step2_run_name YAML key.
# =============================================================================
INSTANCE_NAME="$( basename "$( dirname "${STEP2_DIR}" )" )"
OTI_INSTANCE_DIR="$( cd "${STEP2_DIR}/../../output_to_input" 2>/dev/null && pwd )/${INSTANCE_NAME}"
if [ -z "$( cd "${STEP2_DIR}/../../output_to_input" 2>/dev/null && pwd )" ]; then
    OTI_INSTANCE_DIR="$( realpath -m "${STEP2_DIR}/../../output_to_input/${INSTANCE_NAME}" )"
fi

oti_publish_step2() {
    local gg="$1"
    local dest="$2"
    local target="${OTI_INSTANCE_DIR}/STEP_2-phylogenetic_analysis/${PARENT_RUN_NAME}/gene_group-${gg}"
    # Newicks live in 5_a-output/, 5_b-output/, 5_c-output/, 5_d-output/ depending on which tree methods ran.
    # Explicit destination filename (not 'TARGET/') — the trailing-slash behavior of GNU coreutils
    # ln is unreliable on the /blue network FS.
    # The trailing 'true' guarantees exit 0 even when the LAST glob pattern
    # in the for loop doesn't match (which leaves [ -f "$f" ] returning 1 on
    # the final iteration). Without it, an enabled-fasttree-only run would
    # falsely report FAILED at the wrap layer despite NextFlow succeeding.
    echo "mkdir -p '${target}' && for f in '${dest}/OUTPUT_pipeline/5_'*-output/*.fasttree '${dest}/OUTPUT_pipeline/5_'*-output/*.treefile '${dest}/OUTPUT_pipeline/5_'*-output/*.veryfasttree '${dest}/OUTPUT_pipeline/5_'*-output/*.phylobayes.nwk; do [ -f \"\$f\" ] && ln -sf \"\$f\" \"${target}/\$( basename \"\$f\" )\"; done; true"
}

case "${EXECUTION_MODE}" in
    local)
        echo "Execution mode: local (sequential)"
        conda activate "${ENV_NAME}" 2>/dev/null || true
        for gg in "${SMALL_GG[@]}" "${LARGE_GG[@]}"; do
            DEST="${STEP2_DIR}/gene_group-${gg}/${PARENT_RUN_NAME}"
            echo ""
            echo "[$(date)] Running locally: ${gg}"
            ( cd "${DEST}" && nextflow run ai/main.nf ${RESUME_FLAG} -c ai/nextflow.config -params-file .params.json && eval "$(oti_publish_step2 "${gg}" "${DEST}")" ) \
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
                DEST="${STEP2_DIR}/gene_group-${gg}/${PARENT_RUN_NAME}"
                wrap="module load conda 2>/dev/null || true; conda activate ${ENV_NAME}; ( $(nextflow_run_cmd "${DEST}") && $(oti_publish_step2 "${gg}" "${DEST}") ) || echo \"FAILED: ${gg}\""
                sbatch \
                    --job-name="s2_${tier}_${gg}" \
                    --account="${SLURM_ACCOUNT}" \
                    --qos="${SLURM_QOS_STANDARD}" \
                    --cpus-per-task="${cpus}" \
                    --mem="${mem}gb" \
                    --time="${time_h}:00:00" \
                    --output="${STEP2_DIR}/slurm_logs/s2_${tier}_${gg}-%j.log" \
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
                block_name="s2_${tier}_blk_$(printf '%02d' ${block_n})"

                runner="module load conda 2>/dev/null || true; conda activate ${ENV_NAME}; "
                j=$i
                while [ "$j" -lt "$end" ]; do
                    gg="${arr[$j]}"
                    DEST="${STEP2_DIR}/gene_group-${gg}/${PARENT_RUN_NAME}"
                    runner+="echo '----------'; echo \"[\$(date)] Starting: ${gg}\"; "
                    runner+="( $(nextflow_run_cmd "${DEST}") && $(oti_publish_step2 "${gg}" "${DEST}") ) || echo \"FAILED: ${gg}\"; "
                    j=$((j + 1))
                done

                sbatch \
                    --job-name="${block_name}" \
                    --account="${SLURM_ACCOUNT}" \
                    --qos="${SLURM_QOS_BURST}" \
                    --cpus-per-task="${cpus}" \
                    --mem="${mem}gb" \
                    --time="${time_h}:00:00" \
                    --output="${STEP2_DIR}/slurm_logs/${block_name}-%j.log" \
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
