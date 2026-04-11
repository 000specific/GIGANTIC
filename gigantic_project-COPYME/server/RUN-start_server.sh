#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 April 02 | Purpose: Start GIGANTIC data server locally
# Human: Eric Edsinger

################################################################################
# GIGANTIC Data Server - Local Start
################################################################################
#
# PURPOSE:
# Start the GIGANTIC data server for local access.
# Serves files directly from subproject upload_to_server/ directories.
# Reads configuration from START_HERE-server_config.yaml.
#
# USAGE:
#   bash RUN-start_server.sh [OPTIONS]
#
# OPTIONS:
#   --port PORT   Override port from config
#   --help        Show this help message
#
# PREREQUISITES:
# 1. Python 3 available in PATH
# 2. Subprojects have run their RUN-update_upload_to_server.sh
#    to populate upload_to_server/ with symlinks
#
################################################################################

set -e

# Script directory (server/)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Options
PORT_OVERRIDE=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT_OVERRIDE="--port $2"
            shift 2
            ;;
        --help|-h)
            head -25 "$0" | grep -E "^#" | sed 's/^# //' | sed 's/^#//'
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option: $1"
            echo "Use --help to see available options."
            exit 1
            ;;
    esac
done

echo "========================================================================"
echo "GIGANTIC Data Server - Starting"
echo "========================================================================"
echo ""

# Start the server
exec python3 "${SCRIPT_DIR}/ai/gigantic_server.py" \
    --config "${SCRIPT_DIR}/START_HERE-server_config.yaml" \
    --subprojects-dir "${SCRIPT_DIR}/../subprojects" \
    ${PORT_OVERRIDE}
