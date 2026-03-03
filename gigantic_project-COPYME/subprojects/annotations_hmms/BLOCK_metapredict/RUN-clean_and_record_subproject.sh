#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 03 | Purpose: Clean NextFlow artifacts for MetaPredict project
# Human: Eric Edsinger

set -e

echo "Cleaning MetaPredict project..."

# Clean NextFlow work directories and logs
for workflow_dir in workflow-COPYME-*/ workflow-RUN_*/; do
    [ -d "${workflow_dir}" ] || continue
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

echo "MetaPredict project cleaned."
