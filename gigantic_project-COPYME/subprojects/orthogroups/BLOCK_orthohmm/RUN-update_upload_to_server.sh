#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: Copy key outputs to upload_to_server for OrthoHMM project
# Human: Eric Edsinger

set -e

echo "Updating upload_to_server for OrthoHMM..."

mkdir -p upload_to_server

if [ -d "../output_to_input/BLOCK_orthohmm" ]; then
    cp -r ../output_to_input/BLOCK_orthohmm/* upload_to_server/ 2>/dev/null || true
    echo "  Copied output_to_input/BLOCK_orthohmm/ contents to upload_to_server/"
else
    echo "  No output_to_input/BLOCK_orthohmm/ directory found. Run the pipeline first."
fi

echo "Done."
