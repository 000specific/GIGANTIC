#!/bin/bash
# AI: Claude Code | Opus 4.7 (1M context) | 2026 May 26 | Purpose: Thin wrapper around shared update_upload_to_server.py — publishes genomesDB outputs to the project's data server
# Human: Eric Edsinger

################################################################################
# GIGANTIC genomesDB — Upload to Server Builder
################################################################################
#
# Per gigantic_conventions.md §38: each subproject has ONE subproject-level
# RUN-update_upload_to_server.sh that invokes the shared helper at
# server/ai/update_upload_to_server.py.
#
# Behavior:
#   For each workflow-RUN_*/upload_manifest.tsv discovered under this
#   subproject:
#     - reads included files
#     - symlinks them into upload_to_server/<nested-path>/
#     - writes sidecar .section_metadata.tsv for the server UI
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
    echo "       Expected at gigantic_project-COPYME/server/ai/update_upload_to_server.py"
    exit 1
fi

python3 "${HELPER}" --subproject-dir "${SCRIPT_DIR}" "$@"
