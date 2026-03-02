#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Clean temporary files and record sessions for gene_sizes
# Human: Eric Edsinger

################################################################################
# GIGANTIC gene_sizes - Clean and Record Subproject
################################################################################
#
# PURPOSE:
# Remove temporary Nextflow files (work/, .nextflow/, .nextflow.log*)
# and optionally extract Claude Code session compactions for the
# research notebook.
#
# USAGE:
#   bash RUN-clean_and_record_subproject.sh [OPTIONS]
#
# OPTIONS:
#   --clean             Remove temporary Nextflow files
#   --record-sessions   Extract Claude Code session compactions
#   --all               Both clean and record
#   --dry-run           Show what would be done without doing it
#
################################################################################

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SUBPROJECT_DIR="${SCRIPT_DIR}"

# Parse arguments
CLEAN=false
RECORD=false
DRY_RUN=false

for arg in "$@"; do
    case $arg in
        --clean) CLEAN=true ;;
        --record-sessions) RECORD=true ;;
        --all) CLEAN=true; RECORD=true ;;
        --dry-run) DRY_RUN=true ;;
        *)
            echo "Unknown option: $arg"
            echo "Usage: bash RUN-clean_and_record_subproject.sh [--clean] [--record-sessions] [--all] [--dry-run]"
            exit 1
            ;;
    esac
done

if [ "$CLEAN" = false ] && [ "$RECORD" = false ]; then
    echo "No action specified. Use --clean, --record-sessions, or --all"
    echo "Usage: bash RUN-clean_and_record_subproject.sh [--clean] [--record-sessions] [--all] [--dry-run]"
    exit 0
fi

echo "========================================================================"
echo "GIGANTIC gene_sizes - Clean and Record"
echo "========================================================================"
echo ""

# ============================================================================
# Clean Nextflow temporary files
# ============================================================================

if [ "$CLEAN" = true ]; then
    echo "Cleaning temporary Nextflow files..."
    echo ""

    # Find all workflow directories
    for workflow_dir in "${SUBPROJECT_DIR}"/workflow-*/; do
        if [ -d "$workflow_dir" ]; then
            workflow_name=$(basename "$workflow_dir")
            echo "  Workflow: ${workflow_name}"

            for target in "work" ".nextflow" ".nextflow.log"*; do
                target_path="${workflow_dir}${target}"
                if [ -e "$target_path" ] || [ -d "$target_path" ]; then
                    if [ "$DRY_RUN" = true ]; then
                        echo "    [DRY RUN] Would remove: ${target}"
                    else
                        rm -rf "$target_path"
                        echo "    Removed: ${target}"
                    fi
                fi
            done
        fi
    done

    echo ""
    echo "  Clean complete."
    echo ""
fi

# ============================================================================
# Record Claude Code sessions
# ============================================================================

if [ "$RECORD" = true ]; then
    echo "Recording Claude Code sessions..."
    echo ""

    # Try to find the session extraction script
    EXTRACT_SCRIPT=""
    # Check project root
    if [ -f "${SUBPROJECT_DIR}/../../../RUN-record_project.sh" ]; then
        EXTRACT_SCRIPT="${SUBPROJECT_DIR}/../../../RUN-record_project.sh"
    elif [ -f "${SUBPROJECT_DIR}/../../../../RUN-record_project.sh" ]; then
        EXTRACT_SCRIPT="${SUBPROJECT_DIR}/../../../../RUN-record_project.sh"
    fi

    if [ -n "$EXTRACT_SCRIPT" ]; then
        if [ "$DRY_RUN" = true ]; then
            echo "  [DRY RUN] Would run: bash ${EXTRACT_SCRIPT}"
        else
            echo "  Running session extraction..."
            bash "$EXTRACT_SCRIPT" || echo "  WARNING: Session extraction returned non-zero exit code"
        fi
    else
        echo "  WARNING: Could not find RUN-record_project.sh"
        echo "  Session recording skipped."
    fi

    echo ""
fi

echo "========================================================================"
echo "Done."
echo "========================================================================"
