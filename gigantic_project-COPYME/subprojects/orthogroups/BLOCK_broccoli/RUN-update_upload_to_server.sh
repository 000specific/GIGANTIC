#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 February 28 | Purpose: Copy key outputs to upload_to_server for Broccoli project
# Human: Eric Edsinger

set -e

echo "Updating upload_to_server for Broccoli..."

mkdir -p upload_to_server

if [ -d "../output_to_input/BLOCK_broccoli" ]; then
    cp -r ../output_to_input/BLOCK_broccoli/* upload_to_server/ 2>/dev/null || true
    echo "  Copied output_to_input/BLOCK_broccoli/ contents to upload_to_server/"
else
    echo "  No output_to_input/BLOCK_broccoli/ directory found. Run the pipeline first."
fi

echo "Done."
