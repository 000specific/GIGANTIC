#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 April 26 | Purpose: Run OrthoHMM with --start search_res to skip phmmer (already done in fan-out) and execute Steps 2-5
# Human: Eric Edsinger

# =============================================================================
# 005_ai-bash-run_orthohmm_from_search_res.sh
# =============================================================================
#
# WHY THIS SCRIPT EXISTS
# -----------------------
# In BLOCK_orthohmm_GIGANTIC the slow phmmer step is already done (in the
# parallel fan-out, scripts 003-004). All we need OrthoHMM to do is the
# downstream pipeline:
#
#   Step 2: Determining edge thresholds
#   Step 3: Identifying network edges
#   Step 4: Conducting clustering (MCL)
#   Step 5: Writing orthogroup information
#
# OrthoHMM's --start search_res flag does exactly this: it skips Step 1
# (the all-vs-all phmmer) and starts from "search results" — i.e., it expects
# orthohmm_working_res/*.phmmerout.txt to already be present and reads them
# instead of running phmmer.
#
# The expected directory layout (per orthohmm.py, parser.py, helpers.py):
#
#     {OUTPUT_DIR}/
#       orthohmm_working_res/
#         A_2_B.phmmerout.txt
#         A_2_C.phmmerout.txt
#         ...
#
# The caller (NextFlow process run_orthohmm_from_search_res in main.nf) is
# responsible for staging both the proteomes (--input-dir) and the pooled
# phmmer outputs (into --working-res-dir) before invoking this script. We
# verify both are populated, then run orthohmm.
#
# INPUTS (command-line args)
# --------------------------
#     --input-dir              Directory of short-header proteomes (.pep files
#                              from script 002, staged into the work dir).
#     --working-res-dir        Directory of pooled phmmerout.txt files from
#                              script 004 (must equal {OUTPUT_DIR}/orthohmm_working_res
#                              for OrthoHMM to find them).
#     --output-dir             Where OrthoHMM writes its outputs.
#     --cpus                   Number of cores OrthoHMM will use for MCL etc.
#     --evalue                 Same threshold used during phmmer (for OrthoHMM
#                              to filter the phmmer outputs consistently).
#     --single-copy-threshold  Threshold for single-copy orthogroup designation.
#
# OUTPUTS
# -------
#     {OUTPUT_DIR}/orthohmm_orthogroups.txt
#     {OUTPUT_DIR}/orthohmm_gene_count.txt
#     {OUTPUT_DIR}/orthohmm_single_copy_orthogroups.txt
#     {OUTPUT_DIR}/orthohmm_orthogroups/  (per-orthogroup FASTAs)
#     {OUTPUT_DIR}/5_ai-log-run_orthohmm_from_search_res.log
#
# Prerequisites:
#   - conda activate ai_gigantic_orthogroups_orthohmm
#   - Scripts 002, 003, and 004 must have completed
#
# =============================================================================

set -e  # Exit on error

# =============================================================================
# CONFIGURATION (with defaults; overridable via command-line args)
# =============================================================================

INPUT_DIR=""
WORKING_RES_DIR=""
OUTPUT_DIR="OUTPUT_pipeline/5-output"
CPUS=8
EVALUE="0.0001"
SINGLE_COPY_THRESHOLD="0.5"

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --input-dir)
            INPUT_DIR="$2"
            shift 2
            ;;
        --working-res-dir)
            WORKING_RES_DIR="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --cpus)
            CPUS="$2"
            shift 2
            ;;
        --evalue)
            EVALUE="$2"
            shift 2
            ;;
        --single-copy-threshold)
            SINGLE_COPY_THRESHOLD="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# LOGGING SETUP
# =============================================================================

LOG_DIR="${OUTPUT_DIR}"
mkdir -p "${LOG_DIR}"
LOG_FILE="${LOG_DIR}/5_ai-log-run_orthohmm_from_search_res.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

# =============================================================================
# MAIN
# =============================================================================

log_message "========================================================================"
log_message "Script 005: Run OrthoHMM (--start search_res, Steps 2-5 only)"
log_message "========================================================================"
log_message "Input dir (proteomes):   ${INPUT_DIR}"
log_message "Working res dir:         ${WORKING_RES_DIR}"
log_message "Output dir:              ${OUTPUT_DIR}"
log_message "CPUs:                    ${CPUS}"
log_message "E-value threshold:       ${EVALUE}"
log_message "Single-copy threshold:   ${SINGLE_COPY_THRESHOLD}"

# -----------------------------------------------------------------------------
# Validate inputs
# -----------------------------------------------------------------------------

if [ -z "${INPUT_DIR}" ] || [ ! -d "${INPUT_DIR}" ]; then
    log_message "CRITICAL ERROR: --input-dir not provided or not a directory: ${INPUT_DIR}"
    exit 1
fi

if [ -z "${WORKING_RES_DIR}" ] || [ ! -d "${WORKING_RES_DIR}" ]; then
    log_message "CRITICAL ERROR: --working-res-dir not provided or not a directory: ${WORKING_RES_DIR}"
    exit 1
fi

# Count proteomes
PROTEOME_COUNT=$(ls -1 "${INPUT_DIR}"/*.pep 2>/dev/null | wc -l)
if [ "${PROTEOME_COUNT}" -eq 0 ]; then
    log_message "CRITICAL ERROR: No .pep files in ${INPUT_DIR}"
    log_message "Script 002 must produce short-header proteomes; the calling NextFlow process must stage them here."
    exit 1
fi
log_message "Proteome count: ${PROTEOME_COUNT}"

# Count phmmer outputs
PHMMER_COUNT=$(ls -1 "${WORKING_RES_DIR}"/*.phmmerout.txt 2>/dev/null | wc -l)
if [ "${PHMMER_COUNT}" -eq 0 ]; then
    log_message "CRITICAL ERROR: No phmmerout.txt files in ${WORKING_RES_DIR}"
    log_message "Script 004 must produce pooled phmmer outputs; the calling NextFlow process must stage them here."
    exit 1
fi
log_message "Phmmer output count: ${PHMMER_COUNT}"

# Sanity check: phmmer output count should be proteome_count^2
EXPECTED_PHMMER_COUNT=$(( PROTEOME_COUNT * PROTEOME_COUNT ))
if [ "${PHMMER_COUNT}" -ne "${EXPECTED_PHMMER_COUNT}" ]; then
    log_message "WARNING: phmmer output count (${PHMMER_COUNT}) != proteome_count^2 (${EXPECTED_PHMMER_COUNT})"
    log_message "OrthoHMM may fail with incomplete pairwise data. Verify script 004 verification report."
    # Note: NOT fail-fast here because verification was script 004's job.
    # If we reach this script, script 004 succeeded — so any mismatch here
    # would indicate a NextFlow staging bug, not a phmmer-completion bug.
fi

# -----------------------------------------------------------------------------
# Pre-condition for --start search_res:
#   OrthoHMM expects the working_res dir to be NAMED orthohmm_working_res
#   and located INSIDE the output directory.
# -----------------------------------------------------------------------------

EXPECTED_WORKING_RES_PATH="${OUTPUT_DIR}/orthohmm_working_res"

# If the caller already staged at the expected path, do nothing.
# Otherwise, place the working_res dir at the expected location.
if [ "$(realpath "${WORKING_RES_DIR}")" != "$(realpath "${EXPECTED_WORKING_RES_PATH}" 2>/dev/null || echo "${EXPECTED_WORKING_RES_PATH}")" ]; then
    log_message "Staging phmmer outputs into ${EXPECTED_WORKING_RES_PATH}/"
    mkdir -p "${EXPECTED_WORKING_RES_PATH}"
    cp -n "${WORKING_RES_DIR}"/*.phmmerout.txt "${EXPECTED_WORKING_RES_PATH}/" 2>/dev/null || true
fi

# Check that orthohmm command is available
if ! command -v orthohmm &> /dev/null; then
    log_message "CRITICAL ERROR: orthohmm command not found"
    log_message "Ensure conda env ai_gigantic_orthogroups_orthohmm is activated."
    exit 1
fi

log_message "OrthoHMM version: $(orthohmm --version 2>&1 || echo 'version check failed')"

# -----------------------------------------------------------------------------
# Run OrthoHMM with --start search_res
# -----------------------------------------------------------------------------

log_message ""
log_message "Starting OrthoHMM (--start search_res)..."
log_message ""

orthohmm "${INPUT_DIR}" \
    -o "${OUTPUT_DIR}" \
    -c "${CPUS}" \
    -e "${EVALUE}" \
    -s "${SINGLE_COPY_THRESHOLD}" \
    --start search_res \
    2>&1 | tee -a "${LOG_FILE}"

# -----------------------------------------------------------------------------
# Validate output (fail-fast on missing critical files)
# -----------------------------------------------------------------------------

log_message ""
log_message "Validating OrthoHMM output..."

if [ ! -f "${OUTPUT_DIR}/orthohmm_orthogroups.txt" ]; then
    log_message "CRITICAL ERROR: orthohmm_orthogroups.txt not produced"
    log_message "OrthoHMM did not produce expected output. Check log above for errors."
    exit 1
fi

ORTHOGROUP_COUNT=$(grep -c -v '^\s*$' "${OUTPUT_DIR}/orthohmm_orthogroups.txt" || echo "0")
log_message "Orthogroups identified: ${ORTHOGROUP_COUNT}"

if [ "${ORTHOGROUP_COUNT}" -eq 0 ]; then
    log_message "CRITICAL ERROR: Zero orthogroups produced"
    log_message "Inspect ${OUTPUT_DIR}/orthohmm_working_res/ for incomplete pairs."
    exit 1
fi

if [ ! -f "${OUTPUT_DIR}/orthohmm_gene_count.txt" ]; then
    log_message "CRITICAL ERROR: orthohmm_gene_count.txt not produced"
    exit 1
fi
log_message "Gene count file: present"

if [ ! -f "${OUTPUT_DIR}/orthohmm_single_copy_orthogroups.txt" ]; then
    log_message "CRITICAL ERROR: orthohmm_single_copy_orthogroups.txt not produced"
    exit 1
fi
SINGLE_COPY_COUNT=$(grep -c -v '^\s*$' "${OUTPUT_DIR}/orthohmm_single_copy_orthogroups.txt" || echo "0")
log_message "Single-copy orthogroups: ${SINGLE_COPY_COUNT}"

# -----------------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------------

log_message ""
log_message "========================================================================"
log_message "Script 005 completed successfully"
log_message "========================================================================"
log_message "Output directory: ${OUTPUT_DIR}"
log_message "Log file: ${LOG_FILE}"
