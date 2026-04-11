#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 April 10 | Purpose: Copy key outputs to upload_to_server for permutations_and_features BLOCK
# Human: Eric Edsinger

set -e

echo "Updating upload_to_server for permutations_and_features..."

mkdir -p upload_to_server

if [ -d "../output_to_input/BLOCK_permutations_and_features" ]; then
    cp -r ../output_to_input/BLOCK_permutations_and_features/* upload_to_server/ 2>/dev/null || true
    echo "  Copied output_to_input/BLOCK_permutations_and_features/ contents to upload_to_server/"
else
    echo "  No output_to_input/BLOCK_permutations_and_features/ directory found. Run the pipeline first."
fi

echo "Done."
