#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 May 04 | Purpose: Run hotspots BLOCK_identify_hotspots workflow
# Human: Eric Edsinger

################################################################################
# GIGANTIC hotspots - BLOCK_identify_hotspots (Local)
################################################################################
#
# PURPOSE:
# Detect chromosomal hotspots (clusters of paralogous gene copies) per species.
# Consumes per-species self-BLAST reports from BLOCK_self_blast and user-
# provided gene coordinate TSVs.
#
# USAGE:
#   bash RUN-workflow.sh        # local
#   sbatch RUN-workflow.sbatch  # SLURM
#
# BEFORE RUNNING:
# 1. BLOCK_self_blast must have completed (look for symlinked reports in
#    ../../output_to_input/BLOCK_self_blast/self_blast_reports/)
# 2. Provide per-species gene coordinate TSVs in the location set by
#    inputs.gene_coordinates_dir in START_HERE-user_config.yaml.
#    Default: ../../research_notebook/research_user/gene_coordinates/
#    File naming: <Genus_species>-gene_coordinates.tsv
#    Required columns: Source_Gene_ID, Seqid, Gene_Start, Gene_End, Strand
# 3. Edit START_HERE-user_config.yaml — at minimum confirm:
#    - execution_mode (local | slurm)
#    - inputs.* paths
#    - hotspot.window_size (default 20)
#    - hotspot.evalue_threshold (default 1e-60)
#
################################################################################

set -uo pipefail

echo "========================================================================"
echo "GIGANTIC hotspots BLOCK_identify_hotspots Pipeline"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Activate conda env (parsed from yaml)
# ============================================================================

if [ ! -f "START_HERE-user_config.yaml" ]; then
    echo "ERROR: START_HERE-user_config.yaml not found!"
    exit 1
fi

module load conda 2>/dev/null || true

CONDA_ENV=$( python3 -c "
import re
with open('START_HERE-user_config.yaml') as f:
    for line in f:
        m = re.match(r'\s*environment:\s*[\"]?([^\"\s#]+)', line)
        if m:
            print(m.group(1))
            break
" 2>/dev/null )
CONDA_ENV="${CONDA_ENV:-ai_gigantic_hotspots}"

if conda activate "${CONDA_ENV}" 2>/dev/null; then
    echo "Activated conda environment: ${CONDA_ENV}"
else
    if ! command -v nextflow &> /dev/null || ! command -v python3 &> /dev/null; then
        echo "ERROR: conda env '${CONDA_ENV}' not found and required tools (nextflow, python3) are not on PATH."
        exit 1
    fi
    echo "Using NextFlow + python from PATH"
fi

# ============================================================================
# Parse yaml → env vars (NextFlow 26+ strict config DSL needs them this way)
# ============================================================================

eval "$( python3 - <<'PYTHON_EOF'
import sys, re

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

def emit(name, value):
    v = str(value).replace("'", "'\\''")
    print(f"export {name}='{v}'")

emit('GIGANTIC_EXEC_MODE',                  get(cfg, 'execution_mode', default='local'))
emit('GIGANTIC_QUEUE_SIZE',                 get(cfg, 'slurm_queue_size', default='70'))
emit('GIGANTIC_SLURM_ACCOUNT',              get(cfg, 'slurm_account', default='moroz'))
emit('GIGANTIC_SLURM_QOS',                  get(cfg, 'slurm_qos', default='moroz'))
emit('GIGANTIC_IDENTIFY_CPUS',              get(cfg, 'resources', 'identify_hotspots_per_species', 'cpus', default='2'))
emit('GIGANTIC_IDENTIFY_MEMORY_GB',         get(cfg, 'resources', 'identify_hotspots_per_species', 'memory_gb', default='8'))
emit('GIGANTIC_IDENTIFY_TIME_HOURS',        get(cfg, 'resources', 'identify_hotspots_per_species', 'time_hours', default='1'))
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

if [ ! -f "INPUT_user/gigantic_species_list.txt" ]; then
    echo "ERROR: INPUT_user/gigantic_species_list.txt not found!"
    echo "  Copy from genomesDB/output_to_input/STEP_4-create_final_species_set/"
    echo "  speciesN_gigantic_species_list/species_list.txt"
    exit 1
fi
echo "  [OK] gigantic_species_list.txt found"

# Sanity check that BLOCK_self_blast outputs exist
if [ ! -d "../../output_to_input/BLOCK_self_blast/self_blast_reports" ]; then
    echo ""
    echo "WARNING: ../../output_to_input/BLOCK_self_blast/self_blast_reports/ not found!"
    echo "  BLOCK_self_blast must complete before this BLOCK can run."
    echo "  (If your reports live elsewhere, edit inputs.self_blast_reports_dir in the yaml.)"
    echo ""
fi

echo ""

# ============================================================================
# Run NextFlow pipeline
# ============================================================================

echo "Running NextFlow pipeline..."
echo ""

RESUME_FLAG=""
if [ "${GIGANTIC_RESUME}" == "true" ]; then
    RESUME_FLAG="-resume"
    echo "  resume: enabled"
fi

PROFILE_FLAG=""
if [ "${GIGANTIC_EXEC_MODE}" == "slurm" ]; then
    PROFILE_FLAG="-profile slurm"
fi

nextflow run ai/main.nf -c ai/nextflow.config -params-file START_HERE-user_config.yaml ${PROFILE_FLAG} ${RESUME_FLAG}
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "========================================================================"
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "========================================================================"
    exit $EXIT_CODE
fi

# ============================================================================
# Symlink per-species hotspots into output_to_input/ for any future BLOCK
# ============================================================================

echo ""
echo "Creating symlinks for downstream BLOCKs..."

SHARED_DIR="../../output_to_input/BLOCK_identify_hotspots/hotspots"
mkdir -p "${SHARED_DIR}"

for old_link in "${SHARED_DIR}"/3_ai-hotspots-*.tsv; do
    if [ -L "${old_link}" ]; then
        rm "${old_link}"
    fi
done

WORKFLOW_NAME="$( basename "${SCRIPT_DIR}" )"

for hs in OUTPUT_pipeline/3-output/3_ai-hotspots-*.tsv; do
    if [ -f "${hs}" ]; then
        hs_name=$( basename "${hs}" )
        ln -sf "../../../BLOCK_identify_hotspots/${WORKFLOW_NAME}/OUTPUT_pipeline/3-output/${hs_name}" \
            "${SHARED_DIR}/${hs_name}"
    fi
done

echo "  output_to_input/BLOCK_identify_hotspots/hotspots/ -> symlinks created"

echo ""
echo "========================================================================"
echo "SUCCESS! BLOCK_identify_hotspots pipeline complete."
echo ""
echo "Per-species hotspots:"
echo "  OUTPUT_pipeline/3-output/3_ai-hotspots-<Genus_species>.tsv"
echo ""
echo "Cross-species summary:"
echo "  OUTPUT_pipeline/4-output/4_ai-cross_species_hotspot_summary.tsv"
echo "  OUTPUT_pipeline/4-output/4_ai-project_hotspot_summary.tsv"
echo ""
echo "Excluded species:"
echo "  OUTPUT_pipeline/1-output/1_ai-excluded_species.tsv"
echo "========================================================================"
echo "Completed: $(date)"

conda deactivate 2>/dev/null || true
