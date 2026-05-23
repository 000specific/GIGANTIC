#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 May 05 | Purpose: Update upload_to_server symlinks from manifest
# Human: Eric Edsinger

################################################################################
# GIGANTIC Upload to Server - Symlink Manager
################################################################################
#
# PURPOSE:
# Create/update symlinks in upload_to_server/ from the upload_manifest.tsv.
# Lets users share selected outputs with collaborators via the GIGANTIC server.
#
# USAGE:
#   bash RUN-update_upload_to_server.sh [OPTIONS]
#
# OPTIONS:
#   --dry-run     Show what would be done without making changes
#   --clean       Remove all existing symlinks before creating new ones
#   --help        Show this help message
#
# MANIFEST FORMAT:
#   source_path<TAB>include
#   - Lines starting with # are comments
#   - source_path is relative to subproject root, glob patterns OK (e.g. *.tsv)
#   - include must be "yes" to create the symlink (anything else = skip)
#
# Each glob match becomes one symlink in upload_to_server/ flat (not nested).
# Specify the explicit workflow RUN dir in the manifest path
# (e.g. `BLOCK_X/workflow-RUN_1-name/.../*.tsv`); do not use a wildcard
# `workflow-RUN_*` — that creates ambiguity over which run is canonical.
#
################################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
UPLOAD_DIR="${SCRIPT_DIR}/upload_to_server"
MANIFEST="${UPLOAD_DIR}/upload_manifest.tsv"

DRY_RUN=false
CLEAN_FIRST=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true; shift ;;
        --clean)   CLEAN_FIRST=true; shift ;;
        --help|-h)
            head -40 "$0" | grep -E "^#" | sed 's/^# //' | sed 's/^#//'
            exit 0
            ;;
        *)
            echo -e "${RED}ERROR: Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

echo "========================================================================"
echo "GIGANTIC Upload to Server - Symlink Manager"
echo "========================================================================"
echo ""
echo "Subproject: $(basename "$SCRIPT_DIR")"
echo ""

if $DRY_RUN; then
    echo -e "${BLUE}DRY RUN MODE - No changes will be made${NC}"
    echo ""
fi

if [ ! -f "$MANIFEST" ]; then
    echo -e "${RED}ERROR: Manifest not found at: ${MANIFEST}${NC}"
    exit 1
fi

if $CLEAN_FIRST; then
    echo -e "${YELLOW}Cleaning existing symlinks...${NC}"
    while IFS= read -r -d '' link; do
        name=$(basename "$link")
        if $DRY_RUN; then
            echo -e "  ${BLUE}[DRY RUN]${NC} Would remove: $name"
        else
            rm "$link"
            echo "  Removed: $name"
        fi
    done < <(find "$UPLOAD_DIR" -maxdepth 1 -type l -print0)
    echo ""
fi

created_count=0
skipped_count=0
missing_count=0
stale_count=0

echo "Processing manifest..."
echo ""

while IFS=$'\t' read -r source_path include rest || [ -n "$source_path" ]; do
    [[ -z "$source_path" || "$source_path" =~ ^# ]] && continue
    [[ "$include" != "yes" ]] && continue

    full_pattern="${SCRIPT_DIR}/${source_path}"

    # Expand glob into an array of matches.
    # Using mapfile ensures every match is treated as a separate file rather
    # than collapsed into one whitespace-joined string (which the older
    # orthogroups script then mangled with a "latest RUN" dedup that
    # incorrectly applied to multi-species globs).
    mapfile -t matches < <( compgen -G "$full_pattern" 2>/dev/null || true )

    if [ ${#matches[@]} -eq 0 ]; then
        echo -e "  ${YELLOW}WARNING: No files match: ${source_path}${NC}"
        missing_count=$((missing_count + 1))
        continue
    fi

    for source_file in "${matches[@]}"; do
        [ -f "$source_file" ] || continue

        filename=$(basename "$source_file")
        link_path="${UPLOAD_DIR}/${filename}"

        if [ -L "$link_path" ]; then
            current_target=$(readlink -f "$link_path" 2>/dev/null || true)
            new_target=$(readlink -f "$source_file" 2>/dev/null || true)
            if [ "$current_target" = "$new_target" ]; then
                skipped_count=$((skipped_count + 1))
                continue
            fi
            $DRY_RUN || rm "$link_path"
        fi

        if $DRY_RUN; then
            echo -e "  ${BLUE}[DRY RUN]${NC} Would create: ${filename}"
        else
            relative_source=$(realpath --relative-to="$UPLOAD_DIR" "$source_file")
            ln -s "$relative_source" "$link_path"
            echo -e "  ${GREEN}Created:${NC} ${filename}"
        fi
        created_count=$((created_count + 1))
    done

done < "$MANIFEST"

echo ""
echo "Checking for stale symlinks..."
while IFS= read -r -d '' link; do
    if [ ! -e "$link" ]; then
        name=$(basename "$link")
        stale_count=$((stale_count + 1))
        if $DRY_RUN; then
            echo -e "  ${BLUE}[DRY RUN]${NC} Would remove stale: $name"
        else
            rm "$link"
            echo -e "  ${YELLOW}Removed stale:${NC} $name"
        fi
    fi
done < <(find "$UPLOAD_DIR" -maxdepth 1 -type l -print0)

if [ $stale_count -eq 0 ]; then
    echo "  No stale symlinks found."
fi

echo ""
echo "========================================================================"
if $DRY_RUN; then
    echo -e "${BLUE}DRY RUN SUMMARY${NC}"
    echo "Would create: ${created_count} symlink(s)"
else
    echo -e "${GREEN}SUMMARY${NC}"
    echo "Created: ${created_count} symlink(s)"
fi
echo "Skipped (unchanged): ${skipped_count}"
echo "Missing sources:     ${missing_count}"
echo "Stale removed:       ${stale_count}"
echo "========================================================================"
echo ""

total_links=$( find "$UPLOAD_DIR" -maxdepth 1 -type l 2>/dev/null | wc -l )
echo "Current upload_to_server/ symlink count: ${total_links}"
echo ""
