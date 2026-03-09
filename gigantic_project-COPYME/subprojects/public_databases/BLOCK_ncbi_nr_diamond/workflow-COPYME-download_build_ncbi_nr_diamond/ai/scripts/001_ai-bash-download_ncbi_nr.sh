#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 09 | Purpose: Download NCBI nr protein database
# Human: Eric Edsinger

################################################################################
# Download NCBI nr Protein Database (gzipped FASTA)
################################################################################
#
# Downloads the NCBI non-redundant protein database (nr.gz) using wget.
# Uses -c flag to support resuming interrupted downloads.
#
# USAGE:
#   bash 001_ai-bash-download_ncbi_nr.sh --output-dir OUTPUT_DIR --url URL
#
# ARGUMENTS:
#   --output-dir    Directory to save nr.gz (created if not exists)
#   --url           NCBI FTP URL for nr.gz
#
# OUTPUT:
#   OUTPUT_DIR/nr.gz  (~100 GB compressed FASTA)
#
################################################################################

set -euo pipefail

# ============================================================================
# Parse arguments
# ============================================================================

OUTPUT_DIR=""
DOWNLOAD_URL=""

while [ $# -gt 0 ]; do
    case "$1" in
        --output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --url)
            DOWNLOAD_URL="$2"
            shift 2
            ;;
        *)
            echo "ERROR: Unknown argument: $1"
            echo "Usage: bash 001_ai-bash-download_ncbi_nr.sh --output-dir DIR --url URL"
            exit 1
            ;;
    esac
done

# ============================================================================
# Validate arguments
# ============================================================================

if [ -z "${OUTPUT_DIR}" ]; then
    echo "ERROR: --output-dir is required"
    exit 1
fi

if [ -z "${DOWNLOAD_URL}" ]; then
    echo "ERROR: --url is required"
    exit 1
fi

# ============================================================================
# Download NCBI nr
# ============================================================================

echo "========================================================================"
echo "Downloading NCBI nr protein database"
echo "========================================================================"
echo ""
echo "URL: ${DOWNLOAD_URL}"
echo "Output: ${OUTPUT_DIR}/nr.gz"
echo "Started: $(date)"
echo ""

mkdir -p "${OUTPUT_DIR}"

# Download with resume support (-c) and progress display
wget -c -q --show-progress \
    -O "${OUTPUT_DIR}/nr.gz" \
    "${DOWNLOAD_URL}"

WGET_EXIT_CODE=$?

if [ ${WGET_EXIT_CODE} -ne 0 ]; then
    echo ""
    echo "ERROR: wget failed with exit code ${WGET_EXIT_CODE}"
    echo "The download may have been interrupted. Re-run to resume (wget -c)."
    exit 1
fi

# ============================================================================
# Verify download
# ============================================================================

if [ ! -f "${OUTPUT_DIR}/nr.gz" ]; then
    echo "ERROR: Downloaded file not found at ${OUTPUT_DIR}/nr.gz"
    exit 1
fi

FILE_SIZE=$(stat --printf="%s" "${OUTPUT_DIR}/nr.gz" 2>/dev/null || stat -f "%z" "${OUTPUT_DIR}/nr.gz" 2>/dev/null || echo "0")

if [ "${FILE_SIZE}" -eq 0 ]; then
    echo "ERROR: Downloaded file is empty (0 bytes)"
    rm -f "${OUTPUT_DIR}/nr.gz"
    exit 1
fi

# Convert to human-readable size
FILE_SIZE_HUMAN=$(ls -lh "${OUTPUT_DIR}/nr.gz" | awk '{print $5}')

echo ""
echo "========================================================================"
echo "Download complete!"
echo "  File: ${OUTPUT_DIR}/nr.gz"
echo "  Size: ${FILE_SIZE_HUMAN}"
echo "  Timestamp: $(date)"
echo "========================================================================"
