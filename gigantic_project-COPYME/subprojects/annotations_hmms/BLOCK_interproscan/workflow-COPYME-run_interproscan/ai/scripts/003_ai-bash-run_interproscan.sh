#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Run InterProScan on a single proteome chunk for protein domain and function annotation
# Human: Eric Edsinger

# =============================================================================
# 003_ai-bash-run_interproscan.sh
# =============================================================================
#
# Runs InterProScan on a single proteome chunk FASTA file. This script is called
# once per chunk by the Nextflow pipeline, enabling highly parallel execution
# across species and chunks.
#
# The core InterProScan command is preserved from GIGANTIC_0:
#   interproscan.sh -i INPUT -goterms -dp -f tsv -cpu N -d output/
#
# Flags:
#   -goterms: Include Gene Ontology term assignments
#   -dp: Disable precalculated match lookup (ensures fresh analysis)
#   -f tsv: Output as tab-separated values
#   -cpu N: Number of threads for parallel analysis
#
# Input:
#   --input-fasta: Path to a single chunk FASTA file
#   --output-dir: Directory for output files
#   --interproscan-path: Path to InterProScan installation directory
#   --cpus: Number of CPUs for InterProScan (default: 16)
#   --applications: InterProScan applications to run (default: all)
#
# Output:
#   {chunk_basename}_interproscan.tsv - InterProScan results in TSV format
#       15-column TSV with no header:
#       protein_id  md5  length  analysis_db  signature_id  signature_desc
#       start  stop  score  status  date  interpro_id  interpro_desc  go_terms  pathway
#
# Prerequisites:
#   - InterProScan 5 installed with databases
#   - Java runtime available
#   - conda environment ai_gigantic_interproscan activated
#
# Usage:
#   bash 003_ai-bash-run_interproscan.sh \
#       --input-fasta chunk_001.fasta \
#       --output-dir . \
#       --interproscan-path /path/to/interproscan \
#       --cpus 16 \
#       --applications all
#
# =============================================================================

set -e  # Exit on error
ulimit -c 0  # Disable core dumps (SUPERFAMILY epa-ng segfaults generate TB of core files)

# =============================================================================
# CONFIGURATION
# =============================================================================

# Default values
INPUT_FASTA=""
OUTPUT_DIR="."
INTERPROSCAN_PATH=""
CPUS=16
APPLICATIONS="all"

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --input-fasta)
            INPUT_FASTA="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --interproscan-path)
            INTERPROSCAN_PATH="$2"
            shift 2
            ;;
        --cpus)
            CPUS="$2"
            shift 2
            ;;
        --applications)
            APPLICATIONS="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# VALIDATE INPUTS
# =============================================================================

echo "========================================================================"
echo "Script 003: Run InterProScan on Proteome Chunk"
echo "========================================================================"

# Validate required arguments
if [ -z "${INPUT_FASTA}" ]; then
    echo "CRITICAL ERROR: --input-fasta is required but not provided!"
    exit 1
fi

if [ -z "${INTERPROSCAN_PATH}" ]; then
    echo "CRITICAL ERROR: --interproscan-path is required but not provided!"
    echo "Set the interproscan_install_path parameter in nextflow.config."
    exit 1
fi

# Validate input file exists
if [ ! -f "${INPUT_FASTA}" ]; then
    echo "CRITICAL ERROR: Input FASTA file does not exist!"
    echo "Expected path: ${INPUT_FASTA}"
    echo "Ensure the chunk file was created by script 002."
    exit 1
fi

# Validate input file is not empty
if [ ! -s "${INPUT_FASTA}" ]; then
    echo "CRITICAL ERROR: Input FASTA file is empty!"
    echo "Path: ${INPUT_FASTA}"
    exit 1
fi

# Derive the InterProScan executable path
INTERPROSCAN_EXECUTABLE="${INTERPROSCAN_PATH}/interproscan.sh"

# Validate InterProScan installation
if [ ! -f "${INTERPROSCAN_EXECUTABLE}" ]; then
    echo "CRITICAL ERROR: InterProScan executable not found!"
    echo "Expected: ${INTERPROSCAN_EXECUTABLE}"
    echo "Verify that interproscan_install_path in nextflow.config points to the InterProScan installation directory."
    echo "The directory should contain interproscan.sh."
    exit 1
fi

if [ ! -x "${INTERPROSCAN_EXECUTABLE}" ]; then
    echo "CRITICAL ERROR: InterProScan executable is not executable!"
    echo "Path: ${INTERPROSCAN_EXECUTABLE}"
    echo "Run: chmod +x ${INTERPROSCAN_EXECUTABLE}"
    exit 1
fi

# Derive chunk basename for output naming
CHUNK_BASENAME=$(basename "${INPUT_FASTA}" .fasta)
OUTPUT_TSV="${OUTPUT_DIR}/${CHUNK_BASENAME}_interproscan.tsv"

echo "Input FASTA: ${INPUT_FASTA}"
echo "Output TSV: ${OUTPUT_TSV}"
echo "InterProScan path: ${INTERPROSCAN_PATH}"
echo "CPUs: ${CPUS}"
echo "Applications: ${APPLICATIONS}"
echo ""

# Count input sequences
SEQUENCE_COUNT=$(grep -c '^>' "${INPUT_FASTA}")
echo "Input sequences in chunk: ${SEQUENCE_COUNT}"

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# =============================================================================
# SHORT PATH WORKAROUND
# =============================================================================
# InterProScan's internal H2 database has a VARCHAR(350) column limit for file
# paths. Our deeply nested project directory structure produces paths that
# exceed this limit, causing InterProScan to crash.
#
# Workaround: Copy the input chunk to a short temporary directory under
# /blue/moroz/share/edsinger/, run InterProScan there, then copy results back.
# =============================================================================

SHORT_BASE_PATH="/blue/moroz/share/edsinger/iprs_tmp"
SHORT_JOB_ID="$$_$(date +%s)"
SHORT_WORK_DIR="${SHORT_BASE_PATH}/${SHORT_JOB_ID}"

echo ""
echo "Using short path workaround for InterProScan VARCHAR(350) limit."
echo "Short work directory: ${SHORT_WORK_DIR}"

mkdir -p "${SHORT_WORK_DIR}"

# Copy input FASTA to short path with a short filename
SHORT_INPUT="${SHORT_WORK_DIR}/input.fasta"
cp "${INPUT_FASTA}" "${SHORT_INPUT}"

# Create a short temp output directory
SHORT_OUTPUT_DIR="${SHORT_WORK_DIR}/out"
mkdir -p "${SHORT_OUTPUT_DIR}"

echo "Short input path length: $(echo -n "${SHORT_INPUT}" | wc -c) characters"
echo "Original input path length: $(echo -n "${INPUT_FASTA}" | wc -c) characters"

# =============================================================================
# RUN INTERPROSCAN
# =============================================================================
# Core command preserved from GIGANTIC_0:
#   interproscan.sh -i INPUT -goterms -dp -f tsv -cpu N -d output/
#
# Flags:
#   -i: Input FASTA file
#   -goterms: Include Gene Ontology term assignments
#   -dp: Disable precalculated match lookup (ensures fresh local analysis)
#   -f tsv: Output format as tab-separated values
#   -cpu: Number of threads for parallel processing
#   -d: Output directory
# =============================================================================

echo ""
echo "Running InterProScan..."
echo "This may take several hours depending on the number of sequences and databases."
echo ""

# Build the InterProScan command using SHORT paths
INTERPROSCAN_COMMAND="${INTERPROSCAN_EXECUTABLE} \
    -i ${SHORT_INPUT} \
    -goterms \
    -dp \
    -f tsv \
    -cpu ${CPUS} \
    -d ${SHORT_OUTPUT_DIR}"

# Add applications flag only if not 'all' (InterProScan runs all by default)
if [ "${APPLICATIONS}" != "all" ]; then
    INTERPROSCAN_COMMAND="${INTERPROSCAN_COMMAND} -appl ${APPLICATIONS}"
fi

echo "Command: ${INTERPROSCAN_COMMAND}"
echo ""

# Execute InterProScan
eval ${INTERPROSCAN_COMMAND}

INTERPROSCAN_EXIT_CODE=$?

if [ ${INTERPROSCAN_EXIT_CODE} -ne 0 ]; then
    echo "CRITICAL ERROR: InterProScan failed with exit code ${INTERPROSCAN_EXIT_CODE}!"
    echo "Check the output above for specific error messages."
    echo "Common issues:"
    echo "  - Java heap space: Increase memory allocation or reduce chunk size"
    echo "  - Database not found: Verify InterProScan databases are installed"
    echo "  - License issues: Some component databases may require separate licenses"
    # Clean up short path directory before exiting
    rm -rf "${SHORT_WORK_DIR}"
    exit 1
fi

echo "InterProScan completed successfully."

# =============================================================================
# LOCATE AND COPY OUTPUT FILE BACK
# =============================================================================
# InterProScan writes output to the -d directory with a filename based on the
# input file. We need to find it and copy it back to the real output location.
# =============================================================================

# Find the InterProScan TSV output file in the short path
INTERPROSCAN_OUTPUT_FILE=$(find "${SHORT_OUTPUT_DIR}" -name "*.tsv" -type f | head -1)

if [ -z "${INTERPROSCAN_OUTPUT_FILE}" ] || [ ! -f "${INTERPROSCAN_OUTPUT_FILE}" ]; then
    echo "CRITICAL ERROR: Could not locate InterProScan TSV output file!"
    echo "Expected results in: ${SHORT_OUTPUT_DIR}"
    echo "Directory contents:"
    ls -la "${SHORT_OUTPUT_DIR}"
    # Clean up short path directory before exiting
    rm -rf "${SHORT_WORK_DIR}"
    exit 1
fi

# Copy result back to the real output location
cp "${INTERPROSCAN_OUTPUT_FILE}" "${OUTPUT_TSV}"

# Clean up the short path temporary directory
rm -rf "${SHORT_WORK_DIR}"
echo "Cleaned up short path work directory: ${SHORT_WORK_DIR}"

# =============================================================================
# VALIDATE OUTPUT
# =============================================================================

echo ""
echo "Validating output..."

# Check output file exists
if [ ! -f "${OUTPUT_TSV}" ]; then
    echo "CRITICAL ERROR: Output TSV file was not created!"
    echo "Expected: ${OUTPUT_TSV}"
    exit 1
fi

# Count annotation lines in output
ANNOTATION_COUNT=$(wc -l < "${OUTPUT_TSV}")
echo "Total annotation lines: ${ANNOTATION_COUNT}"

# InterProScan may produce zero annotations for some chunks (all proteins
# have no detectable domains). This is valid but worth noting.
if [ "${ANNOTATION_COUNT}" -eq 0 ]; then
    echo "WARNING: InterProScan produced zero annotations for this chunk."
    echo "This can happen if proteins in the chunk have no detectable domains."
    echo "Creating empty output file to satisfy pipeline requirements."
    touch "${OUTPUT_TSV}"
fi

# =============================================================================
# COMPLETION
# =============================================================================

echo ""
echo "========================================================================"
echo "Script 003 completed successfully"
echo "========================================================================"
echo "  Input chunk: ${INPUT_FASTA}"
echo "  Sequences processed: ${SEQUENCE_COUNT}"
echo "  Annotations found: ${ANNOTATION_COUNT}"
echo "  Output: ${OUTPUT_TSV}"
