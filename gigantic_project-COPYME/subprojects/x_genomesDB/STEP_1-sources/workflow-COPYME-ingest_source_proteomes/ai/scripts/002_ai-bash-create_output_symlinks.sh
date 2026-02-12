#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 12 | Purpose: Create symlinks in output_to_input for STEP_2
# Human: Eric Edsinger
#
# This script creates symlinks from STEP_1-sources/output_to_input/proteomes/
# to the hard-copied proteomes in OUTPUT_pipeline/1-output/proteomes/
#
# This provides a clean interface for STEP_2 while preserving the archived
# copies in OUTPUT_pipeline.

set -e

# Arguments
PROTEOME_DIR="$1"       # Path to OUTPUT_pipeline/1-output/proteomes/
OUTPUT_TO_INPUT="$2"    # Path to ../../output_to_input (STEP_1 level)

echo "========================================================================"
echo "Creating output_to_input symlinks"
echo "========================================================================"
echo "Source: ${PROTEOME_DIR}"
echo "Destination: ${OUTPUT_TO_INPUT}"
echo ""

# Create output_to_input/proteomes directory
SYMLINK_DIR="${OUTPUT_TO_INPUT}/proteomes"
mkdir -p "${SYMLINK_DIR}"

# Count files
FILE_COUNT=$(find "${PROTEOME_DIR}" -maxdepth 1 -type f -name "*.aa" -o -name "*.fasta" -o -name "*.fa" | wc -l)
echo "Found ${FILE_COUNT} proteome files to link"
echo ""

# Create symlinks
LINKED=0
for proteome_file in "${PROTEOME_DIR}"/*.aa "${PROTEOME_DIR}"/*.fasta "${PROTEOME_DIR}"/*.fa; do
    # Skip if glob didn't match anything
    [ -e "$proteome_file" ] || continue

    filename=$(basename "${proteome_file}")
    symlink_path="${SYMLINK_DIR}/${filename}"

    # Calculate relative path from symlink location to target
    # This makes symlinks portable
    rel_path=$(realpath --relative-to="${SYMLINK_DIR}" "${proteome_file}")

    # Remove existing symlink if present
    if [ -L "${symlink_path}" ]; then
        rm "${symlink_path}"
    fi

    # Create symlink
    ln -s "${rel_path}" "${symlink_path}"
    echo "  Linked: ${filename}"
    LINKED=$((LINKED + 1))
done

echo ""
echo "========================================================================"
echo "Created ${LINKED} symlinks in output_to_input/proteomes/"
echo "========================================================================"

# Write manifest of symlinked files
MANIFEST="${OUTPUT_TO_INPUT}/proteome_manifest.tsv"
echo "# GIGANTIC Proteome Manifest - STEP_1 Output" > "${MANIFEST}"
echo "# Generated: $(date)" >> "${MANIFEST}"
echo "# Source: ${PROTEOME_DIR}" >> "${MANIFEST}"
echo "#" >> "${MANIFEST}"
echo "filename	symlink_path" >> "${MANIFEST}"

for symlink_file in "${SYMLINK_DIR}"/*; do
    [ -e "$symlink_file" ] || continue
    filename=$(basename "${symlink_file}")
    echo "${filename}	${symlink_file}" >> "${MANIFEST}"
done

echo "Manifest written to: ${MANIFEST}"
