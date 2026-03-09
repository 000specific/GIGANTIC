#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 09 | Purpose: Download NCBI nr protein database FASTA
# Human: Eric Edsinger

# =============================================================================
# 001_ai-bash-download_ncbi_nr.sh
# =============================================================================
# Downloads the NCBI non-redundant (nr) protein FASTA file from NCBI FTP.
# Uses wget with -c (continue) flag to support resuming interrupted downloads.
#
# Usage:
#   bash 001_ai-bash-download_ncbi_nr.sh --url URL --output-file OUTPUT
#
# Arguments:
#   --url           NCBI nr FASTA download URL
#   --output-file   Output filename for the downloaded file
# =============================================================================

set -e

# ============================================================================
# Parse command-line arguments
# ============================================================================

DOWNLOAD_URL=""
OUTPUT_FILE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --url)
            DOWNLOAD_URL="$2"
            shift 2
            ;;
        --output-file)
            OUTPUT_FILE="$2"
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

if [ -z "${DOWNLOAD_URL}" ]; then
    echo "ERROR: --url is required"
    echo "Usage: bash 001_ai-bash-download_ncbi_nr.sh --url URL --output-file OUTPUT"
    exit 1
fi

if [ -z "${OUTPUT_FILE}" ]; then
    echo "ERROR: --output-file is required"
    echo "Usage: bash 001_ai-bash-download_ncbi_nr.sh --url URL --output-file OUTPUT"
    exit 1
fi

# ============================================================================
# Download NCBI nr FASTA
# ============================================================================

echo "========================================================================"
echo "Downloading NCBI nr protein FASTA"
echo "========================================================================"
echo "URL: ${DOWNLOAD_URL}"
echo "Output: ${OUTPUT_FILE}"
echo "Started: $(date)"
echo ""

wget -c "${DOWNLOAD_URL}" -O "${OUTPUT_FILE}"

# ============================================================================
# Verify download
# ============================================================================

if [ ! -f "${OUTPUT_FILE}" ]; then
    echo "ERROR: Download failed! Output file not found: ${OUTPUT_FILE}"
    exit 1
fi

FILE_SIZE=$(stat --printf="%s" "${OUTPUT_FILE}" 2>/dev/null || stat -f%z "${OUTPUT_FILE}" 2>/dev/null)

if [ "${FILE_SIZE}" -lt 1000000 ]; then
    echo "ERROR: Downloaded file is suspiciously small (${FILE_SIZE} bytes)."
    echo "Expected ~100 GB for NCBI nr. The download may have failed."
    exit 1
fi

echo ""
echo "========================================================================"
echo "Download complete!"
echo "File: ${OUTPUT_FILE}"
echo "Size: $(ls -lh "${OUTPUT_FILE}" | awk '{print $5}')"
echo "Completed: $(date)"
echo "========================================================================"
