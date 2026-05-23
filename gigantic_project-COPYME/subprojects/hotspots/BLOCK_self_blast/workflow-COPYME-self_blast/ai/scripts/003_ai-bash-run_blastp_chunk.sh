#!/bin/bash
# AI: Claude Code | Opus 4.7 | 2026 May 04 | Purpose: Run blastp for one query chunk against one species' self-DB
# Human: Eric Edsinger
#
# GIGANTIC hotspots BLOCK_self_blast - Script 003: Run blastp Chunk
#
# Invoked by NextFlow's run_blastp_chunk process. One invocation = one
# fan-out task = one query chunk vs one species' pre-built blastp DB.
#
# Usage:
#   bash 003_ai-bash-run_blastp_chunk.sh \
#       --query-chunk PATH \
#       --blast-db-path PATH \
#       --output-report PATH \
#       --evalue 1e-3 \
#       --outfmt 6 \
#       --num-threads 5
#
# Arguments are required (no defaults). Fail-fast if any are missing or any
# input file is unreadable.

set -euo pipefail

QUERY_CHUNK=""
BLAST_DB_PATH=""
OUTPUT_REPORT=""
EVALUE=""
OUTFMT=""
NUM_THREADS=""

while [ $# -gt 0 ]; do
    case "$1" in
        --query-chunk)    QUERY_CHUNK="$2"; shift 2 ;;
        --blast-db-path)  BLAST_DB_PATH="$2"; shift 2 ;;
        --output-report)  OUTPUT_REPORT="$2"; shift 2 ;;
        --evalue)         EVALUE="$2"; shift 2 ;;
        --outfmt)         OUTFMT="$2"; shift 2 ;;
        --num-threads)    NUM_THREADS="$2"; shift 2 ;;
        *)
            echo "ERROR: Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

if [ -z "${QUERY_CHUNK}" ] || [ -z "${BLAST_DB_PATH}" ] || [ -z "${OUTPUT_REPORT}" ] \
   || [ -z "${EVALUE}" ] || [ -z "${OUTFMT}" ] || [ -z "${NUM_THREADS}" ]; then
    echo "ERROR: Missing required argument. All of --query-chunk, --blast-db-path, --output-report, --evalue, --outfmt, --num-threads are required." >&2
    exit 1
fi

if [ ! -f "${QUERY_CHUNK}" ]; then
    echo "ERROR: Query chunk file not found: ${QUERY_CHUNK}" >&2
    exit 1
fi

# blastp DBs are referenced by their stem; the .pdb / .pin / .psq sidecar files must exist.
if [ ! -f "${BLAST_DB_PATH}.pdb" ] && [ ! -f "${BLAST_DB_PATH}.pin" ]; then
    echo "ERROR: BLAST DB stem has no .pdb or .pin file: ${BLAST_DB_PATH}" >&2
    echo "       Expected pre-built blastp DB at: ${BLAST_DB_PATH}.{pdb,phr,pin,pjs,pot,psq,ptf,pto}" >&2
    exit 1
fi

if ! command -v blastp >/dev/null 2>&1; then
    echo "ERROR: blastp not found in PATH. Activate the conda env (ai_gigantic_hotspots) first." >&2
    exit 1
fi

echo "Running blastp: query=${QUERY_CHUNK}  db=${BLAST_DB_PATH}  evalue=${EVALUE}  threads=${NUM_THREADS}"

blastp \
    -query "${QUERY_CHUNK}" \
    -db "${BLAST_DB_PATH}" \
    -outfmt "${OUTFMT}" \
    -evalue "${EVALUE}" \
    -num_threads "${NUM_THREADS}" \
    -out "${OUTPUT_REPORT}"

# Sanity check: the report file must exist (blastp produces an empty file
# when there are no hits, which is a valid result; absence of the file is
# the failure mode we guard against).
if [ ! -f "${OUTPUT_REPORT}" ]; then
    echo "ERROR: blastp completed but output report is missing: ${OUTPUT_REPORT}" >&2
    exit 1
fi

LINE_COUNT=$( wc -l < "${OUTPUT_REPORT}" )
echo "Done. Report: ${OUTPUT_REPORT} (${LINE_COUNT} hit lines)"
