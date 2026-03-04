#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 04 | Purpose: Clean NextFlow artifacts and record sessions
# Human: Eric Edsinger

################################################################################
# annotations_X_ocl - Clean and Record Subproject
################################################################################
#
# USAGE:
#   bash RUN-clean_and_record_subproject.sh [OPTIONS]
#
# OPTIONS:
#   --clean              Remove NextFlow work/, .nextflow/, .nextflow.log* files
#   --record-sessions    Extract Claude Code sessions to research_notebook
#   --all                Both --clean and --record-sessions
#   --dry-run            Show what would be done without doing it
#
################################################################################

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

CLEAN=false
RECORD=false
DRY_RUN=false

for arg in "$@"; do
    case $arg in
        --clean) CLEAN=true ;;
        --record-sessions) RECORD=true ;;
        --all) CLEAN=true; RECORD=true ;;
        --dry-run) DRY_RUN=true ;;
        *) echo "Unknown option: $arg"; exit 1 ;;
    esac
done

if ! $CLEAN && ! $RECORD; then
    echo "Usage: bash RUN-clean_and_record_subproject.sh [--clean|--record-sessions|--all] [--dry-run]"
    exit 0
fi

# Clean NextFlow artifacts from all workflow directories
if $CLEAN; then
    echo "Cleaning NextFlow artifacts..."
    for workflow_dir in BLOCK_*/workflow-*/; do
        if [ -d "$workflow_dir" ]; then
            for artifact in work .nextflow .nextflow.log*; do
                target="${workflow_dir}${artifact}"
                if [ -e "$target" ] || ls ${target} 2>/dev/null 1>&2; then
                    if $DRY_RUN; then
                        echo "  [DRY RUN] Would remove: $target"
                    else
                        rm -rf ${target}
                        echo "  Removed: $target"
                    fi
                fi
            done
        fi
    done
    echo "Done."
fi

# Record Claude Code sessions
if $RECORD; then
    echo "Recording Claude Code sessions..."
    # Delegate to project-level recording script
    PROJECT_ROOT="${SCRIPT_DIR}/../.."
    if [ -f "${PROJECT_ROOT}/RUN-record_project.sh" ]; then
        if $DRY_RUN; then
            echo "  [DRY RUN] Would run: bash ${PROJECT_ROOT}/RUN-record_project.sh --subproject annotations_X_ocl"
        else
            bash "${PROJECT_ROOT}/RUN-record_project.sh" --subproject annotations_X_ocl
        fi
    else
        echo "  WARNING: Project-level recording script not found"
    fi
    echo "Done."
fi
