#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Create relative symlinks in output_to_input/ pointing to T1 proteomes in OUTPUT_pipeline
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
#   bash 004_ai-bash-create_output_to_input_symlinks.sh <enumerate_dir> <source_dir> <target_dir>
#
# Arguments:
#   enumerate_dir - Directory to enumerate .aa files from (NextFlow work dir input;
#                   guaranteed complete when process starts via channel dependency)
#   source_dir    - Published location where symlinks should POINT TO
#                   (OUTPUT_pipeline/3-output/T1_proteomes)
#   target_dir    - Directory to CREATE symlinks IN
#                   (output_to_input/T1_proteomes)
#
# Why 3 arguments?
#   NextFlow's publishDir copies files asynchronously. When Process 4 starts,
#   the work directory input (enumerate_dir) has all files, but the publishDir
#   destination (source_dir) may still be copying. We enumerate from the
#   guaranteed-complete work dir, but create symlinks pointing to the final
#   published location.
#
# Output:
#   Relative symlinks in target_dir pointing to source_dir files
#   4-output/symlinks_manifest.tsv  (record of all symlinks created)
# =============================================================================

set -euo pipefail

ENUMERATE_DIRECTORY="$1"
SOURCE_DIRECTORY="$2"
TARGET_DIRECTORY="$3"

echo "============================================"
echo "004: Create output_to_input symlinks"
echo "============================================"
echo ""
echo "Enumerate from: ${ENUMERATE_DIRECTORY}"
echo "Symlinks point to: ${SOURCE_DIRECTORY}"
echo "Symlinks created in: ${TARGET_DIRECTORY}"
echo ""

# Verify enumeration directory exists and has .aa files
if [ ! -d "${ENUMERATE_DIRECTORY}" ]; then
    echo "ERROR: Enumerate directory not found: ${ENUMERATE_DIRECTORY}"
    exit 1
fi

AA_FILE_COUNT=$( ls -1 "${ENUMERATE_DIRECTORY}"/*.aa 2>/dev/null | wc -l )
if [ "${AA_FILE_COUNT}" -eq 0 ]; then
    echo "ERROR: No .aa files found in ${ENUMERATE_DIRECTORY}"
    exit 1
fi

echo "Found ${AA_FILE_COUNT} proteome files"
echo ""

# Create target directory
mkdir -p "${TARGET_DIRECTORY}"

# Calculate relative path from target to source (the published location)
RELATIVE_PATH=$( python3 -c "import os; print( os.path.relpath( '${SOURCE_DIRECTORY}', '${TARGET_DIRECTORY}' ) )" )
echo "Relative path (target -> source): ${RELATIVE_PATH}"
echo ""

# Create output directory for manifest
mkdir -p 4-output

# Create symlinks and manifest
echo -e "symlink_filename\trelative_target_path\tabsolute_source_path" > 4-output/symlinks_manifest.tsv

LINK_COUNT=0
for enumerate_file in "${ENUMERATE_DIRECTORY}"/*.aa; do
    if [ -f "${enumerate_file}" ]; then
        filename=$( basename "${enumerate_file}" )
        ln -sf "${RELATIVE_PATH}/${filename}" "${TARGET_DIRECTORY}/${filename}"

        output="${filename}\t${RELATIVE_PATH}/${filename}\t${SOURCE_DIRECTORY}/${filename}"
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

# Note: Symlinks may show as PENDING here because publishDir has not yet copied
# the source files. They will resolve once NextFlow's publishDir completes.
# This is expected behavior when running inside NextFlow.
echo "--- Symlink status ---"
BROKEN_COUNT=0
for link in "${TARGET_DIRECTORY}"/*.aa; do
    if [ -L "${link}" ]; then
        if [ -e "${link}" ]; then
            echo "  OK: $(basename ${link})"
        else
            echo "  PENDING: $(basename ${link}) (will resolve when publishDir completes)"
            BROKEN_COUNT=$(( BROKEN_COUNT + 1 ))
        fi
    fi
done

if [ "${BROKEN_COUNT}" -gt 0 ]; then
    echo ""
    echo "NOTE: ${BROKEN_COUNT} symlinks are pending - they will resolve when"
    echo "NextFlow finishes publishing files to ${SOURCE_DIRECTORY}"
fi

echo ""
echo "Done!"
