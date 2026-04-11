#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 April 10 | Purpose: Clean NextFlow artifacts from COPYME templates for gigantic_species_tree BLOCK
# Human: Eric Edsinger

set -e

echo "Cleaning gigantic_species_tree BLOCK..."

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

echo "gigantic_species_tree BLOCK cleaned."
