#!/bin/bash
# AI: Claude Code | Opus 4.8 (1M context) | 2026 June 18 | Purpose: Build annogroups per source (local or SLURM via config)
# Human: Eric Edsinger

################################################################################
# GIGANTIC annogroups - BLOCK_build_annogroups
################################################################################
#
# PURPOSE:
# Build the four canonical annogroup types — feature, combination, architecture,
# absent — PER SOURCE annotation database (pfam, gene3d, tmbed, signalp, ...),
# from annotations_hmms outputs. One parser plugin per source
# (ai/scripts/parsers/<source>.py); the four-type construction is shared.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Edit START_HERE-user_config.yaml:
#    - species_set_name (e.g. "species70") — drives the proteome universe
#    - sources ("all" or an explicit subset; each subset entry needs a parser)
#    - inputs.{annotations_hmms_dir, proteomes_dir}  (all via output_to_input, §2)
#    - execution_mode ("local" or "slurm"); if slurm, slurm_account + slurm_qos
# 2. Verify upstream output_to_input/ are populated:
#    - annotations_hmms/output_to_input/BLOCK_interproscan_parsed/<db>/   (e.g. pfam/)
#    - genomesDB/output_to_input/STEP_4-create_final_species_set/<set>_proteomes/*.aa
#
# WHAT THIS DOES:
# 1. Creates (or reuses) per-BLOCK conda env from ai/conda_environment.yml
# 2. Runs the pipeline:
#    001: resolve sources (parser plugins) + build proteome universe  (1-output)
#    002: build annogroups per source (map + membership + dropped audit) (2-output)
#    003: validate per source (strict fail-fast)                      (3-output)
#    004: write cross-source summary (per source / species / phylum)  (4-output)
#    005: write run log
# 3. Creates output_to_input symlinks for downstream consumers (per source)
#
# OUTPUT:
#   OUTPUT_pipeline/1-output/            sources manifest + proteome universe
#   OUTPUT_pipeline/2-output/<source>/   annogroup map + membership (+ dropped audit)
#   OUTPUT_pipeline/3-output/<source>/   validation report
#   OUTPUT_pipeline/4-output/            summary (per source / per species / per phylum)
#   ../../output_to_input/BLOCK_build_annogroups/<species_set>/<source>/
################################################################################

echo "========================================================================"
echo "GIGANTIC annogroups - build_annogroups"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# ============================================================================
# Read flat YAML keys (no Python dependency)
# ============================================================================
read_config() {
    local value=$(grep "^${1}:" START_HERE-user_config.yaml 2>/dev/null | head -1 | sed 's/^[^:]*: *//' | sed 's/^"//;s/"$//')
    echo "${value:-$2}"
}

EXECUTION_MODE=$(read_config "execution_mode" "local")
SPECIES_SET=$(read_config "species_set_name" "")
SOURCES=$(read_config "sources" "all")

# ============================================================================
# RUN_SUMMARY.md placeholder (so status is visible immediately on submit)
# ============================================================================
SUMMARY_FILE="RUN_SUMMARY.md"
WORKFLOW_DIR_NAME="$(basename "${SCRIPT_DIR}")"

if [ "${EXECUTION_MODE}" == "slurm" ] && [ -z "${SLURM_JOB_ID}" ]; then
    STATUS_EMOJI="⏳"; STATUS_TEXT="QUEUED (submitted $(date '+%Y-%m-%d %H:%M:%S'))"
    STATUS_NOTE="Waiting for SLURM to schedule the job. This file updates to IN PROGRESS when it starts and to a final summary on completion."
else
    STATUS_EMOJI="🔄"; STATUS_TEXT="IN PROGRESS (started $(date '+%Y-%m-%d %H:%M:%S'))"
    STATUS_NOTE="This run is currently executing. On success the final block below is replaced with a SUCCESS summary."
fi

cat > "${SUMMARY_FILE}" <<EOF
# Workflow Run Summary: build_annogroups (${SPECIES_SET})

**Status**: ${STATUS_EMOJI} **${STATUS_TEXT}**

**Species set**: \`${SPECIES_SET}\`
**Sources**: \`${SOURCES}\`
**Execution mode**: ${EXECUTION_MODE}

${STATUS_NOTE}
EOF
cp "${SUMMARY_FILE}" "../${WORKFLOW_DIR_NAME}-run_summary.md" 2>/dev/null || true

# ============================================================================
# SLURM self-submission (if execution_mode=slurm and not already in a job)
# ============================================================================
if [ "${EXECUTION_MODE}" == "slurm" ] && [ -z "${SLURM_JOB_ID}" ]; then
    echo "Execution mode: SLURM (submitting job)"
    echo ""
    SLURM_CPUS=$(read_config "cpus" "4")
    SLURM_MEM=$(read_config "memory_gb" "24")
    SLURM_TIME=$(read_config "time_hours" "4")
    SLURM_ACCOUNT=$(read_config "slurm_account" "")
    SLURM_QOS=$(read_config "slurm_qos" "")

    mkdir -p slurm_logs
    SBATCH_ARGS="--job-name=annogroups_build_annogroups"
    SBATCH_ARGS="${SBATCH_ARGS} --cpus-per-task=${SLURM_CPUS}"
    SBATCH_ARGS="${SBATCH_ARGS} --mem=${SLURM_MEM}gb"
    SBATCH_ARGS="${SBATCH_ARGS} --time=${SLURM_TIME}:00:00"
    SBATCH_ARGS="${SBATCH_ARGS} --output=slurm_logs/annogroups_build_annogroups-%j.log"
    [ -n "${SLURM_ACCOUNT}" ] && SBATCH_ARGS="${SBATCH_ARGS} --account=${SLURM_ACCOUNT}"
    [ -n "${SLURM_QOS}" ] && SBATCH_ARGS="${SBATCH_ARGS} --qos=${SLURM_QOS}"

    echo "Submitting with: sbatch ${SBATCH_ARGS}"
    sbatch ${SBATCH_ARGS} --wrap="bash $(realpath $0)"
    echo ""
    echo "Job submitted. Check slurm_logs/ for output."
    exit 0
fi

if [ -n "${SLURM_JOB_ID}" ]; then
    echo "Running inside SLURM job ${SLURM_JOB_ID}"
else
    echo "Execution mode: local"
fi
echo ""

# ============================================================================
# Activate conda env (on-demand creation)
# ============================================================================
ENV_NAME="aiG-annogroups-build_annogroups"
ENV_YML="ai/conda_environment.yml"

module load conda 2>/dev/null || true

if ! command -v conda &> /dev/null; then
    echo "ERROR: conda not found!"
    echo "On HPC (HiPerGator): module load conda"
    exit 1
fi

if ! conda env list 2>/dev/null | grep -q "^${ENV_NAME} "; then
    echo "Environment '${ENV_NAME}' not found. Creating on-demand..."
    if [ ! -f "${ENV_YML}" ]; then
        echo "ERROR: Environment spec not found at: ${ENV_YML}"
        exit 1
    fi
    if command -v mamba &> /dev/null; then
        mamba env create -f "${ENV_YML}" -y; CREATE_EXIT=$?
    else
        conda env create -f "${ENV_YML}" -y; CREATE_EXIT=$?
    fi
    if [ $CREATE_EXIT -ne 0 ]; then
        echo "ERROR: Failed to create conda environment '${ENV_NAME}' (exit ${CREATE_EXIT})"
        echo "If a partial env was left behind: mamba env remove -n ${ENV_NAME} -y"
        exit 1
    fi
    echo "Environment '${ENV_NAME}' created."
    echo ""
fi

if conda activate "${ENV_NAME}" 2>/dev/null; then
    echo "Activated conda environment: ${ENV_NAME}"
else
    echo "WARNING: Could not activate '${ENV_NAME}'. Continuing with current environment."
fi

if ! command -v nextflow &> /dev/null; then
    echo "NextFlow not found in conda env. Trying system module..."
    module load nextflow 2>/dev/null || true
    if ! command -v nextflow &> /dev/null; then
        echo "ERROR: NextFlow not available! Install in env or 'module load nextflow'."
        exit 1
    fi
    echo "Using NextFlow from system module"
else
    echo "NextFlow available"
fi
echo ""

# ============================================================================
# Validate prerequisites
# ============================================================================
echo "Validating prerequisites..."
[ -f "START_HERE-user_config.yaml" ] || { echo "ERROR: START_HERE-user_config.yaml not found!"; exit 1; }
echo "  [OK] Configuration file found"
echo ""
echo "Configuration:"
echo "  Species Set : ${SPECIES_SET}"
echo "  Sources     : ${SOURCES}"
echo ""

# ============================================================================
# Run NextFlow pipeline
# ============================================================================
echo "Running NextFlow pipeline..."
echo ""

RESUME=$(read_config "resume" "false")
RESUME_FLAG=""
if [ "${RESUME}" == "true" ]; then
    RESUME_FLAG="-resume"
    echo "  resume: enabled (using NextFlow work/ cache)"
fi

PARALLELISM_MODE=$(read_config "parallelism_mode" "local")
case "${PARALLELISM_MODE}" in
    slurm) PROFILE_FLAG="-profile standard" ;;
    local) PROFILE_FLAG="-profile local" ;;
    *)
        echo "ERROR: unknown parallelism_mode: '${PARALLELISM_MODE}' (valid: 'slurm' | 'local')"
        exit 1
        ;;
esac
echo "  parallelism_mode: ${PARALLELISM_MODE} (nextflow ${PROFILE_FLAG})"

# Universal GIGANTIC YAML->params pattern: pass the YAML directly via
# -params-file (NextFlow loads it natively, populating params.X.Y.Z).
nextflow run ai/main.nf ${RESUME_FLAG} ${PROFILE_FLAG} \
    -params-file START_HERE-user_config.yaml

EXIT_CODE=$?
if [ $EXIT_CODE -ne 0 ]; then
    echo ""
    echo "========================================================================"
    echo "FAILED! Pipeline exited with code ${EXIT_CODE}"
    echo "========================================================================"
    exit $EXIT_CODE
fi

# ============================================================================
# Create symlinks for output_to_input (downstream consumers)
# ============================================================================
# Real files live in OUTPUT_pipeline/2-output/<source>/. Expose each source's
# annogroup map + membership (+ dropped-orphan audit) under a
# <species_set>/<source>/ subdir so downstream paths are stable.
echo ""
echo "Creating symlinks for downstream consumers..."

SHARED_ROOT="../../output_to_input/BLOCK_build_annogroups/${SPECIES_SET}"
mkdir -p "${SHARED_ROOT}"
SYMLINK_COUNT=0

for source_out in OUTPUT_pipeline/2-output/*/; do
    [ -d "${source_out}" ] || continue
    source_name="$(basename "${source_out}")"
    source_shared="${SHARED_ROOT}/${source_name}"
    mkdir -p "${source_shared}"
    # Remove stale symlinks from previous runs
    for old in "${source_shared}"/*.tsv; do
        [ -L "$old" ] && rm -f "$old"
    done
    for real in "${source_out}"*.tsv; do
        [ -f "$real" ] || continue
        fname="$(basename "$real")"
        ln -sf "../../../../BLOCK_build_annogroups/${WORKFLOW_DIR_NAME}/OUTPUT_pipeline/2-output/${source_name}/${fname}" \
            "${source_shared}/${fname}"
        SYMLINK_COUNT=$((SYMLINK_COUNT + 1))
    done
done

echo "  output_to_input/BLOCK_build_annogroups/${SPECIES_SET}/ -> ${SYMLINK_COUNT} symlinks created"

# ============================================================================
# Final RUN_SUMMARY.md (SUCCESS)
# ============================================================================
cat > "${SUMMARY_FILE}" <<EOF
# Workflow Run Summary: build_annogroups (${SPECIES_SET})

**Status**: ✅ **SUCCESS (completed $(date '+%Y-%m-%d %H:%M:%S'))**

**Species set**: \`${SPECIES_SET}\`
**Sources**: \`${SOURCES}\`
**Downstream symlinks**: ${SYMLINK_COUNT} (in ../../output_to_input/BLOCK_build_annogroups/${SPECIES_SET}/)

## Outputs (real files)
- \`OUTPUT_pipeline/1-output/\`            sources manifest + proteome universe
- \`OUTPUT_pipeline/2-output/<source>/\`   annogroup map + membership (+ dropped audit)
- \`OUTPUT_pipeline/3-output/<source>/\`   validation report
- \`OUTPUT_pipeline/4-output/\`            summary (per source / per species / per phylum)
EOF
cp "${SUMMARY_FILE}" "../${WORKFLOW_DIR_NAME}-run_summary.md" 2>/dev/null || true

echo ""
echo "========================================================================"
echo "SUCCESS! Annogroups built."
echo "  Species Set: ${SPECIES_SET}"
echo "  Downstream: ../../output_to_input/BLOCK_build_annogroups/${SPECIES_SET}/"
echo "========================================================================"
echo "Completed: $(date)"

conda deactivate 2>/dev/null || true
