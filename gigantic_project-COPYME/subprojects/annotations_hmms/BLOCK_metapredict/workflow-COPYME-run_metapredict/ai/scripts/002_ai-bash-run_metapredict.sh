#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 May 23 | Purpose: Run MetaPredict CLI tools on one species proteome, preserving native output
# Human: Eric Edsinger

# =============================================================================
# 002_ai-bash-run_metapredict.sh
# =============================================================================
#
# Runs three MetaPredict CLI commands on one species proteome FASTA and
# preserves each command's native output unchanged:
#
#   metapredict-predict-disorder INPUT -o disorder.csv
#   metapredict-predict-idrs     INPUT -o idrs.fasta           (default mode = fasta)
#   metapredict-predict-pLDDT    INPUT -o pLDDT_scores.csv
#
# All three outputs land in:
#   ${OUTPUT_DIR}/metapredict_raw_output_${PHYLONAME}/
#
# That directory is what NextFlow publishes to OUTPUT_pipeline. No parsing,
# no reduction, no rounding, no rm -rf. Downstream code reads from the raw
# files. This follows the GIGANTIC convention: preserve the tool's native
# output in OUTPUT_pipeline.
#
# Input:
#   --input-fasta : Path to a single species proteome FASTA file (.aa)
#   --output-dir  : Directory where metapredict_raw_output_<phyloname>/ is created
#   --phyloname   : GIGANTIC phyloname (used in the output dir name + log)
#   --device      : Optional. cpu | mps | cuda | cuda:N (default: cpu)
#
# Prerequisites:
#   - Conda env ai_gigantic_metapredict activated (provides the metapredict
#     CLI binaries on PATH).
#
# =============================================================================

set -e

# =============================================================================
# ARG PARSING
# =============================================================================

INPUT_FASTA=""
OUTPUT_DIR="."
PHYLONAME=""
DEVICE="cpu"

while [[ $# -gt 0 ]]; do
    case $1 in
        --input-fasta)  INPUT_FASTA="$2"; shift 2 ;;
        --output-dir)   OUTPUT_DIR="$2";  shift 2 ;;
        --phyloname)    PHYLONAME="$2";   shift 2 ;;
        --device)       DEVICE="$2";      shift 2 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# =============================================================================
# LOGGING
# =============================================================================

mkdir -p "${OUTPUT_DIR}"
LOG_FILE="${OUTPUT_DIR}/2_ai-log-run_metapredict_${PHYLONAME}.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

# =============================================================================
# VALIDATE INPUTS
# =============================================================================

log_message "========================================================================"
log_message "Script 002: Run MetaPredict CLI tools (raw output preserved)"
log_message "========================================================================"

if [ -z "${INPUT_FASTA}" ]; then
    log_message "CRITICAL ERROR: --input-fasta is required but not provided!"
    exit 1
fi

if [ -z "${PHYLONAME}" ]; then
    log_message "CRITICAL ERROR: --phyloname is required but not provided!"
    exit 1
fi

if [ ! -f "${INPUT_FASTA}" ]; then
    log_message "CRITICAL ERROR: Input FASTA file does not exist: ${INPUT_FASTA}"
    exit 1
fi

if [ ! -s "${INPUT_FASTA}" ]; then
    log_message "CRITICAL ERROR: Input FASTA file is empty: ${INPUT_FASTA}"
    exit 1
fi

# Confirm each CLI is on PATH
for cmd in metapredict-predict-disorder metapredict-predict-idrs metapredict-predict-pLDDT; do
    if ! command -v "$cmd" &> /dev/null; then
        log_message "CRITICAL ERROR: ${cmd} not found on PATH"
        log_message "Activate conda env ai_gigantic_metapredict first."
        exit 1
    fi
done

SEQUENCE_COUNT=$(grep -c '^>' "${INPUT_FASTA}")
log_message "Input FASTA: ${INPUT_FASTA}"
log_message "Phyloname: ${PHYLONAME}"
log_message "Device: ${DEVICE}"
log_message "Input sequences: ${SEQUENCE_COUNT}"

# =============================================================================
# RAW OUTPUT DIR — preserved as-is by NextFlow publishDir (see main.nf)
# =============================================================================

RAW_DIR="${OUTPUT_DIR}/metapredict_raw_output_${PHYLONAME}"
mkdir -p "${RAW_DIR}"
log_message "Raw output directory: ${RAW_DIR}"

# =============================================================================
# RUN 1: PER-RESIDUE DISORDER SCORES
# =============================================================================

DISORDER_OUT="${RAW_DIR}/disorder.csv"
log_message ""
log_message "Running: metapredict-predict-disorder -> $(basename ${DISORDER_OUT})"
metapredict-predict-disorder \
    "${INPUT_FASTA}" \
    -o "${DISORDER_OUT}" \
    -d "${DEVICE}" \
    -s \
    2>&1 | tee -a "${LOG_FILE}"

DISORDER_EXIT=${PIPESTATUS[0]}
if [ ${DISORDER_EXIT} -ne 0 ] || [ ! -s "${DISORDER_OUT}" ]; then
    log_message "CRITICAL ERROR: metapredict-predict-disorder failed (exit=${DISORDER_EXIT})"
    log_message "Expected output: ${DISORDER_OUT}"
    exit 1
fi
log_message "  disorder.csv size: $(wc -c < ${DISORDER_OUT}) bytes"

# =============================================================================
# RUN 2: INTRINSICALLY DISORDERED REGIONS (default mode = fasta)
# =============================================================================

IDRS_OUT="${RAW_DIR}/idrs.fasta"
log_message ""
log_message "Running: metapredict-predict-idrs -> $(basename ${IDRS_OUT})"
metapredict-predict-idrs \
    "${INPUT_FASTA}" \
    -o "${IDRS_OUT}" \
    -d "${DEVICE}" \
    -s \
    2>&1 | tee -a "${LOG_FILE}"

IDRS_EXIT=${PIPESTATUS[0]}
if [ ${IDRS_EXIT} -ne 0 ] || [ ! -e "${IDRS_OUT}" ]; then
    log_message "CRITICAL ERROR: metapredict-predict-idrs failed (exit=${IDRS_EXIT})"
    log_message "Expected output: ${IDRS_OUT}"
    exit 1
fi
log_message "  idrs.fasta size: $(wc -c < ${IDRS_OUT}) bytes"

# =============================================================================
# RUN 3: pLDDT SCORES
# =============================================================================

PLDDT_OUT="${RAW_DIR}/pLDDT_scores.csv"
log_message ""
log_message "Running: metapredict-predict-pLDDT -> $(basename ${PLDDT_OUT})"
metapredict-predict-pLDDT \
    "${INPUT_FASTA}" \
    -o "${PLDDT_OUT}" \
    -d "${DEVICE}" \
    -s \
    2>&1 | tee -a "${LOG_FILE}"

PLDDT_EXIT=${PIPESTATUS[0]}
if [ ${PLDDT_EXIT} -ne 0 ] || [ ! -s "${PLDDT_OUT}" ]; then
    log_message "CRITICAL ERROR: metapredict-predict-pLDDT failed (exit=${PLDDT_EXIT})"
    log_message "Expected output: ${PLDDT_OUT}"
    exit 1
fi
log_message "  pLDDT_scores.csv size: $(wc -c < ${PLDDT_OUT}) bytes"

# =============================================================================
# COMPLETION
# =============================================================================

log_message ""
log_message "========================================================================"
log_message "Script 002 completed successfully for: ${PHYLONAME}"
log_message "========================================================================"
log_message "Raw output dir: ${RAW_DIR}"
log_message "  disorder.csv         (per-residue disorder scores)"
log_message "  idrs.fasta           (IDR regions, header carries IDR_START / IDR_END)"
log_message "  pLDDT_scores.csv     (per-residue pLDDT confidence scores)"
log_message "Log file: ${LOG_FILE}"
