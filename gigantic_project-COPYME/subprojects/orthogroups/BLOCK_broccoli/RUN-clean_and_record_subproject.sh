#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: Clean NextFlow artifacts and record sessions for Broccoli project
# Human: Eric Edsinger

set -e

echo "Cleaning Broccoli project..."

for workflow_dir in workflow-COPYME-*/; do
    if [ -d "${workflow_dir}work" ]; then
        echo "  Removing: ${workflow_dir}work/"
        rm -rf "${workflow_dir}work"
    fi
    if [ -d "${workflow_dir}.nextflow" ]; then
        echo "  Removing: ${workflow_dir}.nextflow/"
        rm -rf "${workflow_dir}.nextflow"
    fi
    rm -f "${workflow_dir}".nextflow.log*
done

echo "Broccoli project cleaned."
