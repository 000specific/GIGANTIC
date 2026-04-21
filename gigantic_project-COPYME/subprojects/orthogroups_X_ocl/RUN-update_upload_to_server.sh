#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 April 20 | Purpose: Thin wrapper around shared update_upload_to_server.py
# Human: Eric Edsinger

################################################################################
# GIGANTIC orthogroups_X_ocl - Upload to Server Builder
################################################################################
#
# PURPOSE:
# Build this subproject's upload_to_server/ tree from per-workflow manifests.
#
# For each workflow-RUN_*/upload_manifest.tsv discovered under this subproject
# (BLOCK_*/workflow-RUN_* dirs), the shared helper:
#   - reads included files
#   - symlinks them into upload_to_server/<BLOCK_*>/<workflow-RUN_*>/<...>/
#     preserving structure_NNN/ and N-output/ subdirs
#   - writes sidecar .section_metadata.tsv for the server UI
#
# The heavy lifting lives in the shared helper:
#   gigantic_project-COPYME/server/ai/update_upload_to_server.py
#
# USAGE:
#   bash RUN-update_upload_to_server.sh [OPTIONS]
#
# OPTIONS:
#   --dry-run     Report actions without writing
#   --clean       Remove broken symlinks + empty dirs (implicit if not --dry-run)
#   --strict      Treat manifest warnings as errors (good for CI)
#
################################################################################

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
HELPER="${SCRIPT_DIR}/../../server/ai/update_upload_to_server.py"

if [ ! -f "${HELPER}" ]; then
    echo "ERROR: shared helper not found: ${HELPER}"
    exit 1
fi

python3 "${HELPER}" --subproject-dir "${SCRIPT_DIR}" "$@"
