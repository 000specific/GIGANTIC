#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 May 24 | Purpose: Single user-runnable entry point for STEP_1 RBH/RBF homolog discovery (orchestrator across all gene groups)
# Human: Eric Edsinger

# =============================================================================
# RUN-workflow.sh - STEP_1 RBH/RBF Homolog Discovery Orchestrator
# =============================================================================
# Single user-runnable script for this STEP_1 workflow. Invoked from this
# COPYME directory:
#     bash RUN-workflow.sh
#
# Reads START_HERE-user_config.yaml. Always orchestrator mode (no per-gene-group
# invocation by the user; per-gene-group RUN_01 dirs are created from this
# COPYME and either run locally or sbatched by this script).
#
# Pipeline:
#   1. Create per-workflow conda env once on the login node (if missing)
#   2. Generate species_keeper_list from genomesDB BLAST DB dir
#   3. For each gene group in gene_group_source_tsv:
#        - Set up gene_group-X/workflow-RUN_01-rbh_rbf_homologs/ from this COPYME
#        - Customize INPUT_user/ and YAML per gene group
#        - Categorize as small (<= large_threshold seqs) or large
#   4. Dispatch per execution_mode:
#        local         - sequential nextflow runs
#        slurm-standard - 1 sbatch per gene group, standard QOS
#        slurm-burst    - chunk into blocks (burst_block_size per tier), 1 sbatch per block, burst QOS
# =============================================================================

set -e

# Resolve where this script lives
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# Disable NextFlow telemetry/update checks (prevents curl hangs on compute nodes)
export NXF_OFFLINE=true

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
RGS_FASTAS_DIR=$(read_config "rgs_fastas_dir" "")
LARGE_THRESHOLD=$(read_config "large_threshold" "50")
RESUME=$(read_config "resume" "false")

SLURM_ACCOUNT=$(read_config "slurm_account" "")
SLURM_QOS_STANDARD=$(read_config "slurm_qos_standard" "")
SLURM_QOS_BURST=$(read_config "slurm_qos_burst" "")

SMALL_CPUS=$(read_config "small_cpus" "2")
SMALL_MEM=$(read_config "small_memory_gb" "15")
SMALL_TIME=$(read_config "small_time_hours" "12")
SMALL_TIME_BURST=$(read_config "small_time_hours_burst" "96")
SMALL_BURST_BLOCK=$(read_config "small_burst_block_size" "10")

LARGE_CPUS=$(read_config "large_cpus" "8")
LARGE_MEM=$(read_config "large_memory_gb" "60")
LARGE_TIME=$(read_config "large_time_hours" "12")
LARGE_TIME_BURST=$(read_config "large_time_hours_burst" "96")
LARGE_BURST_BLOCK=$(read_config "large_burst_block_size" "3")

# Conda env name is fixed per the colocated conda_environment.yml
ENV_NAME="aiG-trees_gene_groups-rbh_rbf_homologs"
ENV_YML="ai/conda_environment.yml"

# =============================================================================
# Sanity-check inputs
# =============================================================================
if [ ! -f "${STEP0_SUMMARY}" ]; then
    echo "ERROR: STEP_0 summary TSV not found: ${STEP0_SUMMARY}" >&2
    echo "Set gene_group_source_tsv in START_HERE-user_config.yaml" >&2
    exit 1
fi
if [ ! -d "${RGS_FASTAS_DIR}" ]; then
    echo "ERROR: RGS FASTAs directory not found: ${RGS_FASTAS_DIR}" >&2
    echo "Set rgs_fastas_dir in START_HERE-user_config.yaml" >&2
    exit 1
fi
if [ ! -f "${ENV_YML}" ]; then
    echo "ERROR: conda env spec not found: ${ENV_YML}" >&2
    exit 1
fi

# Pick blast_databases_dir from nested YAML (extract any indented `blast_databases_dir:` under `inputs:`)
BLAST_DB_DIR_REL=$(awk '/^inputs:/{inblock=1;next} /^[^[:space:]]/{inblock=0} inblock && /^[[:space:]]+blast_databases_dir:/ {sub(/^[[:space:]]+blast_databases_dir:[[:space:]]*/, ""); gsub(/"/, ""); print; exit}' START_HERE-user_config.yaml)
if [ -z "${BLAST_DB_DIR_REL}" ]; then
    echo "ERROR: inputs.blast_databases_dir not set in START_HERE-user_config.yaml" >&2
    exit 1
fi
# YAML paths are relative to per-gene-group RUN_01 depth (sibling of orchestrator at
# STEP_1/gene_group-X/workflow-RUN_01-*). Resolve from that virtual sibling location.
BLAST_DB_DIR=$(realpath -m "$(dirname "${SCRIPT_DIR}")/gene_group-PLACEHOLDER/workflow-RUN_01-rbh_rbf_homologs/${BLAST_DB_DIR_REL}" 2>/dev/null)
if [ ! -d "${BLAST_DB_DIR}" ]; then
    echo "ERROR: inputs.blast_databases_dir not found or invalid:" >&2
    echo "  YAML value:     ${BLAST_DB_DIR_REL}" >&2
    echo "  Resolved path:  ${BLAST_DB_DIR}" >&2
    exit 1
fi

# =============================================================================
# Create conda env once on the login node (first thing, before any sbatch)
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
# Generate species_keeper_list from genomesDB
# =============================================================================
STEP1_DIR="$(dirname "${SCRIPT_DIR}")"   # parent: .../STEP_1-homolog_discovery
SPECIES_KEEPER_LIST="${STEP1_DIR}/.species_keeper_list_$$.tsv"

ls "${BLAST_DB_DIR}"/*.aa 2>/dev/null | while read f; do
    basename "$f" | sed 's/-T1-proteome\.aa$//' | awk -F'_' '{print $(NF-1)"_"$NF}'
done | sort -u > "${SPECIES_KEEPER_LIST}"

species_count=$(wc -l < "${SPECIES_KEEPER_LIST}")
echo "Species keeper list: ${species_count} species from genomesDB"

mkdir -p "${STEP1_DIR}/slurm_logs"

# =============================================================================
# Phase 1: setup gene_group-X/workflow-RUN_01-*/ directories
# =============================================================================
SMALL_GG=()
LARGE_GG=()

setup_count=0
skip_count=0
error_count=0
total_count=0

RGS_SPECIES_MAP_SOURCE="${SCRIPT_DIR}/INPUT_user/rgs_species_map.tsv"

while IFS=$'\t' read -r gene_group_id gene_group_name sanitized_name rgs_filename sequence_count; do
    total_count=$((total_count + 1))

    DEST="${STEP1_DIR}/gene_group-${sanitized_name}/workflow-RUN_01-rbh_rbf_homologs"
    RGS_SOURCE="${RGS_FASTAS_DIR}/${rgs_filename}"

    if [ ! -f "${RGS_SOURCE}" ]; then
        echo "  ERROR: RGS not found: ${rgs_filename}" >&2
        error_count=$((error_count + 1))
        continue
    fi

    if [ "$sequence_count" -gt "$LARGE_THRESHOLD" ] 2>/dev/null; then
        LARGE_GG+=("${sanitized_name}")
    else
        SMALL_GG+=("${sanitized_name}")
    fi

    if [ -d "${DEST}" ]; then
        skip_count=$((skip_count + 1))
        continue
    fi

    # Create gene_group-X/workflow-RUN_01-* from this COPYME
    mkdir -p "${STEP1_DIR}/gene_group-${sanitized_name}"
    cp -r "${SCRIPT_DIR}" "${DEST}"

    # Drop the COPYME's INPUT_user contents and seed with per-gene-group inputs
    mkdir -p "${DEST}/INPUT_user"
    rm -f "${DEST}/INPUT_user/"*.aa  2>/dev/null
    cp -L "${RGS_SOURCE}" "${DEST}/INPUT_user/${rgs_filename}"
    cp "${SPECIES_KEEPER_LIST}" "${DEST}/INPUT_user/species_keeper_list.tsv"
    if [ -f "${RGS_SPECIES_MAP_SOURCE}" ]; then
        cp "${RGS_SPECIES_MAP_SOURCE}" "${DEST}/INPUT_user/rgs_species_map.tsv"
    fi

    # Patch the per-RUN_01 YAML
    CONFIG_FILE="${DEST}/START_HERE-user_config.yaml"
    sed -i "s|^  name: \"PLACEHOLDER\"|  name: \"${sanitized_name}\"|" "${CONFIG_FILE}"
    sed -i "s|^  rgs_full_length_file: \"INPUT_user/PLACEHOLDER.aa\"|  rgs_full_length_file: \"INPUT_user/${rgs_filename}\"|" "${CONFIG_FILE}"

    # Flatten the per-RUN_01 YAML to .params.json for nextflow -params-file
    # (nextflow 26.x strict config parser disallows Groovy imports in nextflow.config)
    DEST="${DEST}" CONFIG_FILE="${CONFIG_FILE}" python3 - <<'PYTHON_FLATTEN'
import os, yaml, json
from pathlib import Path
dest = Path(os.environ['DEST']).resolve()
cfg_path = Path(os.environ['CONFIG_FILE'])
with open(cfg_path) as f:
    cfg = yaml.safe_load(f)

def resolve(rel):
    if rel is None: return None
    p = Path(rel)
    return str(p if p.is_absolute() else (dest / p).resolve())

gf = cfg.get('gene_family', {}) or {}
inp = cfg.get('inputs', {}) or {}
proj = cfg.get('project', {}) or {}
bl = cfg.get('blast', {}) or {}
out = cfg.get('output', {}) or {}

is_full = gf.get('rgs_sequence_is_full_length', True)
rgs_full = gf.get('rgs_full_length_file')
rgs_sub = gf.get('rgs_subsequence_file')

flat = {
    'gene_family': gf.get('name'),
    'rgs_full_length_file': rgs_full,
    'rgs_subsequence_file': rgs_sub,
    'rgs_sequence_is_full_length': bool(is_full),
    'rgs_file': rgs_full if is_full else rgs_sub,
    'include_orphan_rgs': bool(gf.get('include_orphan_rgs', False)),

    'species_keeper_list': inp.get('species_keeper_list', 'INPUT_user/species_keeper_list.tsv'),
    'rgs_species_map':     inp.get('rgs_species_map',     'INPUT_user/rgs_species_map.tsv'),
    'blast_databases_dir': resolve(inp.get('blast_databases_dir')),
    'rgs_genomes_dir':     resolve(inp.get('rgs_genomes_dir')),

    'project_database': proj.get('database', 'speciesN_T1-speciesN'),
    'project_name':     proj.get('name', 'GIGANTIC'),

    'blast_evalue':     str(bl.get('evalue', '1e-3')),
    'blast_threads':    int(bl.get('threads', 10)),
    'blast_conda_env':  bl.get('conda_env', 'blast'),

    'output_dir':  out.get('base_dir', 'OUTPUT_pipeline'),

    # Per-label NextFlow process resources (Layer 3 - inside SLURM block)
    # Threaded directly into nextflow.config withLabel: blocks via params.*
    'local_cpus':       int(cfg.get('local_cpus', 2)),
    'local_memory_gb':  int(cfg.get('local_memory_gb', 10)),
    'local_time_hours': int(cfg.get('local_time_hours', 1)),
    'blast_cpus':       int(cfg.get('blast_cpus', 10)),
    'blast_memory_gb':  int(cfg.get('blast_memory_gb', 75)),
    'blast_time_hours': int(cfg.get('blast_time_hours', 24)),
}
with open(dest / '.params.json', 'w') as f:
    json.dump(flat, f, indent=2)
PYTHON_FLATTEN

    setup_count=$((setup_count + 1))
done < <(tail -n +2 "${STEP0_SUMMARY}")

rm -f "${SPECIES_KEEPER_LIST}"

echo ""
echo "Setup: ${setup_count} new, ${skip_count} already exist, ${error_count} errors"
echo "Small gene groups (<= ${LARGE_THRESHOLD} seqs): ${#SMALL_GG[@]}"
echo "Large gene groups (>  ${LARGE_THRESHOLD} seqs): ${#LARGE_GG[@]}"
echo ""

# Shuffle so slow groups spread evenly across blocks
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

# Build the per-gene-group nextflow invocation as a reusable shell snippet.
# Runs inside the gene-group's workflow-RUN_01 directory; uses the activated env.
# Uses -params-file .params.json (flattened from START_HERE-user_config.yaml at setup time).
nextflow_run_cmd() {
    local dest="$1"
    echo "cd '${dest}' && nextflow run ai/main.nf ${RESUME_FLAG} -c ai/nextflow.config -params-file .params.json"
}

case "${EXECUTION_MODE}" in
    local)
        echo "Execution mode: local (sequential)"
        conda activate "${ENV_NAME}" 2>/dev/null || true
        for gg in "${SMALL_GG[@]}" "${LARGE_GG[@]}"; do
            DEST="${STEP1_DIR}/gene_group-${gg}/workflow-RUN_01-rbh_rbf_homologs"
            echo ""
            echo "------------------------------------------------------------"
            echo "[$(date)] Running locally: ${gg}"
            echo "------------------------------------------------------------"
            ( cd "${DEST}" && nextflow run ai/main.nf ${RESUME_FLAG} -c ai/nextflow.config -params-file .params.json ) \
                || echo "  FAILED: ${gg}"
        done
        ;;

    slurm-standard)
        echo "Execution mode: slurm-standard (1 sbatch per gene group, QOS=${SLURM_QOS_STANDARD})"
        for tier in small large; do
            if [ "$tier" = "small" ]; then
                arr=("${SMALL_GG[@]}")
                cpus="${SMALL_CPUS}"; mem="${SMALL_MEM}"; time_h="${SMALL_TIME}"
            else
                arr=("${LARGE_GG[@]}")
                cpus="${LARGE_CPUS}"; mem="${LARGE_MEM}"; time_h="${LARGE_TIME}"
            fi
            for gg in "${arr[@]}"; do
                DEST="${STEP1_DIR}/gene_group-${gg}/workflow-RUN_01-rbh_rbf_homologs"
                wrap="module load conda 2>/dev/null || true; conda activate ${ENV_NAME}; $(nextflow_run_cmd "${DEST}")"
                sbatch \
                    --job-name="s1_${tier}_${gg}" \
                    --account="${SLURM_ACCOUNT}" \
                    --qos="${SLURM_QOS_STANDARD}" \
                    --cpus-per-task="${cpus}" \
                    --mem="${mem}gb" \
                    --time="${time_h}:00:00" \
                    --output="${STEP1_DIR}/slurm_logs/s1_${tier}_${gg}-%j.log" \
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
                block_name="s1_${tier}_blk_$(printf '%02d' ${block_n})"

                # Build runner: sequential nextflow per gene group in the block
                runner="module load conda 2>/dev/null || true; conda activate ${ENV_NAME}; "
                j=$i
                while [ "$j" -lt "$end" ]; do
                    gg="${arr[$j]}"
                    DEST="${STEP1_DIR}/gene_group-${gg}/workflow-RUN_01-rbh_rbf_homologs"
                    runner+="echo '----------'; echo \"[\$(date)] Starting: ${gg}\"; "
                    runner+="( $(nextflow_run_cmd "${DEST}") ) || echo \"FAILED: ${gg}\"; "
                    j=$((j + 1))
                done

                sbatch \
                    --job-name="${block_name}" \
                    --account="${SLURM_ACCOUNT}" \
                    --qos="${SLURM_QOS_BURST}" \
                    --cpus-per-task="${cpus}" \
                    --mem="${mem}gb" \
                    --time="${time_h}:00:00" \
                    --output="${STEP1_DIR}/slurm_logs/${block_name}-%j.log" \
                    --wrap="${runner}"

                i="$end"
            done
        done
        ;;

    *)
        echo "ERROR: Invalid execution_mode: ${EXECUTION_MODE}" >&2
        echo "Must be one of: local, slurm-standard, slurm-burst" >&2
        exit 1
        ;;
esac

echo ""
echo "========================================================================"
echo "Dispatch complete: $(date)"
echo "========================================================================"
