#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 12 | Purpose: Clean up subproject and record AI sessions
# Human: Eric Edsinger

################################################################################
# GIGANTIC Subproject Cleanup and Recording Script
################################################################################
#
# PURPOSE:
# Clean up temporary files and record AI session provenance.
# Run this after confirming your workflow results are correct.
#
# USAGE:
#   bash RUN-clean_and_record_subproject.sh [OPTIONS]
#
# OPTIONS:
#   --clean-work       Remove work/ and .nextflow* from all workflow directories
#   --harden-links     Convert softlinks to hard copies in upload_to_server/
#   --remove-gitkeep   Remove .gitkeep files from non-empty directories
#   --record-sessions  Extract Claude Code session summaries to research_notebook/
#   --all              Run all cleanup operations (includes --record-sessions)
#   --dry-run          Show what would be done without making changes
#   --help             Show this help message
#
# EXAMPLES:
#   bash RUN-clean_and_record_subproject.sh --dry-run --all    # Preview all operations
#   bash RUN-clean_and_record_subproject.sh --record-sessions  # Only extract sessions
#   bash RUN-clean_and_record_subproject.sh --clean-work       # Only remove temp files
#   bash RUN-clean_and_record_subproject.sh --all              # Do everything
#
# SESSION RECORDING:
#   Extracts Claude Code context compaction summaries from ~/.claude/projects/
#   and saves them to research_notebook/research_ai/project/sessions/
#   This provides research provenance for AI-assisted work.
#   Safe to run multiple times - overwrites with complete current state.
#
# WARNING:
#   --clean-work is DESTRUCTIVE! NextFlow's work/ directory contains all
#   intermediate files. Once deleted, you cannot use -resume to continue
#   a failed run. Only clean after successful completion.
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

# Find project root (parent of subprojects/)
PROJECT_ROOT="$SCRIPT_DIR"
while [ "$PROJECT_ROOT" != "/" ]; do
    if [ -d "$PROJECT_ROOT/research_notebook" ] && [ -d "$PROJECT_ROOT/subprojects" ]; then
        break
    fi
    PROJECT_ROOT=$(dirname "$PROJECT_ROOT")
done

if [ "$PROJECT_ROOT" == "/" ]; then
    PROJECT_ROOT="$SCRIPT_DIR/../.."  # Fallback: assume subprojects/[name]/
fi

# Options (default: all off)
CLEAN_WORK=false
HARDEN_LINKS=false
REMOVE_GITKEEP=false
RECORD_SESSIONS=false
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --clean-work)
            CLEAN_WORK=true
            shift
            ;;
        --harden-links)
            HARDEN_LINKS=true
            shift
            ;;
        --remove-gitkeep)
            REMOVE_GITKEEP=true
            shift
            ;;
        --record-sessions)
            RECORD_SESSIONS=true
            shift
            ;;
        --all)
            CLEAN_WORK=true
            HARDEN_LINKS=true
            REMOVE_GITKEEP=true
            RECORD_SESSIONS=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help|-h)
            head -50 "$0" | grep -E "^#" | sed 's/^# //' | sed 's/^#//'
            exit 0
            ;;
        *)
            echo -e "${RED}ERROR: Unknown option: $1${NC}"
            echo "Use --help to see available options."
            exit 1
            ;;
    esac
done

# Check if any operation was selected
if ! $CLEAN_WORK && ! $HARDEN_LINKS && ! $REMOVE_GITKEEP && ! $RECORD_SESSIONS; then
    echo -e "${YELLOW}No operations selected. Use --help to see options.${NC}"
    echo ""
    echo "Quick reference:"
    echo "  --clean-work       Remove work/ and .nextflow* temp files"
    echo "  --harden-links     Convert softlinks to hard copies"
    echo "  --remove-gitkeep   Remove .gitkeep from non-empty directories"
    echo "  --record-sessions  Extract Claude Code session summaries"
    echo "  --all              All of the above"
    echo "  --dry-run          Preview without making changes"
    exit 0
fi

echo "========================================================================"
echo "GIGANTIC Subproject Cleanup and Recording"
echo "========================================================================"
echo ""
echo "Subproject: $(basename "$SCRIPT_DIR")"
echo "Location: $SCRIPT_DIR"
echo "Project root: $PROJECT_ROOT"
echo ""

if $DRY_RUN; then
    echo -e "${BLUE}DRY RUN MODE - No changes will be made${NC}"
    echo ""
fi

# Track what we'll do
OPERATIONS=()
$RECORD_SESSIONS && OPERATIONS+=("Record Claude Code sessions")
$CLEAN_WORK && OPERATIONS+=("Clean NextFlow work directories")
$HARDEN_LINKS && OPERATIONS+=("Harden softlinks in upload_to_server/")
$REMOVE_GITKEEP && OPERATIONS+=("Remove .gitkeep from non-empty directories")

echo "Operations to perform:"
for op in "${OPERATIONS[@]}"; do
    echo "  - $op"
done
echo ""

################################################################################
# Operation 0: Record Claude Code Sessions (runs FIRST - before cleanup)
################################################################################

record_sessions() {
    echo -e "${YELLOW}=== Recording Claude Code Sessions ===${NC}"
    echo ""

    # Get Claude's encoded project directory
    working_dir=$(cd "$PROJECT_ROOT" && pwd)
    encoded_path=$(echo "$working_dir" | sed 's|/|-|g' | sed 's|_|-|g')
    claude_project_dir="$HOME/.claude/projects/$encoded_path"

    echo "  Working directory: $working_dir"
    echo "  Claude project dir: $claude_project_dir"

    if [ ! -d "$claude_project_dir" ]; then
        echo ""
        echo -e "  ${YELLOW}No Claude Code session data found.${NC}"
        echo "  This means Claude Code has not been used from this directory."
        return
    fi

    # Count JSONL files
    jsonl_count=$(find "$claude_project_dir" -name "*.jsonl" 2>/dev/null | wc -l)
    echo "  Session files found: $jsonl_count"

    if [ "$jsonl_count" -eq 0 ]; then
        echo "  No sessions to extract."
        return
    fi

    # Output locations - log file lives inside sessions folder
    sessions_dir="$PROJECT_ROOT/research_notebook/research_ai/project/sessions"
    log_file="$sessions_dir/SESSION_EXTRACTION_LOG.md"

    echo "  Output directory: $sessions_dir"
    echo ""

    if $DRY_RUN; then
        echo -e "  ${BLUE}[DRY RUN]${NC} Would extract sessions to: $sessions_dir"
        echo -e "  ${BLUE}[DRY RUN]${NC} Would update log: $sessions_dir/SESSION_EXTRACTION_LOG.md"
        echo ""
        echo -e "${GREEN}  Session recording preview complete.${NC}"
        return
    fi

    # Create output directory
    mkdir -p "$sessions_dir"

    # Create log file header if it doesn't exist
    if [ ! -f "$log_file" ]; then
        cat > "$log_file" << 'LOGHEADER'
# Session Extraction Log

This log records all Claude Code session extractions for this GIGANTIC project.
Each extraction overwrites the previous version with complete current state.

| Date | Session ID | Compactions | Output File |
|------|------------|-------------|-------------|
LOGHEADER
    fi

    # Process each JSONL file
    total_compactions=0
    files_created=0

    for jsonl_file in "$claude_project_dir"/*.jsonl; do
        [ -f "$jsonl_file" ] || continue

        session_id=$(basename "$jsonl_file" .jsonl)
        short_id="${session_id:0:8}"

        echo "  Processing: $short_id..."

        # Extract compaction summaries using Python inline
        output_file="$sessions_dir/session_$(date +%Y%B%d | tr '[:upper:]' '[:lower:]')_$short_id.md"

        # Run extraction
        compaction_count=$(python3 << PYEND
import json
import sys
from datetime import datetime

jsonl_path = "$jsonl_file"
output_path = "$output_file"
session_id = "$session_id"
project_path = "$working_dir"

summaries = []
with open(jsonl_path, 'r') as f:
    for line_num, line in enumerate(f, 1):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if data.get('isCompactSummary', False):
                content = data.get('message', {}).get('content', '')
                if 'This session is being continued' in content:
                    summaries.append({
                        'line': line_num,
                        'timestamp': data.get('timestamp', ''),
                        'content': content
                    })
        except:
            pass

if summaries:
    with open(output_path, 'w') as f:
        f.write(f"# Claude Code Session Extraction\\n\\n")
        f.write(f"**Session ID**: {session_id}\\n")
        f.write(f"**Project Path**: {project_path}\\n")
        f.write(f"**Compaction Count**: {len(summaries)}\\n")
        f.write(f"**Extracted**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\\n\\n")
        f.write("---\\n\\n")

        for i, s in enumerate(summaries, 1):
            ts = s['timestamp'][:19] if s['timestamp'] else 'Unknown'
            f.write(f"## Compaction Summary {i}\\n\\n")
            f.write(f"**Timestamp**: {ts}\\n")
            f.write(f"**JSONL Line**: {s['line']}\\n\\n")
            f.write("\\x60\\x60\\x60\\n")
            f.write(s['content'])
            f.write("\\n\\x60\\x60\\x60\\n\\n---\\n\\n")

print(len(summaries))
PYEND
)

        if [ "$compaction_count" -gt 0 ]; then
            echo "    Found $compaction_count compaction(s)"
            echo "    Written to: $(basename "$output_file")"

            # Append to log
            echo "| $(date '+%Y-%m-%d %H:%M') | $short_id... | $compaction_count | $(basename "$output_file") |" >> "$log_file"

            total_compactions=$((total_compactions + compaction_count))
            files_created=$((files_created + 1))
        fi
    done

    echo ""
    echo -e "${GREEN}  Session recording complete.${NC}"
    echo "  Total compactions: $total_compactions"
    echo "  Files created: $files_created"
}

################################################################################
# Operation 1: Clean NextFlow work directories
################################################################################

clean_work_directories() {
    echo -e "${YELLOW}=== Cleaning NextFlow work directories ===${NC}"

    # Find all workflow directories
    workflow_dirs=$(find "$SCRIPT_DIR" -maxdepth 1 -type d -name "workflow*" 2>/dev/null)

    if [ -z "$workflow_dirs" ]; then
        echo "  No workflow directories found."
        return
    fi

    for workflow_dir in $workflow_dirs; do
        workflow_name=$(basename "$workflow_dir")
        echo ""
        echo "  Processing: $workflow_name"

        # Items to clean
        items_to_clean=(
            "$workflow_dir/work"
            "$workflow_dir/.nextflow"
        )

        # Also find .nextflow.log* files
        nextflow_logs=$(find "$workflow_dir" -maxdepth 1 -name ".nextflow.log*" 2>/dev/null)

        for item in "${items_to_clean[@]}"; do
            if [ -e "$item" ]; then
                size=$(du -sh "$item" 2>/dev/null | cut -f1 || echo "?")
                if $DRY_RUN; then
                    echo -e "    ${BLUE}[DRY RUN]${NC} Would remove: $(basename "$item") ($size)"
                else
                    echo "    Removing: $(basename "$item") ($size)"
                    rm -rf "$item"
                fi
            fi
        done

        for log in $nextflow_logs; do
            if [ -f "$log" ]; then
                if $DRY_RUN; then
                    echo -e "    ${BLUE}[DRY RUN]${NC} Would remove: $(basename "$log")"
                else
                    echo "    Removing: $(basename "$log")"
                    rm -f "$log"
                fi
            fi
        done
    done

    echo ""
    echo -e "${GREEN}  Work directory cleanup complete.${NC}"
}

################################################################################
# Operation 2: Harden softlinks in upload_to_server/
################################################################################

harden_softlinks() {
    echo -e "${YELLOW}=== Hardening softlinks in upload_to_server/ ===${NC}"

    upload_dir="$SCRIPT_DIR/upload_to_server"

    if [ ! -d "$upload_dir" ]; then
        echo "  No upload_to_server/ directory found."
        return
    fi

    # Find all symbolic links
    symlinks=$(find "$upload_dir" -type l 2>/dev/null)

    if [ -z "$symlinks" ]; then
        echo "  No softlinks found in upload_to_server/."
        return
    fi

    link_count=0
    for link in $symlinks; do
        # Get the target of the symlink
        target=$(readlink -f "$link" 2>/dev/null)

        if [ -e "$target" ]; then
            link_count=$((link_count + 1))
            rel_path=${link#$upload_dir/}

            if $DRY_RUN; then
                echo -e "    ${BLUE}[DRY RUN]${NC} Would harden: $rel_path"
            else
                echo "    Hardening: $rel_path"
                # Remove symlink and copy the actual file
                rm "$link"
                cp -r "$target" "$link"
            fi
        else
            echo -e "    ${RED}WARNING: Broken symlink: ${link#$upload_dir/}${NC}"
        fi
    done

    echo ""
    if [ $link_count -eq 0 ]; then
        echo "  No valid softlinks to harden."
    else
        echo -e "${GREEN}  Hardened $link_count softlink(s).${NC}"
    fi
}

################################################################################
# Operation 3: Remove .gitkeep from non-empty directories
################################################################################

remove_gitkeep() {
    echo -e "${YELLOW}=== Removing .gitkeep from non-empty directories ===${NC}"

    # Find all .gitkeep files
    gitkeep_files=$(find "$SCRIPT_DIR" -name ".gitkeep" 2>/dev/null)

    if [ -z "$gitkeep_files" ]; then
        echo "  No .gitkeep files found."
        return
    fi

    removed_count=0
    kept_count=0

    for gitkeep in $gitkeep_files; do
        dir=$(dirname "$gitkeep")

        # Count items in directory (excluding .gitkeep itself)
        item_count=$(find "$dir" -maxdepth 1 ! -name ".gitkeep" ! -path "$dir" | wc -l)

        rel_dir=${dir#$SCRIPT_DIR/}

        if [ "$item_count" -gt 0 ]; then
            # Directory has other files, .gitkeep is no longer needed
            removed_count=$((removed_count + 1))
            if $DRY_RUN; then
                echo -e "    ${BLUE}[DRY RUN]${NC} Would remove: $rel_dir/.gitkeep (dir has $item_count item(s))"
            else
                echo "    Removing: $rel_dir/.gitkeep (dir has $item_count item(s))"
                rm "$gitkeep"
            fi
        else
            # Directory is empty except for .gitkeep, keep it
            kept_count=$((kept_count + 1))
            echo "    Keeping: $rel_dir/.gitkeep (dir is empty)"
        fi
    done

    echo ""
    echo -e "${GREEN}  Removed $removed_count .gitkeep file(s), kept $kept_count.${NC}"
}

################################################################################
# Execute selected operations
################################################################################

# Session recording runs FIRST (before any cleanup)
if $RECORD_SESSIONS; then
    record_sessions
    echo ""
fi

if $CLEAN_WORK; then
    if ! $DRY_RUN; then
        echo -e "${RED}WARNING: This will permanently delete NextFlow work directories!${NC}"
        echo "You will not be able to use -resume after this."
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            echo "Skipping work directory cleanup."
            CLEAN_WORK=false
        fi
    fi

    if $CLEAN_WORK; then
        clean_work_directories
    fi
    echo ""
fi

if $HARDEN_LINKS; then
    harden_softlinks
    echo ""
fi

if $REMOVE_GITKEEP; then
    remove_gitkeep
    echo ""
fi

echo "========================================================================"
if $DRY_RUN; then
    echo -e "${BLUE}DRY RUN COMPLETE - No changes were made${NC}"
    echo "Remove --dry-run to execute these operations."
else
    echo -e "${GREEN}CLEANUP AND RECORDING COMPLETE${NC}"
fi
echo "========================================================================"
