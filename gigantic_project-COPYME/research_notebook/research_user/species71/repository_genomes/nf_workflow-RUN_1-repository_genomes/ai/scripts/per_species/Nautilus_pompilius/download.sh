#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Download Nautilus pompilius data from NGDC Genome Warehouse
# Human: Eric Edsinger

set -euo pipefail

OUTPUT_DIRECTORY="$1"
REPOSITORY_URL="$2"
GENOME_URL="${3:-}"
ANNOTATION_URL="${4:-}"
PROTEIN_URL="${5:-}"

mkdir -p "${OUTPUT_DIRECTORY}"
LOG_FILE="${OUTPUT_DIRECTORY}/download_log.txt"

echo "  Downloading Nautilus_pompilius..."

{
  echo "Species: Nautilus_pompilius"
  echo "Repository: ${REPOSITORY_URL}"
  echo "Date: $(date)"
  echo ""
} > "${LOG_FILE}"

# Genome: GWHBECW00000000.genome.fasta.gz (gzipped)
if [ -n "${GENOME_URL}" ]; then
  echo "  Downloading genome (gzipped)..."
  wget -q --no-check-certificate -O "${OUTPUT_DIRECTORY}/genome.fasta.gz" "${GENOME_URL}"
  echo "  Decompressing genome..."
  gunzip -f "${OUTPUT_DIRECTORY}/genome.fasta.gz"
  echo "Genome URL: ${GENOME_URL}" >> "${LOG_FILE}"
else
  echo "  No genome URL provided"
  echo "Genome: not available" >> "${LOG_FILE}"
fi

# Annotation: GWHBECW00000000.gff.gz (gzipped)
if [ -n "${ANNOTATION_URL}" ]; then
  echo "  Downloading annotation (gzipped)..."
  wget -q --no-check-certificate -O "${OUTPUT_DIRECTORY}/annotation.gff3.gz" "${ANNOTATION_URL}"
  echo "  Decompressing annotation..."
  gunzip -f "${OUTPUT_DIRECTORY}/annotation.gff3.gz"
  echo "Annotation URL: ${ANNOTATION_URL}" >> "${LOG_FILE}"
else
  echo "  No annotation URL provided"
  echo "Annotation: not available" >> "${LOG_FILE}"
fi

# Protein: GWHBECW00000000.Protein.faa.gz (gzipped)
if [ -n "${PROTEIN_URL}" ]; then
  echo "  Downloading protein (gzipped)..."
  wget -q --no-check-certificate -O "${OUTPUT_DIRECTORY}/protein.faa.gz" "${PROTEIN_URL}"
  echo "  Decompressing protein..."
  gunzip -f "${OUTPUT_DIRECTORY}/protein.faa.gz"
  echo "Protein URL: ${PROTEIN_URL}" >> "${LOG_FILE}"
else
  echo "  No protein URL provided"
  echo "Protein: not available" >> "${LOG_FILE}"
fi

echo "  Download log: ${LOG_FILE}"
