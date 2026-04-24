#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Master download script that loops over per-species download scripts for repository genomes
# Human: Eric Edsinger

# =============================================================================
# 001_ai-bash-download_repository_genomes.sh
#
# Orchestrates the download of genome data from various external repositories.
# Reads the manifest to get the species list, then for each species, runs its
# per-species download script located in:
#
#   ai/scripts/per_species/{genus_species}/download.sh
#
# Each per-species script is responsible for downloading whatever data is
# available (genome, annotation, protein) and placing it into:
#
#   1-output/{genus_species}/
#
# Per-species scripts should create one or more of these files:
#   1-output/{genus_species}/genome.fasta     (genome assembly)
#   1-output/{genus_species}/annotation.gff3  (GFF3 annotation)
#   1-output/{genus_species}/annotation.gtf   (GTF annotation, if GFF3 not available)
#   1-output/{genus_species}/protein.faa      (protein sequences, if available)
#   1-output/{genus_species}/download_log.txt (log of what was downloaded)
#
# If a per-species download script does not exist, the species is SKIPPED
# (not failed) -- this allows incremental development of download scripts.
#
# Usage:
#   bash 001_ai-bash-download_repository_genomes.sh <scripts_dir> <manifest_path>
#
# Arguments:
#   scripts_dir    - Path to ai/scripts/ directory (contains per_species/)
#   manifest_path  - Path to repository_genomes_manifest.tsv
#
# Output:
#   1-output/{genus_species}/  (one directory per species with downloaded files)
# =============================================================================

set -euo pipefail

SCRIPTS_DIRECTORY="$1"
MANIFEST_PATH="$2"

echo "============================================"
echo "001: Download repository genomes"
echo "============================================"
echo ""
echo "Scripts directory: ${SCRIPTS_DIRECTORY}"
echo "Manifest: ${MANIFEST_PATH}"
echo ""

# Validate inputs
if [ ! -d "${SCRIPTS_DIRECTORY}" ]; then
    echo "ERROR: Scripts directory not found: ${SCRIPTS_DIRECTORY}"
    exit 1
fi

if [ ! -f "${MANIFEST_PATH}" ]; then
    echo "ERROR: Manifest file not found: ${MANIFEST_PATH}"
    exit 1
fi

# Create output directory
mkdir -p 1-output

# Count species (skip comment lines and header)
SPECIES_COUNT=$( grep -v '^#' "${MANIFEST_PATH}" | grep -v '^genus_species' | grep -v '^\s*$' | wc -l )
echo "Species in manifest: ${SPECIES_COUNT}"
echo ""

# Track results
PROCESSED_COUNT=0
SKIPPED_COUNT=0
FAILED_COUNT=0
SKIPPED_SPECIES=""
FAILED_SPECIES=""

# genus_species	repository_url	genome_url	annotation_url	protein_url
# Lissachatina_fulica	http://gigadb.org/dataset/100647			
# NOTE: Using 'cut' for field extraction because bash 'IFS=$'\t' read' collapses
# consecutive tabs into one delimiter, which breaks parsing of empty fields.
grep -v '^#' "${MANIFEST_PATH}" | grep -v '^genus_species' | grep -v '^\s*$' | while IFS= read -r manifest_line; do

    genus_species=$( printf '%s' "${manifest_line}" | cut -f1 )
    repository_url=$( printf '%s' "${manifest_line}" | cut -f2 )
    genome_url=$( printf '%s' "${manifest_line}" | cut -f3 )
    annotation_url=$( printf '%s' "${manifest_line}" | cut -f4 )
    protein_url=$( printf '%s' "${manifest_line}" | cut -f5 )

    echo "--------------------------------------------"
    echo "${genus_species}"
    echo "  Repository: ${repository_url}"
    echo "--------------------------------------------"

    PER_SPECIES_SCRIPT="${SCRIPTS_DIRECTORY}/per_species/${genus_species}/download.sh"

    # Check if per-species download script exists
    if [ ! -f "${PER_SPECIES_SCRIPT}" ]; then
        echo "  SKIPPED: No download script found"
        echo "  Expected: ${PER_SPECIES_SCRIPT}"
        SKIPPED_COUNT=$(( SKIPPED_COUNT + 1 ))
        SKIPPED_SPECIES="${SKIPPED_SPECIES} ${genus_species}"
        echo ""
        continue
    fi

    # Create per-species output directory
    SPECIES_OUTPUT_DIRECTORY="1-output/${genus_species}"
    mkdir -p "${SPECIES_OUTPUT_DIRECTORY}"

    # Run per-species download script
    # Pass: output_dir, repository_url, genome_url, annotation_url, protein_url
    echo "  Running: ${PER_SPECIES_SCRIPT}"
    if bash "${PER_SPECIES_SCRIPT}" \
        "${SPECIES_OUTPUT_DIRECTORY}" \
        "${repository_url}" \
        "${genome_url:-}" \
        "${annotation_url:-}" \
        "${protein_url:-}" 2>&1; then

        # Check what files were downloaded
        FILE_COUNT=$( ls -1 "${SPECIES_OUTPUT_DIRECTORY}" 2>/dev/null | wc -l )
        echo "  SUCCESS: ${FILE_COUNT} files in ${SPECIES_OUTPUT_DIRECTORY}/"

        # List downloaded files
        for downloaded_file in "${SPECIES_OUTPUT_DIRECTORY}"/*; do
            if [ -f "${downloaded_file}" ]; then
                FILE_SIZE=$( du -h "${downloaded_file}" | cut -f1 )
                echo "    $( basename "${downloaded_file}" ): ${FILE_SIZE}"
            fi
        done

        PROCESSED_COUNT=$(( PROCESSED_COUNT + 1 ))
    else
        echo "  FAILED: Download script returned error"
        FAILED_COUNT=$(( FAILED_COUNT + 1 ))
        FAILED_SPECIES="${FAILED_SPECIES} ${genus_species}"
    fi

    echo ""
done

echo "============================================"
echo "Download complete"
echo "============================================"
echo ""

# Count actual species directories with files
ACTUAL_DIRS=$( find 1-output -mindepth 1 -maxdepth 1 -type d | wc -l )
DIRS_WITH_FILES=$( find 1-output -mindepth 1 -maxdepth 1 -type d -exec sh -c 'ls -1 "$1"/* 2>/dev/null | head -1 | grep -q . && echo "$1"' _ {} \; 2>/dev/null | wc -l )

echo "Species in manifest:           ${SPECIES_COUNT}"
echo "Species with download scripts: ${ACTUAL_DIRS}"
echo "Species with downloaded files:  ${DIRS_WITH_FILES}"
echo ""

if [ "${DIRS_WITH_FILES}" -eq 0 ]; then
    echo "WARNING: No species have been downloaded yet."
    echo "Per-species download scripts need to be created in:"
    echo "  ${SCRIPTS_DIRECTORY}/per_species/{genus_species}/download.sh"
    echo ""
    echo "This is expected during initial setup -- scripts are added incrementally."
    # Exit 0 intentionally: having no scripts yet is OK during development
    exit 0
fi

# List summary of what was downloaded
echo "--- Downloaded species ---"
for species_dir in 1-output/*/; do
    if [ -d "${species_dir}" ]; then
        species_name=$( basename "${species_dir}" )
        has_genome="  "
        has_annotation="  "
        has_protein="  "

        [ -f "${species_dir}/genome.fasta" ] && has_genome="G "
        [ -f "${species_dir}/annotation.gff3" ] || [ -f "${species_dir}/annotation.gtf" ] && has_annotation="A "
        [ -f "${species_dir}/protein.faa" ] && has_protein="P "

        echo "  [${has_genome}${has_annotation}${has_protein}] ${species_name}"
    fi
done
echo ""
echo "  Legend: G=genome, A=annotation, P=protein"

echo ""
echo "Done!"
