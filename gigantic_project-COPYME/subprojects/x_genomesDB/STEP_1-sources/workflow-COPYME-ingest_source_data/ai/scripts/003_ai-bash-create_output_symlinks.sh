#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 13 16:00 | Purpose: Create symlinks in output_to_input and write symlink manifest
# Human: Eric Edsinger
#
# 003_ai-bash-create_output_symlinks.sh
#
# STEP 3 of 3 in the source data ingestion workflow.
#
# Creates symlinks in STEP_1-sources/output_to_input/ pointing to the
# hard-copied files in OUTPUT_pipeline/2-output/. Also writes a manifest
# documenting every symlink to OUTPUT_pipeline/3-output/.
#
# This provides a clean interface for STEP_2 while preserving the
# archived copies in OUTPUT_pipeline/2-output/.
#
# Usage:
#   bash 003_ai-bash-create_output_symlinks.sh \
#       <source_dir> <output_to_input_dir> <manifest_output_dir>
#
# Arguments:
#   source_dir          Path to OUTPUT_pipeline/2-output/ (the ingested data)
#   output_to_input_dir Path to ../../output_to_input (STEP_1 level)
#   manifest_output_dir Path to OUTPUT_pipeline/3-output/ (where symlink manifest goes)

set -e

# ============================================================================
# Arguments
# ============================================================================

SOURCE_DIR="$1"
OUTPUT_TO_INPUT="$2"
MANIFEST_OUTPUT_DIR="$3"

echo "============================================================"
echo "STEP 3: Create output_to_input Symlinks"
echo "============================================================"
echo "Source: ${SOURCE_DIR}"
echo "Symlink destination: ${OUTPUT_TO_INPUT}"
echo "Manifest output: ${MANIFEST_OUTPUT_DIR}"
echo ""

# Validate arguments
if [ -z "$SOURCE_DIR" ] || [ -z "$OUTPUT_TO_INPUT" ] || [ -z "$MANIFEST_OUTPUT_DIR" ]; then
    echo "CRITICAL ERROR: Missing arguments!"
    echo "Usage: bash 003_ai-bash-create_output_symlinks.sh <source_dir> <output_to_input_dir> <manifest_output_dir>"
    exit 1
fi

if [ ! -d "$SOURCE_DIR" ]; then
    echo "CRITICAL ERROR: Source directory not found: ${SOURCE_DIR}"
    exit 1
fi

# Create output directories
mkdir -p "${OUTPUT_TO_INPUT}"
mkdir -p "${MANIFEST_OUTPUT_DIR}"

# ============================================================================
# Create symlinks
# ============================================================================

DATA_TYPES=("T1_proteomes" "genomes" "gene_annotations")

declare -A EXTENSIONS
EXTENSIONS[T1_proteomes]="*.aa"
EXTENSIONS[genomes]="*.fasta"
EXTENSIONS[gene_annotations]="*.gff3 *.gtf"

TOTAL_LINKED=0

# Initialize manifest
MANIFEST="${MANIFEST_OUTPUT_DIR}/3_ai-symlink_manifest.tsv"
echo -e "Data_Type (type of data)\tFilename (original filename preserved)\tSymlink_Path (location in output_to_input)\tTarget_Path (relative path to hard copy in OUTPUT_pipeline 2-output)" > "${MANIFEST}"

for DATA_TYPE in "${DATA_TYPES[@]}"; do
    SOURCE_SUBDIR="${SOURCE_DIR}/${DATA_TYPE}"
    SYMLINK_DIR="${OUTPUT_TO_INPUT}/${DATA_TYPE}"

    echo "--- ${DATA_TYPE} ---"

    if [ ! -d "${SOURCE_SUBDIR}" ]; then
        echo "  Source directory not found: ${SOURCE_SUBDIR}"
        echo "  Skipping ${DATA_TYPE}"
        echo ""
        continue
    fi

    mkdir -p "${SYMLINK_DIR}"

    LINKED=0

    for PATTERN in ${EXTENSIONS[$DATA_TYPE]}; do
        for source_file in "${SOURCE_SUBDIR}"/${PATTERN}; do
            [ -e "$source_file" ] || continue

            filename=$(basename "${source_file}")
            symlink_path="${SYMLINK_DIR}/${filename}"

            # Calculate relative path from symlink location to target
            rel_path=$(realpath --relative-to="${SYMLINK_DIR}" "${source_file}")

            # Remove existing symlink if present
            if [ -L "${symlink_path}" ]; then
                rm "${symlink_path}"
            fi

            # Create symlink
            ln -s "${rel_path}" "${symlink_path}"
            LINKED=$((LINKED + 1))

            # Write to manifest
            echo -e "${DATA_TYPE}\t${filename}\t${symlink_path}\t${rel_path}" >> "${MANIFEST}"
        done
    done

    echo "  Created ${LINKED} symlinks"
    TOTAL_LINKED=$((TOTAL_LINKED + LINKED))
    echo ""
done

echo "============================================================"
echo "Total symlinks created: ${TOTAL_LINKED}"
echo "Symlink manifest: ${MANIFEST}"
echo "============================================================"
