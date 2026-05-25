#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 May 04 | Purpose: Run hotspots self-BLAST workflow (local entrypoint)
# Human: Eric Edsinger

################################################################################
# GIGANTIC hotspots - BLOCK_self_blast (Local)
################################################################################
#
# PURPOSE:
# Run blastp of each species' proteome against itself, fanning the per-chunk
# blastp tasks out across SLURM (or local CPUs). Produces one tabular self-
# BLAST report per species — the input to BLOCK_identify_hotspots.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Copy the GIGANTIC species list into INPUT_user/gigantic_species_list.txt
# 2. Edit START_HERE-user_config.yaml — at minimum review:
#    - execution_mode (slurm | local)
#    - inputs.proteomes_dir and inputs.blast_db_dir
#    - slurm_account / slurm_qos (if execution_mode == slurm)
#
# FOR SLURM CLUSTERS:
#   sbatch RUN-workflow.sbatch
#
# WHAT THIS DOES:
# 1. Validates inputs (each species has a proteome AND a pre-built blastp DB)
# 2. Chunks each proteome into ~50 query chunks (~600 sequences each)
# 3. Fans the chunks out across SLURM array on burst QOS (or local CPUs)
# 4. Concatenates per-chunk reports into per-species self-BLAST reports
# 5. Writes a timestamped run log to ai/logs/
#
################################################################################

set -uo pipefail

echo "========================================================================"
echo "GIGANTIC hotspots BLOCK_self_blast Pipeline (Local)"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Parse START_HERE-user_config.yaml into env vars
# ============================================================================
# nextflow.config reads these (NextFlow 26+ strict config DSL forbids
# variable declarations in nextflow.config, so we pre-export from yaml here).
# Users continue to edit only the yaml.

if [ ! -f "START_HERE-user_config.yaml" ]; then
    echo "ERROR: START_HERE-user_config.yaml not found!"
    exit 1
fi

# Load conda first so python3 (with PyYAML or fallback) is available
module load conda 2>/dev/null || true

# GIGANTIC env naming convention: aiG-<subproject>-<block_or_step>-<optional_details>
# Subproject-shared env: BOTH hotspots BLOCKs use the same env.
ENV_NAME="aiG-hotspots"
ENV_YML="ai/conda_environment.yml"

if ! command -v conda &> /dev/null; then
    echo "ERROR: conda not found! On HPC (HiPerGator): module load conda"
    exit 1
fi

env_is_complete() {
    local env_prefix=$(conda env list 2>/dev/null | awk -v n="${ENV_NAME}" '$1==n {print $NF}')
    if [ -z "${env_prefix}" ]; then return 1; fi
    if [ ! -x "${env_prefix}/bin/python" ]; then return 1; fi
    return 0
}

if ! env_is_complete; then
    if conda env list 2>/dev/null | awk '{print $1}' | grep -q "^${ENV_NAME}$"; then
        echo "Removing broken/incomplete env '${ENV_NAME}'..."
        conda env remove -n "${ENV_NAME}" -y 2>&1 | tail -3
    fi
    echo "Creating conda env '${ENV_NAME}' from ${ENV_YML}..."
    if [ ! -f "${ENV_YML}" ]; then
        echo "ERROR: Environment spec not found at: ${ENV_YML}"
        exit 1
    fi
    if command -v mamba &> /dev/null; then
        mamba env create -f "${ENV_YML}" -y
    else
        conda env create -f "${ENV_YML}" -y
    fi
    if ! env_is_complete; then
        echo "ERROR: Environment creation failed."
        exit 1
    fi
fi

if conda activate "${ENV_NAME}" 2>/dev/null; then
    echo "Activated conda environment: ${ENV_NAME}"
else
    echo "WARNING: Could not activate '${ENV_NAME}'. Continuing with current environment."
fi

if ! command -v nextflow &> /dev/null; then
    module load nextflow 2>/dev/null || true
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: NextFlow not available!"
        exit 1
    fi
fi

# Parse yaml into env vars (PyYAML is widely available; fallback to text parse)
eval "$( python3 - <<'PYTHON_EOF'
import sys, re

# Try PyYAML first; fall back to simple regex parser if unavailable
try:
    import yaml
    with open('START_HERE-user_config.yaml') as f:
        cfg = yaml.safe_load(f) or {}
    def get(d, *keys, default=''):
        cur = d
        for k in keys:
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[ k ]
        return cur if cur is not None else default
except Exception:
    # Minimal fallback: extract a few flat keys via regex (best effort)
    cfg = {}
    cur_section = None
    with open('START_HERE-user_config.yaml') as f:
        for line in f:
            line = line.rstrip( '\n' )
            if not line.strip() or line.lstrip().startswith( '#' ):
                continue
            m = re.match( r'^([a-zA-Z_]+):\s*$', line )
            if m:
                cur_section = m.group( 1 )
                cfg[ cur_section ] = {}
                continue
            m = re.match( r'^\s+([a-zA-Z_]+):\s*[\"]?([^\"#]+?)[\"]?\s*(?:#.*)?$', line )
            if m and cur_section is not None:
                cfg[ cur_section ][ m.group( 1 ) ] = m.group( 2 ).strip()
                continue
            m = re.match( r'^([a-zA-Z_]+):\s*[\"]?([^\"#]+?)[\"]?\s*(?:#.*)?$', line )
            if m:
                cfg[ m.group( 1 ) ] = m.group( 2 ).strip()
    def get(d, *keys, default=''):
        cur = d
        for k in keys:
            if not isinstance(cur, dict) or k not in cur:
                return default
            cur = cur[ k ]
        return cur if cur is not None else default

# Emit shell exports for nextflow.config
def emit(name, value):
    v = str(value).replace("'", "'\\''")
    print(f"export {name}='{v}'")

emit('GIGANTIC_EXEC_MODE',                  get(cfg, 'execution_mode', default='local'))
emit('GIGANTIC_QUEUE_SIZE',                 get(cfg, 'slurm_queue_size', default='200'))
emit('GIGANTIC_BURST_ACCOUNT',              get(cfg, 'slurm_burst_account', default='moroz'))
emit('GIGANTIC_BURST_QOS',                  get(cfg, 'slurm_burst_qos', default='moroz-b'))
emit('GIGANTIC_BLASTP_CPUS',                get(cfg, 'resources', 'blastp_chunk', 'cpus', default='5'))
emit('GIGANTIC_BLASTP_MEMORY_GB',           get(cfg, 'resources', 'blastp_chunk', 'memory_gb', default='30'))
emit('GIGANTIC_BLASTP_TIME_HOURS',          get(cfg, 'resources', 'blastp_chunk', 'time_hours', default='5'))
emit('GIGANTIC_LOCAL_STEP_CPUS',            get(cfg, 'resources', 'local_step', 'cpus', default='4'))
emit('GIGANTIC_LOCAL_STEP_MEMORY_GB',       get(cfg, 'resources', 'local_step', 'memory_gb', default='30'))
emit('GIGANTIC_LOCAL_STEP_TIME_HOURS',      get(cfg, 'resources', 'local_step', 'time_hours', default='2'))
emit('GIGANTIC_RESUME',                     get(cfg, 'resume', default='false'))
PYTHON_EOF
)"

echo "  execution_mode: ${GIGANTIC_EXEC_MODE}"
echo "  resume: ${GIGANTIC_RESUME}"
echo ""

# ============================================================================
# Validate prerequisites
# ============================================================================

if [ ! -d "INPUT_user" ]; then
    echo "ERROR: INPUT_user/ directory not found!"
    exit 1
fi
echo "  [OK] INPUT_user/ directory found"

if [ ! -f "INPUT_user/gigantic_species_list.txt" ]; then
    echo ""
    echo "ERROR: INPUT_user/gigantic_species_list.txt not found!"
    echo "  Copy it from genomesDB/output_to_input/STEP_4-create_final_species_set/"
    echo "  speciesN_gigantic_species_list/species_list.txt"
    exit 1
fi
echo "  [OK] gigantic_species_list.txt found"
echo ""

# ============================================================================
# Run NextFlow pipeline
# ============================================================================

echo "Running NextFlow pipeline..."
echo ""

RESUME_FLAG=""
if [ "${GIGANTIC_RESUME}" == "true" ]; then
    RESUME_FLAG="-resume"
    echo "  resume: enabled (using NextFlow work/ cache)"
fi

PROFILE_FLAG=""
if [ "${GIGANTIC_EXEC_MODE}" == "slurm" ]; then
    PROFILE_FLAG="-profile slurm"
fi

# -params-file overrides params{} defaults in ai/nextflow.config with the
# user's yaml values. Profile slurm is added when execution_mode==slurm to
# enable the `array = 100` SLURM array batching directive.
nextflow run ai/main.nf -c ai/nextflow.config -params-file START_HERE-user_config.yaml ${PROFILE_FLAG} ${RESUME_FLAG}
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "========================================================================"
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "Check the logs above and OUTPUT_pipeline/*/N_ai-log-*.log for details."
    echo "========================================================================"
    exit $EXIT_CODE
fi

# ============================================================================
# Symlink per-species self-BLAST reports for downstream consumers
# ============================================================================

echo ""
echo "Creating symlinks for downstream BLOCKs..."

SHARED_DIR="../../output_to_input/BLOCK_self_blast/self_blast_reports"
mkdir -p "${SHARED_DIR}"

for old_link in "${SHARED_DIR}"/*-self_blast.tsv; do
    if [ -L "${old_link}" ]; then
        rm "${old_link}"
    fi
done

WORKFLOW_NAME="$( basename "${SCRIPT_DIR}" )"

for report in OUTPUT_pipeline/4-output/self_blast_reports/*-self_blast.tsv; do
    if [ -f "${report}" ]; then
        report_name=$( basename "${report}" )
        ln -sf "../../../BLOCK_self_blast/${WORKFLOW_NAME}/OUTPUT_pipeline/4-output/self_blast_reports/${report_name}" \
            "${SHARED_DIR}/${report_name}"
    fi
done

echo "  output_to_input/BLOCK_self_blast/self_blast_reports/ -> symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! BLOCK_self_blast pipeline complete."
echo ""
echo "Per-species self-BLAST reports:"
echo "  OUTPUT_pipeline/4-output/self_blast_reports/<Genus_species>-self_blast.tsv"
echo ""
echo "Symlinked for downstream BLOCKs:"
echo "  ../../output_to_input/BLOCK_self_blast/self_blast_reports/"
echo ""
echo "Excluded species (with reasons):"
echo "  OUTPUT_pipeline/1-output/1_ai-excluded_species.tsv"
echo "========================================================================"
echo "Completed: $(date)"

conda deactivate 2>/dev/null || true
