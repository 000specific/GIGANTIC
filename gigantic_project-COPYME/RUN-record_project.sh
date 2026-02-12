#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 12 | Purpose: Record Claude Code sessions for project and all subprojects
# Human: Eric Edsinger

################################################################################
# GIGANTIC Project Session Recording
################################################################################
#
# PURPOSE:
# Extract Claude Code context compaction summaries from ~/.claude/projects/
# for the project root AND each subproject directory, saving them as
# human-readable markdown in research_notebook/research_ai/
#
# This provides complete research provenance - a record of all AI-assisted
# work across the entire project.
#
# USAGE:
#   bash RUN-record_project.sh [OPTIONS]
#
# OPTIONS:
#   --project-only     Only record project-level sessions (skip subprojects)
#   --dry-run          Show what would be recorded without making changes
#   --help             Show this help message
#
# OUTPUT:
#   research_notebook/research_ai/project/sessions/           (project-level)
#   research_notebook/research_ai/subproject-*/sessions/      (per-subproject)
#   research_notebook/research_ai/project/SESSION_EXTRACTION_LOG.md
#
# NOTES:
#   - Run from GIGANTIC project root directory
#   - Overwrites previous extractions with complete current state
#   - Safe to run multiple times
#   - Gracefully handles subprojects with no session data
#   - Requires Python 3
#
################################################################################

# Don't use set -e so we can handle missing sessions gracefully
# set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory (project root)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Options
PROJECT_ONLY=false
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --project-only)
            PROJECT_ONLY=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
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
echo "GIGANTIC Project Session Recording"
echo "========================================================================"
echo ""

if $DRY_RUN; then
    echo -e "${BLUE}DRY RUN MODE - No changes will be made${NC}"
    echo ""
fi

# Verify we're in a GIGANTIC project
if [ ! -d "${SCRIPT_DIR}/research_notebook" ]; then
    echo -e "${RED}ERROR: research_notebook/ directory not found!${NC}"
    echo "This script must be run from a GIGANTIC project root."
    exit 1
fi

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}python3 not found directly, trying module load...${NC}"
    module load python 2>/dev/null || true

    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}ERROR: Python 3 not available!${NC}"
        echo "Please install Python 3 or load the appropriate module."
        exit 1
    fi
fi

echo "Project root: $SCRIPT_DIR"
echo "Python: $(which python3)"
echo ""

################################################################################
# Function: Extract sessions for a given working directory
################################################################################

extract_sessions() {
    local working_dir="$1"
    local output_base="$2"
    local label="$3"

    echo -e "${YELLOW}--- $label ---${NC}"
    echo "  Working directory: $working_dir"

    # Get Claude's encoded project directory
    encoded_path=$(echo "$working_dir" | sed 's|/|-|g' | sed 's|_|-|g')
    claude_project_dir="$HOME/.claude/projects/$encoded_path"

    echo "  Claude project dir: $claude_project_dir"

    if [ ! -d "$claude_project_dir" ]; then
        echo -e "  ${YELLOW}No session data found. Skipping.${NC}"
        echo ""
        return 0
    fi

    # Count JSONL files
    jsonl_count=$(find "$claude_project_dir" -name "*.jsonl" 2>/dev/null | wc -l)
    echo "  Session files found: $jsonl_count"

    if [ "$jsonl_count" -eq 0 ]; then
        echo "  No sessions to extract."
        echo ""
        return 0
    fi

    # Output locations - log file lives inside sessions folder
    sessions_dir="$output_base/sessions"
    log_file="$sessions_dir/SESSION_EXTRACTION_LOG.md"

    echo "  Output directory: $sessions_dir"
    echo "  Log file: $log_file"

    if $DRY_RUN; then
        echo -e "  ${BLUE}[DRY RUN]${NC} Would extract $jsonl_count session file(s)"
        echo ""
        return 0
    fi

    # Create output directory
    mkdir -p "$sessions_dir"

    # Create log file header if it doesn't exist
    if [ ! -f "$log_file" ]; then
        mkdir -p "$(dirname "$log_file")"
        cat > "$log_file" << 'LOGHEADER'
# Session Extraction Log

This log records all Claude Code session extractions for this GIGANTIC project.
Each extraction overwrites the previous version with complete current state.

| Date | Location | Session ID | Compactions | Output File |
|------|----------|------------|-------------|-------------|
LOGHEADER
    fi

    # Process each JSONL file
    local total_compactions=0
    local files_created=0

    for jsonl_file in "$claude_project_dir"/*.jsonl; do
        [ -f "$jsonl_file" ] || continue

        session_id=$(basename "$jsonl_file" .jsonl)
        short_id="${session_id:0:8}"

        # Run extraction using Python
        output_file="$sessions_dir/session_$(date +%Y%B%d | tr '[:upper:]' '[:lower:]')_$short_id.md"

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
            echo "    Session $short_id: $compaction_count compaction(s)"

            # Append to log
            echo "| $(date '+%Y-%m-%d %H:%M') | $label | $short_id... | $compaction_count | $(basename "$output_file") |" >> "$log_file"

            total_compactions=$((total_compactions + compaction_count))
            files_created=$((files_created + 1))
        fi
    done

    if [ "$files_created" -gt 0 ]; then
        echo -e "  ${GREEN}Extracted $total_compactions compaction(s) to $files_created file(s)${NC}"
    else
        echo "  No compactions found in session files."
    fi
    echo ""
}

################################################################################
# Main: Record project-level sessions
################################################################################

echo "Recording project-level sessions..."
echo ""

extract_sessions "$SCRIPT_DIR" "$SCRIPT_DIR/research_notebook/research_ai/project" "project"

################################################################################
# Record subproject sessions (unless --project-only)
################################################################################

if ! $PROJECT_ONLY; then
    echo "Recording subproject sessions..."
    echo ""

    # Find all subprojects
    if [ -d "$SCRIPT_DIR/subprojects" ]; then
        for subproject_dir in "$SCRIPT_DIR/subprojects"/*; do
            if [ -d "$subproject_dir" ]; then
                subproject_name=$(basename "$subproject_dir")

                # Skip directories starting with . or _
                if [[ "$subproject_name" == .* ]] || [[ "$subproject_name" == _* ]]; then
                    continue
                fi

                # Output to subproject-specific research_ai directory
                output_base="$SCRIPT_DIR/research_notebook/research_ai/subproject-$subproject_name"

                extract_sessions "$subproject_dir" "$output_base" "subproject-$subproject_name"
            fi
        done
    else
        echo "  No subprojects/ directory found."
        echo ""
    fi

    # Also check for workflow directories within subprojects
    echo "Recording workflow-level sessions..."
    echo ""

    if [ -d "$SCRIPT_DIR/subprojects" ]; then
        for subproject_dir in "$SCRIPT_DIR/subprojects"/*; do
            if [ -d "$subproject_dir" ]; then
                subproject_name=$(basename "$subproject_dir")

                # Skip directories starting with . or _
                if [[ "$subproject_name" == .* ]] || [[ "$subproject_name" == _* ]]; then
                    continue
                fi

                # Find workflow directories
                for workflow_dir in "$subproject_dir"/workflow*; do
                    if [ -d "$workflow_dir" ]; then
                        workflow_name=$(basename "$workflow_dir")

                        # Output to subproject directory (workflows share subproject sessions folder)
                        output_base="$SCRIPT_DIR/research_notebook/research_ai/subproject-$subproject_name"

                        extract_sessions "$workflow_dir" "$output_base" "$subproject_name/$workflow_name"
                    fi
                done
            fi
        done
    fi
fi

################################################################################
# Summary
################################################################################

echo "========================================================================"
if $DRY_RUN; then
    echo -e "${BLUE}DRY RUN COMPLETE - No changes were made${NC}"
    echo "Remove --dry-run to execute recording."
else
    echo -e "${GREEN}SESSION RECORDING COMPLETE${NC}"
    echo ""
    echo "Each location has its own SESSION_EXTRACTION_LOG.md"
    echo ""
    echo "View project sessions and log:"
    echo "  ls research_notebook/research_ai/project/sessions/"
    echo "  cat research_notebook/research_ai/project/sessions/SESSION_EXTRACTION_LOG.md"
    echo ""
    echo "View subproject sessions and logs:"
    echo "  ls research_notebook/research_ai/subproject-*/sessions/"
    echo "  cat research_notebook/research_ai/subproject-*/sessions/SESSION_EXTRACTION_LOG.md"
fi
echo "========================================================================"
