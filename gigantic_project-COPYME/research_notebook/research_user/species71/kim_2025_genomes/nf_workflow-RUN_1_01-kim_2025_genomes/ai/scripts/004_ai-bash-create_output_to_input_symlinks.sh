#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 11 18:25 | Purpose: Create relative symlinks in output_to_input/ pointing to T1 proteomes in OUTPUT_pipeline
# Human: Eric Edsinger

# =============================================================================
# 004_ai-bash-create_output_to_input_symlinks.sh
#
# Creates relative symlinks from the subproject output_to_input/T1_proteomes/
# directory back to the published T1 proteome files in OUTPUT_pipeline/3-output/.
#
# This avoids data duplication while making proteomes accessible to downstream
# GIGANTIC subprojects via the standard output_to_input/ pathway.
#
# Usage:
#   bash 004_ai-bash-create_output_to_input_symlinks.sh <source_dir> <target_dir>
#
# Arguments:
#   source_dir  - Directory containing the .aa proteome files (OUTPUT_pipeline/3-output/T1_proteomes)
#   target_dir  - Directory to create symlinks in (output_to_input/T1_proteomes)
#
# Output:
#   Relative symlinks in target_dir pointing to source_dir files
#   4-output/symlinks_manifest.tsv  (record of all symlinks created)
# =============================================================================

set -euo pipefail

SOURCE_DIRECTORY="$1"
TARGET_DIRECTORY="$2"

echo "============================================"
echo "004: Create output_to_input symlinks"
echo "============================================"
echo ""
echo "Source: ${SOURCE_DIRECTORY}"
echo "Target: ${TARGET_DIRECTORY}"
echo ""

# Verify source directory exists and has .aa files
if [ ! -d "${SOURCE_DIRECTORY}" ]; then
    echo "ERROR: Source directory not found: ${SOURCE_DIRECTORY}"
    exit 1
fi

AA_FILE_COUNT=$( ls -1 "${SOURCE_DIRECTORY}"/*.aa 2>/dev/null | wc -l )
if [ "${AA_FILE_COUNT}" -eq 0 ]; then
    echo "ERROR: No .aa files found in ${SOURCE_DIRECTORY}"
    exit 1
fi

echo "Found ${AA_FILE_COUNT} proteome files"
echo ""

# Create target directory
mkdir -p "${TARGET_DIRECTORY}"

# Calculate relative path from target to source
RELATIVE_PATH=$( python3 -c "import os; print( os.path.relpath( '${SOURCE_DIRECTORY}', '${TARGET_DIRECTORY}' ) )" )
echo "Relative path: ${RELATIVE_PATH}"
echo ""

# Create output directory for manifest
mkdir -p 4-output

# Create symlinks and manifest
echo -e "symlink_filename\trelative_target_path\tabsolute_source_path" > 4-output/symlinks_manifest.tsv

LINK_COUNT=0
for source_file in "${SOURCE_DIRECTORY}"/*.aa; do
    if [ -f "${source_file}" ]; then
        filename=$( basename "${source_file}" )
        ln -sf "${RELATIVE_PATH}/${filename}" "${TARGET_DIRECTORY}/${filename}"

        output="${filename}\t${RELATIVE_PATH}/${filename}\t${source_file}"
        echo -e "${output}" >> 4-output/symlinks_manifest.tsv

        echo "  Linked: ${filename}"
        LINK_COUNT=$(( LINK_COUNT + 1 ))
    fi
done

echo ""
echo "============================================"
echo "Created ${LINK_COUNT} symlinks in ${TARGET_DIRECTORY}"
echo "============================================"
echo ""

# Verify symlinks
echo "--- Verification ---"
for link in "${TARGET_DIRECTORY}"/*.aa; do
    if [ -L "${link}" ]; then
        if [ -e "${link}" ]; then
            echo "  OK: $(basename ${link})"
        else
            echo "  BROKEN: $(basename ${link}) -> $(readlink ${link})"
            exit 1
        fi
    fi
done

echo ""
echo "Done!"
