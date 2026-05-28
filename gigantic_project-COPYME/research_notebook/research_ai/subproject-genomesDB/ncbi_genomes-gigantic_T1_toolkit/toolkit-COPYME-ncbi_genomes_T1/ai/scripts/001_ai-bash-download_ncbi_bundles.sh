#!/usr/bin/env bash
# AI: Claude Code | Opus 4.7 (1M context) | 2026 May 28 | Purpose: Download genome+GFF3+protein+CDS bundles from NCBI via the datasets CLI, with retry+integrity checks. Ground-up rebuild from RUN_2 lineage.
# Human: Eric Edsinger

# =============================================================================
# 001_ai-bash-download_ncbi_bundles.sh
#
# Downloads NCBI genome assembly bundles for every species in the input manifest
# using the NCBI datasets CLI. Each bundle includes genome FASTA, GFF3
# annotation, protein FASTA, and CDS FASTA. Outputs one zip per species.
#
# Resilient to transient NCBI failures: retry+exponential-backoff loop with
# zip-integrity validation between attempts. Skips already-downloaded zips on
# re-run (idempotent).
#
# Usage:
#   bash 001_ai-bash-download_ncbi_bundles.sh <manifest_path>
#
# Arguments:
#   manifest_path  - Path to TSV manifest with columns: genus_species, accession
#                    Lines starting with '#' are comments; header `genus_species`
#                    is also skipped.
#
# Output:
#   1-output/downloads/<Genus_species>.zip  (one zip per species)
#
# Requires:
#   - NCBI datasets CLI (provided by conda env aiG-toolkit-ncbi_genomes)
#   - unzip (standard on most systems)
# =============================================================================

set -euo pipefail

MANIFEST_PATH="${1:?ERROR: must supply manifest path as first argument}"

echo "============================================"
echo "001: Download NCBI bundles"
echo "============================================"
echo ""
echo "Manifest: ${MANIFEST_PATH}"
echo ""

if [ ! -f "${MANIFEST_PATH}" ]; then
    echo "ERROR: Manifest file not found: ${MANIFEST_PATH}"
    exit 1
fi

if ! command -v datasets &> /dev/null; then
    echo "ERROR: NCBI datasets CLI not found on PATH."
    echo "       Expected to be provided by the active conda env (aiG-toolkit-ncbi_genomes)."
    exit 1
fi

echo "datasets version: $( datasets --version 2>&1 )"
echo ""

mkdir -p 1-output/downloads

# Count species (skip comment lines, header row, blank lines)
SPECIES_COUNT=$( grep -v '^#' "${MANIFEST_PATH}" | grep -v '^genus_species' | grep -v '^[[:space:]]*$' | wc -l )
echo "Species to download: ${SPECIES_COUNT}"
echo ""

DOWNLOAD_COUNT=0
FAILED_COUNT=0
declare -a FAILED_SPECIES=()

while IFS=$'\t' read -r genus_species accession; do
    DOWNLOAD_COUNT=$(( DOWNLOAD_COUNT + 1 ))
    echo "--------------------------------------------"
    echo "[${DOWNLOAD_COUNT}/${SPECIES_COUNT}] ${genus_species} (${accession})"
    echo "--------------------------------------------"

    OUTPUT_FILE="1-output/downloads/${genus_species}.zip"

    if [ -f "${OUTPUT_FILE}" ]; then
        if unzip -t "${OUTPUT_FILE}" > /dev/null 2>&1; then
            echo "  Already downloaded and zip integrity OK; skipping."
            echo ""
            continue
        else
            echo "  Existing zip is corrupt; removing and re-downloading."
            rm -f "${OUTPUT_FILE}"
        fi
    fi

    MAX_ATTEMPTS=4
    attempt=1
    download_success=false
    while [ "${attempt}" -le "${MAX_ATTEMPTS}" ]; do
        echo "  Downloading genome+gff3+protein+cds (attempt ${attempt}/${MAX_ATTEMPTS})..."
        rm -f "${OUTPUT_FILE}"

        if datasets download genome accession "${accession}" \
            --include genome,gff3,protein,cds \
            --filename "${OUTPUT_FILE}" 2>&1; then

            if unzip -t "${OUTPUT_FILE}" > /dev/null 2>&1; then
                FILE_SIZE=$( du -h "${OUTPUT_FILE}" | cut -f1 )
                echo "  SUCCESS: ${OUTPUT_FILE} (${FILE_SIZE})"
                download_success=true
                break
            else
                echo "  Downloaded zip is corrupt/truncated; retrying..."
            fi
        else
            echo "  datasets CLI returned an error; retrying..."
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
        rm -f "${OUTPUT_FILE}"
        FAILED_COUNT=$(( FAILED_COUNT + 1 ))
        FAILED_SPECIES+=("${genus_species}")
    fi

    echo ""
done < <( grep -v '^#' "${MANIFEST_PATH}" | grep -v '^genus_species' | grep -v '^[[:space:]]*$' )

echo "============================================"
echo "Download complete"
echo "============================================"
echo ""

ACTUAL_COUNT=$( ls -1 1-output/downloads/*.zip 2>/dev/null | wc -l )
echo "Successfully downloaded: ${ACTUAL_COUNT} / ${SPECIES_COUNT}"

if [ "${FAILED_COUNT}" -gt 0 ]; then
    echo ""
    echo "FAILED species (${FAILED_COUNT}):"
    for species in "${FAILED_SPECIES[@]}"; do
        echo "  - ${species}"
    done
fi

echo ""
echo "--- Downloaded files ---"
for zip_file in 1-output/downloads/*.zip; do
    if [ -f "${zip_file}" ]; then
        FILE_SIZE=$( du -h "${zip_file}" | cut -f1 )
        echo "  $( basename "${zip_file}" ): ${FILE_SIZE}"
    fi
done

echo ""

# Fail-fast per gigantic_conventions.md §36: if nothing downloaded, error out.
if [ "${ACTUAL_COUNT}" -eq 0 ]; then
    echo "ERROR: No files were downloaded successfully."
    exit 1
fi

# Fail-fast per §36: if ANY species failed, surface loudly. Downstream processes
# depend on the manifest count matching the download count; silent partial
# success would cascade into confusing T1 extraction failures.
if [ "${FAILED_COUNT}" -gt 0 ]; then
    echo "ERROR: ${FAILED_COUNT} species failed to download. Fix and re-run."
    exit 1
fi

echo "Done."
