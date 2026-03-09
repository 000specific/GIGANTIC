#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 09 | Purpose: Build BLAST protein database from NCBI nr FASTA
# Human: Eric Edsinger

# =============================================================================
# 002_ai-bash-build_blastp_database.sh
# =============================================================================
# Decompresses the NCBI nr.gz FASTA and builds a BLAST protein database
# using makeblastdb.
#
# GIGANTIC convention: Does NOT use -parse_seqids because many NCBI nr
# identifiers exceed the 50-character limit imposed by that flag.
#
# Usage:
#   bash 002_ai-bash-build_blastp_database.sh --input-file NR.GZ --output-dir DIR
#
# Arguments:
#   --input-file    Path to compressed nr.gz FASTA file
#   --output-dir    Output directory for BLAST database files
# =============================================================================

set -e

# ============================================================================
# Parse command-line arguments
# ============================================================================

INPUT_FILE=""
OUTPUT_DIR=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --input-file)
            INPUT_FILE="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        *)
            echo "ERROR: Unknown argument: $1"
            exit 1
            ;;
    esac
done

# ============================================================================
# Validate arguments
# ============================================================================

if [ -z "${INPUT_FILE}" ]; then
    echo "ERROR: --input-file is required"
    echo "Usage: bash 002_ai-bash-build_blastp_database.sh --input-file NR.GZ --output-dir DIR"
    exit 1
fi

if [ -z "${OUTPUT_DIR}" ]; then
    echo "ERROR: --output-dir is required"
    echo "Usage: bash 002_ai-bash-build_blastp_database.sh --input-file NR.GZ --output-dir DIR"
    exit 1
fi

if [ ! -f "${INPUT_FILE}" ]; then
    echo "ERROR: Input file not found: ${INPUT_FILE}"
    exit 1
fi

mkdir -p "${OUTPUT_DIR}"

# ============================================================================
# Step 1: Decompress nr.gz
# ============================================================================

echo "========================================================================"
echo "Building BLAST Protein Database from NCBI nr"
echo "========================================================================"
echo "Input: ${INPUT_FILE}"
echo "Output directory: ${OUTPUT_DIR}"
echo "Started: $(date)"
echo ""

DECOMPRESSED_FILE="${OUTPUT_DIR}/nr"

echo "Step 1: Decompressing ${INPUT_FILE}..."
echo "  This may take 30-60 minutes for the full NCBI nr database."
gunzip -k -c "${INPUT_FILE}" > "${DECOMPRESSED_FILE}"

if [ ! -f "${DECOMPRESSED_FILE}" ]; then
    echo "ERROR: Decompression failed! File not found: ${DECOMPRESSED_FILE}"
    exit 1
fi

echo "  Decompressed file size: $(ls -lh "${DECOMPRESSED_FILE}" | awk '{print $5}')"
echo ""

# ============================================================================
# Step 2: Build BLAST protein database with makeblastdb
# ============================================================================
# NOTE: Do NOT use -parse_seqids (GIGANTIC convention)
# Many NCBI nr identifiers exceed the 50-character limit imposed by
# -parse_seqids, which causes makeblastdb to fail.
# ============================================================================

echo "Step 2: Running makeblastdb..."
echo "  Database type: prot"
echo "  NOTE: Building WITHOUT -parse_seqids (GIGANTIC convention)"
echo ""

makeblastdb \
    -in "${DECOMPRESSED_FILE}" \
    -dbtype prot \
    -out "${OUTPUT_DIR}/nr"

echo ""
echo "  makeblastdb completed."
echo ""

# ============================================================================
# Step 3: Verify output files exist
# ============================================================================

echo "Step 3: Verifying BLAST database files..."

EXPECTED_FILES=( "nr.pdb" "nr.phr" "nr.pin" "nr.psq" "nr.pot" "nr.ptf" "nr.pto" )
MISSING_COUNT=0

for expected_file in "${EXPECTED_FILES[@]}"; do
    full_path="${OUTPUT_DIR}/${expected_file}"
    if [ -f "${full_path}" ]; then
        echo "  Found: ${expected_file} ($(ls -lh "${full_path}" | awk '{print $5}'))"
    else
        echo "  MISSING: ${expected_file}"
        MISSING_COUNT=$((MISSING_COUNT + 1))
    fi
done

if [ $MISSING_COUNT -gt 0 ]; then
    echo ""
    echo "ERROR: ${MISSING_COUNT} expected database file(s) missing!"
    echo "makeblastdb may have failed. Check error messages above."
    exit 1
fi

# ============================================================================
# Step 4: Clean up uncompressed FASTA to save disk space
# ============================================================================

echo ""
echo "Step 4: Cleaning up uncompressed FASTA to save disk space..."
rm -f "${DECOMPRESSED_FILE}"
echo "  Removed: ${DECOMPRESSED_FILE}"

echo ""
echo "========================================================================"
echo "BLAST protein database build complete!"
echo "Database: ${OUTPUT_DIR}/nr"
echo "Completed: $(date)"
echo "========================================================================"
