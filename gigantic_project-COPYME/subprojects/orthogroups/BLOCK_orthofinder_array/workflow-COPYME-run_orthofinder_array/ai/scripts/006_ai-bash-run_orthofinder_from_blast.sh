#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 April 27 | Purpose: Run OrthoFinder with -b to skip search (already done in fan-out) and execute clustering + tree inference + reconciliation
# Human: Eric Edsinger

# =============================================================================
# 006_ai-bash-run_orthofinder_from_blast.sh
# =============================================================================
#
# WHY THIS SCRIPT EXISTS
# -----------------------
# In BLOCK_orthofinder_array the slow DIAMOND step is already done (in the
# parallel fan-out, scripts 003-005). All we need OrthoFinder to do is the
# downstream pipeline:
#
#   - Orthogroup clustering (MCL on the search-result graph)
#   - Gene-tree inference (one tree per orthogroup — typically the next
#     dominant cost; benefits from many cores)
#   - Species-tree inference (STAG / consensus)
#   - Duplication/loss reconciliation
#
# OrthoFinder's `-b <dir>` flag does exactly this: it expects a populated
# WorkingDirectory (Species{N}.fa, diamondDBSpecies{N}.dmnd, Blast{A}_{B}.txt
# for every pair, SequenceIDs.txt, SpeciesIDs.txt) and skips the search step.
#
# Per OrthoFinder docs: "Once the BLAST searches have been completed the
# orthogroups can be calculated using the '-b' command, allowing you to
# manage BLAST searches separately on a cluster before resuming the
# OrthoFinder analysis."
#
# Script 005 produces the pooled workdir at the expected layout. This
# script just invokes `orthofinder -b` on it.
#
# INPUTS (command-line args)
# --------------------------
#     --pooled-workdir         Directory of OrthoFinder workdir + all Blast
#                              files (output of script 005). The PARENT of
#                              this directory becomes the OrthoFinder output
#                              location, and -b points at the workdir itself.
#     --output-dir             Where this script writes its output structure
#                              (orthofinder_output/ subdirectory).
#     --cpus                   Total cpus for OrthoFinder (-t plus -a).
#     --search-method          "diamond" or "blast" — passed to -S for
#                              consistency with script 003.
#     --mcl-inflation          MCL inflation parameter (-I).
#
# OUTPUTS
# -------
#     {OUTPUT_DIR}/orthofinder_output/                 OrthoFinder Results_<date>
#                                                      with all downstream outputs.
#     {OUTPUT_DIR}/6_ai-log-run_orthofinder_from_blast.log
#
# Prerequisites:
#   - conda activate ai_gigantic_orthogroups
#   - Scripts 002, 003, 004, 005 must have completed
#
# =============================================================================

set -e

# =============================================================================
# CONFIGURATION
# =============================================================================

POOLED_WORKDIR=""
OUTPUT_DIR="OUTPUT_pipeline/6-output"
CPUS=8
SEARCH_METHOD="diamond"
MCL_INFLATION="1.5"

while [[ $# -gt 0 ]]; do
    case $1 in
        --pooled-workdir)
            POOLED_WORKDIR="$2"
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
        --search-method)
            SEARCH_METHOD="$2"
            shift 2
            ;;
        --mcl-inflation)
            MCL_INFLATION="$2"
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
LOG_FILE="${LOG_DIR}/6_ai-log-run_orthofinder_from_blast.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

# =============================================================================
# MAIN
# =============================================================================

log_message "========================================================================"
log_message "Script 006: Run OrthoFinder (-b, resume from BLAST results)"
log_message "========================================================================"
log_message "Pooled workdir:     ${POOLED_WORKDIR}"
log_message "Output dir:         ${OUTPUT_DIR}"
log_message "CPUs:               ${CPUS}"
log_message "Search method:      ${SEARCH_METHOD}"
log_message "MCL inflation:      ${MCL_INFLATION}"

# -----------------------------------------------------------------------------
# Validate inputs
# -----------------------------------------------------------------------------

if [ -z "${POOLED_WORKDIR}" ] || [ ! -d "${POOLED_WORKDIR}" ]; then
    log_message "CRITICAL ERROR: --pooled-workdir not provided or not a directory: ${POOLED_WORKDIR}"
    exit 1
fi

# Sanity check: workdir should contain Blast{A}_{B}.txt.gz files (compressed
# by DIAMOND's --compress 1, which OrthoFinder's -op command emits) plus the
# Species/DB files OrthoFinder needs. OrthoFinder -b reads the .gz files
# natively (it created them this way in the original workflow).
BLAST_COUNT=$(ls -1 "${POOLED_WORKDIR}"/Blast*.txt.gz 2>/dev/null | wc -l)
if [ "${BLAST_COUNT}" -eq 0 ]; then
    log_message "CRITICAL ERROR: No Blast{A}_{B}.txt.gz files in pooled workdir!"
    log_message "Script 005 must produce the populated workdir."
    exit 1
fi
log_message "Blast file count:   ${BLAST_COUNT}"

SPECIES_COUNT=$(ls -1 "${POOLED_WORKDIR}"/Species*.fa 2>/dev/null | wc -l)
if [ "${SPECIES_COUNT}" -eq 0 ]; then
    log_message "CRITICAL ERROR: No Species{N}.fa files in pooled workdir!"
    log_message "Script 003 should have placed these via OrthoFinder -op."
    exit 1
fi
log_message "Species count:      ${SPECIES_COUNT}"

# Check that orthofinder is available
if ! command -v orthofinder &> /dev/null; then
    log_message "CRITICAL ERROR: orthofinder command not found"
    log_message "Ensure conda env ai_gigantic_orthogroups is activated."
    exit 1
fi

log_message "OrthoFinder version: $(orthofinder --help 2>&1 | head -3 | tail -1 || echo 'version check failed')"

# -----------------------------------------------------------------------------
# Run OrthoFinder with -b
# -----------------------------------------------------------------------------

mkdir -p "${OUTPUT_DIR}/orthofinder_output"

log_message ""
log_message "Starting OrthoFinder (-b resume)..."
log_message ""

# Allocate cpus: -t for parallel search/tree; -a for OrthoFinder algorithm.
# Per OrthoFinder docs, -a should be 4-8x smaller than -t (RAM-heavier).
# Use -t = CPUS (full allocation) and -a = max(1, CPUS/8).
ANALYSIS_CPUS=$(( CPUS / 8 ))
if [ ${ANALYSIS_CPUS} -lt 1 ]; then
    ANALYSIS_CPUS=1
fi

orthofinder \
    -b "${POOLED_WORKDIR}" \
    -o "${OUTPUT_DIR}/orthofinder_output" \
    -t "${CPUS}" \
    -a "${ANALYSIS_CPUS}" \
    -S "${SEARCH_METHOD}" \
    -I "${MCL_INFLATION}" \
    2>&1 | tee -a "${LOG_FILE}"

# -----------------------------------------------------------------------------
# Validate output
# -----------------------------------------------------------------------------

log_message ""
log_message "Validating OrthoFinder output..."

# OrthoFinder writes Results_<date> inside the output directory
RESULTS_DIRS=( "${OUTPUT_DIR}/orthofinder_output"/Results_* )
if [ ${#RESULTS_DIRS[@]} -eq 0 ] || [ ! -d "${RESULTS_DIRS[0]}" ]; then
    log_message "CRITICAL ERROR: OrthoFinder did not produce a Results_<date> directory"
    log_message "Check the log above for OrthoFinder errors."
    exit 1
fi
RESULTS_DIR="${RESULTS_DIRS[0]}"
log_message "OrthoFinder results: ${RESULTS_DIR}"

# Critical output: Orthogroups.tsv
if [ ! -f "${RESULTS_DIR}/Orthogroups/Orthogroups.tsv" ]; then
    log_message "CRITICAL ERROR: Orthogroups/Orthogroups.tsv not produced"
    exit 1
fi

ORTHOGROUP_COUNT=$(tail -n +2 "${RESULTS_DIR}/Orthogroups/Orthogroups.tsv" | wc -l)
log_message "Orthogroups identified: ${ORTHOGROUP_COUNT}"

if [ "${ORTHOGROUP_COUNT}" -eq 0 ]; then
    log_message "CRITICAL ERROR: Zero orthogroups produced"
    log_message "Inspect ${POOLED_WORKDIR}/ for incomplete pairs."
    exit 1
fi

# Single-copy orthogroups
SC_FILE="${RESULTS_DIR}/Orthogroups/Orthogroups_SingleCopyOrthologues.txt"
if [ -f "${SC_FILE}" ]; then
    SINGLE_COPY_COUNT=$(wc -l < "${SC_FILE}")
    log_message "Single-copy orthogroups: ${SINGLE_COPY_COUNT}"
fi

# -----------------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------------

log_message ""
log_message "========================================================================"
log_message "Script 006 completed successfully"
log_message "========================================================================"
log_message "OrthoFinder output: ${RESULTS_DIR}"
log_message "Log file: ${LOG_FILE}"
