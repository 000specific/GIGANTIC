#!/bin/bash
# AI: Claude Code | Opus 4.7 (1M context) | 2026 May 26 | Purpose: Unified driver for GIGANTIC data server — runs locally or self-submits to SLURM based on execution_mode in START_HERE-server_config.yaml
# Human: Eric Edsinger

################################################################################
# GIGANTIC Data Server — Unified Driver
################################################################################
#
# Per gigantic_conventions.md §29: a single RUN-*.sh is the canonical entry
# point. It self-submits to SLURM when execution_mode==slurm in the YAML
# config, runs locally otherwise. There is no separate .sbatch file.
#
# USAGE:
#   bash RUN-start_server.sh [OPTIONS]
#
# OPTIONS:
#   --port PORT      Override port from config (local mode only)
#   --execution MODE Override execution_mode ('local' or 'slurm')
#   --help           Show this help message
#
# CONFIG:
#   All settings come from START_HERE-server_config.yaml, including:
#   - execution_mode: local | slurm
#   - port, project_name, subproject_order, etc.
#   - slurm.* settings (account, qos, partition, time_hours, memory_gb, cpus)
#
################################################################################

set -e

# ---------------------------------------------------------------------------
# Script location + arg parsing
# ---------------------------------------------------------------------------

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CONFIG_PATH="${SCRIPT_DIR}/START_HERE-server_config.yaml"

PORT_OVERRIDE=""
EXECUTION_OVERRIDE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT_OVERRIDE="--port $2"
            shift 2
            ;;
        --execution)
            EXECUTION_OVERRIDE="$2"
            shift 2
            ;;
        --help|-h)
            head -32 "$0" | grep -E "^#" | sed 's/^# //' | sed 's/^#//'
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option: $1"
            echo "Use --help to see available options."
            exit 1
            ;;
    esac
done

if [[ ! -f "${CONFIG_PATH}" ]]; then
    echo "ERROR: Config file not found: ${CONFIG_PATH}"
    exit 1
fi

# ---------------------------------------------------------------------------
# Read execution_mode and slurm settings from YAML
# (Uses Python because the server's built-in YAML parser is shipped with
# gigantic_server.py; using Python directly here keeps this driver
# self-contained and doesn't require PyYAML if not already installed.)
# ---------------------------------------------------------------------------

read_yaml_value() {
    python3 - "$CONFIG_PATH" "$1" "$2" <<'PYTHON'
import sys
config_path, top_key, sub_key = sys.argv[ 1 ], sys.argv[ 2 ], sys.argv[ 3 ]
current_top = None
with open( config_path ) as f:
    for raw in f:
        line = raw.rstrip( '\n' )
        stripped = line.strip()
        if not stripped or stripped.startswith( '#' ):
            continue
        # top-level scalar (no leading spaces)
        if not line.startswith( ' ' ):
            if ':' in stripped:
                key, _, value = stripped.partition( ':' )
                key = key.strip()
                value = value.strip().strip( '"' ).strip( "'" )
                if sub_key == '' and key == top_key:
                    print( value ); sys.exit( 0 )
                current_top = key
            continue
        # nested (indented) scalar — value belongs to current_top
        if current_top == top_key and ':' in stripped:
            key, _, value = stripped.partition( ':' )
            key = key.strip()
            value = value.strip().strip( '"' ).strip( "'" )
            if key == sub_key:
                print( value ); sys.exit( 0 )
print( '' )
PYTHON
}

EXECUTION_MODE="${EXECUTION_OVERRIDE:-$(read_yaml_value execution_mode '')}"
EXECUTION_MODE="${EXECUTION_MODE:-local}"

# ---------------------------------------------------------------------------
# SLURM mode: write an sbatch wrapper and submit it
# ---------------------------------------------------------------------------

if [[ "${EXECUTION_MODE}" == "slurm" ]]; then
    SLURM_ACCOUNT="$( read_yaml_value slurm account )"
    SLURM_QOS="$( read_yaml_value slurm qos )"
    SLURM_PARTITION="$( read_yaml_value slurm partition )"
    SLURM_TIME_HOURS="$( read_yaml_value slurm time_hours )"
    SLURM_MEMORY_GB="$( read_yaml_value slurm memory_gb )"
    SLURM_CPUS="$( read_yaml_value slurm cpus )"

    : "${SLURM_PARTITION:=hpg-default}"
    : "${SLURM_TIME_HOURS:=720}"
    : "${SLURM_MEMORY_GB:=4}"
    : "${SLURM_CPUS:=1}"

    if [[ -z "${SLURM_ACCOUNT}" || "${SLURM_ACCOUNT}" == "your_account" ]]; then
        echo "ERROR: slurm.account is unset or still the placeholder 'your_account'."
        echo "       Edit START_HERE-server_config.yaml → slurm.account and slurm.qos."
        exit 1
    fi

    mkdir -p "${SCRIPT_DIR}/logs"
    SBATCH_WRAPPER="${SCRIPT_DIR}/logs/.run_server_$$.sbatch"
    SLURM_TIME_HMS="${SLURM_TIME_HOURS}:00:00"

    cat > "${SBATCH_WRAPPER}" <<SBATCH
#!/bin/bash
#SBATCH --job-name=gigantic_server
#SBATCH --partition=${SLURM_PARTITION}
#SBATCH --time=${SLURM_TIME_HMS}
#SBATCH --mem=${SLURM_MEMORY_GB}gb
#SBATCH --cpus-per-task=${SLURM_CPUS}
#SBATCH --account=${SLURM_ACCOUNT}
#SBATCH --qos=${SLURM_QOS}
#SBATCH --output=${SCRIPT_DIR}/logs/slurm_server_%j.log

echo "========================================================================"
echo "GIGANTIC Data Server — SLURM Job"
echo "========================================================================"
echo "Job ID:    \${SLURM_JOB_ID}"
echo "Node:      \$(hostname)"
echo "Started:   \$(date)"
echo ""

exec python3 "${SCRIPT_DIR}/ai/gigantic_server.py" \\
    --config "${CONFIG_PATH}" \\
    --subprojects-dir "${SCRIPT_DIR}/../subprojects"
SBATCH

    echo "========================================================================"
    echo "GIGANTIC Data Server — Submitting to SLURM"
    echo "========================================================================"
    echo "Account:   ${SLURM_ACCOUNT}"
    echo "QOS:       ${SLURM_QOS}"
    echo "Partition: ${SLURM_PARTITION}"
    echo "Walltime:  ${SLURM_TIME_HMS}"
    echo "Memory:    ${SLURM_MEMORY_GB}gb"
    echo "CPUs:      ${SLURM_CPUS}"
    echo "Wrapper:   ${SBATCH_WRAPPER}"
    echo ""

    sbatch "${SBATCH_WRAPPER}"
    exit 0
fi

# ---------------------------------------------------------------------------
# Local mode: run the server directly in the foreground
# ---------------------------------------------------------------------------

echo "========================================================================"
echo "GIGANTIC Data Server — Local Start"
echo "========================================================================"
echo ""

exec python3 "${SCRIPT_DIR}/ai/gigantic_server.py" \
    --config "${CONFIG_PATH}" \
    --subprojects-dir "${SCRIPT_DIR}/../subprojects" \
    ${PORT_OVERRIDE}
