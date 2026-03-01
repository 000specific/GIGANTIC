#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: Copy key outputs to upload_to_server for OrthoFinder project
# Human: Eric Edsinger

set -e

echo "Updating upload_to_server for OrthoFinder..."

mkdir -p upload_to_server

if [ -d "output_to_input" ]; then
    cp -r output_to_input/* upload_to_server/ 2>/dev/null || true
    echo "  Copied output_to_input contents to upload_to_server/"
else
    echo "  No output_to_input/ directory found. Run the pipeline first."
fi

echo "Done."
