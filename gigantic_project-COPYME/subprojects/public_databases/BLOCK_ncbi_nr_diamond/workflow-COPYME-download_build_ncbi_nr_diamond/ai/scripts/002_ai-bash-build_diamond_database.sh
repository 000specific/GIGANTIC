#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 09 | Purpose: Build DIAMOND database from NCBI nr
# Human: Eric Edsinger

################################################################################
# Build DIAMOND Database from NCBI nr Protein FASTA
################################################################################
#
# Builds a DIAMOND search database from the NCBI nr gzipped FASTA file.
# DIAMOND can read gzipped input directly - no decompression needed.
#
# USAGE:
#   bash 002_ai-bash-build_diamond_database.sh --input-file NR.GZ --output-dir DIR --threads N
#
# ARGUMENTS:
#   --input-file    Path to nr.gz (gzipped FASTA)
#   --output-dir    Directory to save nr.dmnd (created if not exists)
#   --threads       Number of threads for DIAMOND makedb
#
# OUTPUT:
#   OUTPUT_DIR/nr.dmnd  (~150 GB DIAMOND database)
#
################################################################################

set -euo pipefail

# ============================================================================
# Parse arguments
# ============================================================================

INPUT_FILE=""
OUTPUT_DIR=""
THREADS=15

while [ $# -gt 0 ]; do
    case "$1" in
        --input-file)
            INPUT_FILE="$2"
            shift 2
            ;;
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --threads)
            THREADS="$2"
            shift 2
            ;;
        *)
            echo "ERROR: Unknown argument: $1"
            echo "Usage: bash 002_ai-bash-build_diamond_database.sh --input-file NR.GZ --output-dir DIR --threads N"
            exit 1
            ;;
    esac
done

# ============================================================================
# Validate arguments
# ============================================================================

if [ -z "${INPUT_FILE}" ]; then
    echo "ERROR: --input-file is required"
    exit 1
fi

if [ -z "${OUTPUT_DIR}" ]; then
    echo "ERROR: --output-dir is required"
    exit 1
fi

if [ ! -f "${INPUT_FILE}" ]; then
    echo "ERROR: Input file not found: ${INPUT_FILE}"
    exit 1
fi

# Check that DIAMOND is available
if ! command -v diamond &> /dev/null; then
    echo "ERROR: diamond not found in PATH"
    echo "Ensure the conda environment with DIAMOND is activated."
    exit 1
fi

# ============================================================================
# Build DIAMOND database
# ============================================================================

echo "========================================================================"
echo "Building DIAMOND database from NCBI nr"
echo "========================================================================"
echo ""
echo "Input: ${INPUT_FILE}"
echo "Output: ${OUTPUT_DIR}/nr.dmnd"
echo "Threads: ${THREADS}"
echo "DIAMOND version: $(diamond version 2>&1 | head -1)"
echo "Started: $(date)"
echo ""

mkdir -p "${OUTPUT_DIR}"

# DIAMOND makedb reads gzipped FASTA directly
# --in: input FASTA (gzipped OK)
# -d: output database prefix (DIAMOND adds .dmnd extension)
# --threads: number of CPU threads
diamond makedb \
    --in "${INPUT_FILE}" \
    -d "${OUTPUT_DIR}/nr" \
    --threads "${THREADS}"

DIAMOND_EXIT_CODE=$?

if [ ${DIAMOND_EXIT_CODE} -ne 0 ]; then
    echo ""
    echo "ERROR: diamond makedb failed with exit code ${DIAMOND_EXIT_CODE}"
    exit 1
fi

# ============================================================================
# Verify output
# ============================================================================

if [ ! -f "${OUTPUT_DIR}/nr.dmnd" ]; then
    echo "ERROR: DIAMOND database not found at ${OUTPUT_DIR}/nr.dmnd"
    exit 1
fi

DATABASE_SIZE=$(stat --printf="%s" "${OUTPUT_DIR}/nr.dmnd" 2>/dev/null || stat -f "%z" "${OUTPUT_DIR}/nr.dmnd" 2>/dev/null || echo "0")

if [ "${DATABASE_SIZE}" -eq 0 ]; then
    echo "ERROR: DIAMOND database is empty (0 bytes)"
    rm -f "${OUTPUT_DIR}/nr.dmnd"
    exit 1
fi

# Convert to human-readable size
DATABASE_SIZE_HUMAN=$(ls -lh "${OUTPUT_DIR}/nr.dmnd" | awk '{print $5}')

echo ""
echo "========================================================================"
echo "DIAMOND database build complete!"
echo "  Database: ${OUTPUT_DIR}/nr.dmnd"
echo "  Size: ${DATABASE_SIZE_HUMAN}"
echo "  Timestamp: $(date)"
echo "========================================================================"
