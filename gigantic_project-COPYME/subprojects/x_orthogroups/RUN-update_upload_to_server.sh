#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 26 | Purpose: Update upload_to_server symlinks from manifest
# Human: Eric Edsinger

################################################################################
# GIGANTIC Upload to Server - Symlink Manager
################################################################################
#
# PURPOSE:
# Create/update symlinks in upload_to_server/ based on the manifest file.
# This allows users to easily share selected outputs with collaborators via
# the GIGANTIC server.
#
# USAGE:
#   bash RUN-update_upload_to_server.sh [OPTIONS]
#
# OPTIONS:
#   --dry-run     Show what would be done without making changes
#   --clean       Remove all existing symlinks before creating new ones
#   --help        Show this help message
#
# HOW IT WORKS:
# 1. Reads upload_to_server/upload_manifest.tsv
# 2. For each line with "yes", creates symlink(s) in upload_to_server/
# 3. Glob patterns are expanded (e.g., *.tsv matches all .tsv files)
# 4. For workflow-RUN_* patterns: automatically selects the latest RUN
# 5. Stale symlinks (pointing to non-existent files) are removed
#
# MANIFEST FORMAT:
#   source_path<TAB>include
#   - Lines starting with # are comments
#   - source_path is relative to subproject root
#   - include must be "yes" to create symlink
#
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory (subproject root)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
UPLOAD_DIR="${SCRIPT_DIR}/upload_to_server"
MANIFEST="${UPLOAD_DIR}/upload_manifest.tsv"

# Options
DRY_RUN=false
CLEAN_FIRST=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --clean)
            CLEAN_FIRST=true
            shift
            ;;
        --help|-h)
            head -40 "$0" | grep -E "^#" | sed 's/^# //' | sed 's/^#//'
            exit 0
            ;;
        *)
            echo -e "${RED}ERROR: Unknown option: $1${NC}"
            echo "Use --help to see available options."
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

# Check manifest exists
if [ ! -f "$MANIFEST" ]; then
    echo -e "${RED}ERROR: Manifest not found at: ${MANIFEST}${NC}"
    echo ""
    echo "Please create upload_to_server/upload_manifest.tsv"
    exit 1
fi

# Clean existing symlinks if requested
if $CLEAN_FIRST; then
    echo -e "${YELLOW}Cleaning existing symlinks...${NC}"

    # Find all symlinks in upload_to_server (excluding manifest and README)
    symlinks=$(find "$UPLOAD_DIR" -maxdepth 1 -type l 2>/dev/null)

    for link in $symlinks; do
        link_name=$(basename "$link")
        if $DRY_RUN; then
            echo -e "  ${BLUE}[DRY RUN]${NC} Would remove: $link_name"
        else
            echo "  Removing: $link_name"
            rm "$link"
        fi
    done
    echo ""
fi

# Track counts
created_count=0
skipped_count=0
missing_count=0
stale_count=0

echo "Processing manifest..."
echo ""

# Read manifest and create symlinks
while IFS=$'\t' read -r source_path include || [ -n "$source_path" ]; do
    # Skip empty lines and comments
    [[ -z "$source_path" || "$source_path" =~ ^# ]] && continue

    # Only process lines with "yes"
    if [[ "$include" != "yes" ]]; then
        continue
    fi

    # Expand glob patterns
    full_pattern="${SCRIPT_DIR}/${source_path}"

    # Use compgen to safely expand globs
    matches=$(compgen -G "$full_pattern" 2>/dev/null || true)

    if [ -z "$matches" ]; then
        echo -e "  ${YELLOW}WARNING: No files match: ${source_path}${NC}"
        missing_count=$((missing_count + 1))
        continue
    fi

    # If pattern contains workflow-RUN_* and multiple matches exist,
    # keep only files from the latest (highest-numbered) RUN directory
    if [[ "$source_path" == *"workflow-RUN_"* ]]; then
        match_count=$(echo "$matches" | wc -l)
        if [ "$match_count" -gt 1 ]; then
            # Sort matches and keep only the last one (highest RUN number)
            latest_match=$(echo "$matches" | sort -t'_' -k2 -V | tail -n 1)
            latest_run_dir=$(echo "$latest_match" | grep -oP 'workflow-RUN_\d+-[^/]+')
            echo -e "  ${BLUE}Multiple RUNs found, using latest: ${latest_run_dir}${NC}"
            matches="$latest_match"
        fi
    fi

    for source_file in $matches; do
        if [ -f "$source_file" ]; then
            filename=$(basename "$source_file")
            link_path="${UPLOAD_DIR}/${filename}"

            # Check if symlink already exists and points to same target
            if [ -L "$link_path" ]; then
                current_target=$(readlink -f "$link_path" 2>/dev/null || true)
                new_target=$(readlink -f "$source_file" 2>/dev/null || true)

                if [ "$current_target" = "$new_target" ]; then
                    skipped_count=$((skipped_count + 1))
                    continue
                fi

                # Different target - remove old link
                if ! $DRY_RUN; then
                    rm "$link_path"
                fi
            fi

            if $DRY_RUN; then
                echo -e "  ${BLUE}[DRY RUN]${NC} Would create: $filename -> $(basename "$(dirname "$source_file")")/..."
            else
                # Create relative symlink
                relative_source=$(realpath --relative-to="$UPLOAD_DIR" "$source_file")
                ln -s "$relative_source" "$link_path"
                echo -e "  ${GREEN}Created:${NC} $filename"
            fi
            created_count=$((created_count + 1))
        fi
    done

done < "$MANIFEST"

# Remove stale symlinks (pointing to non-existent files)
echo ""
echo "Checking for stale symlinks..."

for link in $(find "$UPLOAD_DIR" -maxdepth 1 -type l 2>/dev/null); do
    if [ ! -e "$link" ]; then
        link_name=$(basename "$link")
        stale_count=$((stale_count + 1))

        if $DRY_RUN; then
            echo -e "  ${BLUE}[DRY RUN]${NC} Would remove stale: $link_name"
        else
            echo -e "  ${YELLOW}Removing stale:${NC} $link_name"
            rm "$link"
        fi
    fi
done

if [ $stale_count -eq 0 ]; then
    echo "  No stale symlinks found."
fi

# Summary
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
echo "Missing sources: ${missing_count}"
echo "Stale removed: ${stale_count}"
echo "========================================================================"
echo ""

# Show current contents
echo "Current upload_to_server/ contents:"
ls -la "$UPLOAD_DIR" | grep -v "^total" | grep -v "^\." || echo "  (empty)"
echo ""
