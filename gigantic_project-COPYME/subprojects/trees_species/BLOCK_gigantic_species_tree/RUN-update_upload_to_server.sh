#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 April 10 | Purpose: Copy key outputs to upload_to_server for gigantic_species_tree BLOCK
# Human: Eric Edsinger

set -e

echo "Updating upload_to_server for gigantic_species_tree..."

mkdir -p upload_to_server

if [ -d "../output_to_input/BLOCK_gigantic_species_tree" ]; then
    cp -r ../output_to_input/BLOCK_gigantic_species_tree/* upload_to_server/ 2>/dev/null || true
    echo "  Copied output_to_input/BLOCK_gigantic_species_tree/ contents to upload_to_server/"
else
    echo "  No output_to_input/BLOCK_gigantic_species_tree/ directory found. Run the pipeline first."
fi

echo "Done."
