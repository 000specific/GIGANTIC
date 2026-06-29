#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 April 18 | Purpose: Run moroz_innovations_analysis (innovations + origins-at-clade)
# Human: Eric Edsinger

################################################################################
# GIGANTIC moroz_innovations_analysis
################################################################################
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Edit START_HERE-user_config.yaml:
#    - run_label, species_set_name
#    - target_clades (bare names)
#    - target_structures
#    - feature_sources paths (ortho + annotation OCL outputs)
#    - species_tree_source (clade_species_mappings TSV)
#    - execution_mode ("local" or "slurm")
#
# WHAT THIS DOES:
# - Activates (or creates) conda env aiG-moroz_innovations-analysis
# - Runs Script 001 which computes per (feature_type, structure, clade):
#     innovations_any, innovations_all, origins_at_clade tables
#
# OUTPUT:
#   OUTPUT_pipeline/{structure_id}/1-output/
#     1_ai-{structure_id}_innovations_any-{ortho|anno}.tsv
#     1_ai-{structure_id}_innovations_all-{ortho|anno}.tsv
#     1_ai-{structure_id}_origins_at_clade-{ortho|anno}.tsv
#
################################################################################

echo "========================================================================"
echo "GIGANTIC moroz_innovations_analysis"
echo "========================================================================"
echo "Started: $(date)"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Read execution_mode from config (flat YAML grep)
# ============================================================================

read_config() {
    local value=$(grep "^${1}:" START_HERE-user_config.yaml 2>/dev/null | head -1 | sed 's/^[^:]*: *//' | sed 's/^"//;s/"$//')
    echo "${value:-$2}"
}

EXECUTION_MODE=$(read_config "execution_mode" "local")

# ============================================================================
# SLURM self-submission (optional, matches annotations_X_ocl pattern)
# ============================================================================

if [ "${EXECUTION_MODE}" == "slurm" ] && [ -z "${SLURM_JOB_ID}" ]; then
    SLURM_ACCOUNT=$(read_config "slurm_account" "moroz")
    SLURM_QOS=$(read_config "slurm_qos" "moroz")
    CPUS=$(read_config "cpus" "2")
    MEMORY_GB=$(read_config "memory_gb" "16")
    TIME_HOURS=$(read_config "time_hours" "2")

    mkdir -p slurm_logs

    sbatch \
        --job-name=moroz_innovations \
        --account="${SLURM_ACCOUNT}" \
        --qos="${SLURM_QOS}" \
        --cpus-per-task="${CPUS}" \
        --mem="${MEMORY_GB}g" \
        --time="${TIME_HOURS}:00:00" \
        --output="slurm_logs/moroz_innovations-%j.log" \
        --wrap="bash $(pwd)/RUN-workflow.sh"
    echo "Submitted SLURM job. Check slurm_logs/ for progress."
    exit 0
fi

# ============================================================================
# Conda env setup
# ============================================================================

ENV_NAME="aiG-moroz_innovations-analysis"
ENV_YML="ai/conda_environment.yml"

module load conda 2>/dev/null || true

env_is_complete() {
    local env_prefix=$(conda env list 2>/dev/null | awk -v n="${ENV_NAME}" '$1==n {print $NF}')
    if [ -z "${env_prefix}" ]; then
        return 1
    fi
    if [ ! -x "${env_prefix}/bin/python" ]; then
        return 1
    fi
    return 0
}

if ! env_is_complete; then
    if conda env list 2>/dev/null | awk '{print $1}' | grep -q "^${ENV_NAME}$"; then
        echo "Broken conda env detected -- removing and rebuilding."
        conda env remove -n "${ENV_NAME}" -y
    fi
    echo "Creating conda env ${ENV_NAME} from ${ENV_YML}..."
    mamba env create -f "${ENV_YML}" -y || conda env create -f "${ENV_YML}" -y
fi

# Activate
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "${ENV_NAME}"

# ============================================================================
# Run Script 001
# ============================================================================

echo ""
echo "Running Script 001 (innovations + origins-at-clade)..."
python ai/scripts/001_ai-python-compute_innovations_and_origins.py

STATUS=$?
echo ""
if [ ${STATUS} -eq 0 ]; then
    echo "Finished: $(date) -- SUCCESS"
else
    echo "Finished: $(date) -- FAILED (exit ${STATUS})"
fi
exit ${STATUS}
