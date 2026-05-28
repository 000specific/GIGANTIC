#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Download genome, GFF3, and protein data from NCBI using datasets CLI
# Human: Eric Edsinger

# =============================================================================
# 001_ai-bash-download_ncbi_datasets.sh
#
# Downloads genome assembly, GFF3 annotation, and protein FASTA files from NCBI
# for each species listed in the input manifest, using the NCBI datasets CLI.
#
# Usage:
#   bash 001_ai-bash-download_ncbi_datasets.sh <manifest_path>
#
# Arguments:
#   manifest_path  - Path to TSV manifest with columns: genus_species, accession
#                    (default: INPUT_user/ncbi_genomes_manifest.tsv relative to
#                     the nf_workflow directory)
#
# Output:
#   1-output/downloads/Genus_species.zip  (one zip per species)
#
# Requires:
#   - NCBI datasets CLI (conda env: ncbi_datasets)
# =============================================================================

set -euo pipefail

MANIFEST_PATH="${1:-INPUT_user/ncbi_genomes_manifest.tsv}"

echo "============================================"
echo "001: Download NCBI datasets"
echo "============================================"
echo ""
echo "Manifest: ${MANIFEST_PATH}"
echo ""

# Validate manifest exists
if [ ! -f "${MANIFEST_PATH}" ]; then
    echo "ERROR: Manifest file not found: ${MANIFEST_PATH}"
    exit 1
fi

# Check that datasets CLI is available — activate ncbi_datasets env if needed
# (NextFlow spawns this script without the outer shell's conda env active)
if ! command -v datasets &> /dev/null; then
    echo "datasets CLI not in PATH — activating ncbi_datasets conda env..."
    source /etc/profile.d/modules.sh 2>/dev/null || true
    module load conda 2>&1 >/dev/null
    # conda function isn't available in this subshell; use the env's bin directly
    NCBI_DATASETS_BIN="/blue/moroz/share/edsinger/conda/envs/ncbi_datasets/bin"
    if [ -x "${NCBI_DATASETS_BIN}/datasets" ]; then
        export PATH="${NCBI_DATASETS_BIN}:${PATH}"
    fi
    if ! command -v datasets &> /dev/null; then
        echo "ERROR: NCBI datasets CLI still not found after env activation!"
        echo "  Tried: ${NCBI_DATASETS_BIN}/datasets"
        exit 1
    fi
fi

echo "datasets version: $( datasets --version 2>&1 )"
echo ""

# Create output directory
mkdir -p 1-output/downloads

# Count species (skip comment lines and header)
SPECIES_COUNT=$( grep -v '^#' "${MANIFEST_PATH}" | grep -v '^genus_species' | grep -v '^\s*$' | wc -l )
echo "Species to download: ${SPECIES_COUNT}"
echo ""

# Loop over manifest and download each species
DOWNLOAD_COUNT=0
FAILED_COUNT=0
FAILED_SPECIES=""

# genus_species	accession
# Intoshia_linei	GCA_001642005.1
grep -v '^#' "${MANIFEST_PATH}" | grep -v '^genus_species' | grep -v '^\s*$' | while IFS=$'\t' read -r genus_species accession; do

    DOWNLOAD_COUNT=$(( DOWNLOAD_COUNT + 1 ))
    echo "--------------------------------------------"
    echo "[${DOWNLOAD_COUNT}/${SPECIES_COUNT}] ${genus_species} (${accession})"
    echo "--------------------------------------------"

    OUTPUT_FILE="1-output/downloads/${genus_species}.zip"

    # Skip if already downloaded
    if [ -f "${OUTPUT_FILE}" ]; then
        echo "  Already exists, skipping: ${OUTPUT_FILE}"
        echo ""
        continue
    fi

    # Download genome, GFF3, protein, and CDS (CDS added 2026-04-20 for sono nucleotide analyses)
    # Retry loop for transient NCBI network failures (TLS timeouts, gateway errors)
    MAX_ATTEMPTS=4
    attempt=1
    download_success=false
    while [ "${attempt}" -le "${MAX_ATTEMPTS}" ]; do
        echo "  Downloading genome + gff3 + protein + cds (attempt ${attempt}/${MAX_ATTEMPTS})..."
        # Clear any partial zip from previous attempt
        rm -f "${OUTPUT_FILE}"
        if datasets download genome accession "${accession}" \
            --include genome,gff3,protein,cds \
            --filename "${OUTPUT_FILE}" 2>&1; then
            # Verify the zip is actually valid (not truncated) — unzip -t tests without extracting
            if unzip -t "${OUTPUT_FILE}" > /dev/null 2>&1; then
                echo "  SUCCESS: ${OUTPUT_FILE}"
                FILE_SIZE=$( du -h "${OUTPUT_FILE}" | cut -f1 )
                echo "  Size: ${FILE_SIZE}"
                download_success=true
                break
            else
                echo "  Downloaded zip corrupt/truncated; retrying..."
            fi
        else
            echo "  datasets CLI failed; retrying..."
        fi
        attempt=$(( attempt + 1 ))
        if [ "${attempt}" -le "${MAX_ATTEMPTS}" ]; then
            backoff=$(( attempt * 10 ))
            echo "  Waiting ${backoff}s before retry..."
            sleep "${backoff}"
        fi
    done
    if [ "${download_success}" = "false" ]; then
        echo "  FAILED after ${MAX_ATTEMPTS} attempts: ${genus_species} (${accession})"
        rm -f "${OUTPUT_FILE}"  # don't leave a bad zip
        FAILED_COUNT=$(( FAILED_COUNT + 1 ))
        FAILED_SPECIES="${FAILED_SPECIES} ${genus_species}"
    fi

    echo ""
done

echo "============================================"
echo "Download complete"
echo "============================================"
echo ""

# Count actual downloaded files
ACTUAL_COUNT=$( ls -1 1-output/downloads/*.zip 2>/dev/null | wc -l )
echo "Downloaded zip files: ${ACTUAL_COUNT}"
echo ""

# List all downloads with sizes
echo "--- Downloaded files ---"
for zip_file in 1-output/downloads/*.zip; do
    if [ -f "${zip_file}" ]; then
        FILE_SIZE=$( du -h "${zip_file}" | cut -f1 )
        echo "  $( basename "${zip_file}" ): ${FILE_SIZE}"
    fi
done

echo ""

# Fail if no files were downloaded
if [ "${ACTUAL_COUNT}" -eq 0 ]; then
    echo "ERROR: No files were downloaded!"
    exit 1
fi

echo "Done!"
