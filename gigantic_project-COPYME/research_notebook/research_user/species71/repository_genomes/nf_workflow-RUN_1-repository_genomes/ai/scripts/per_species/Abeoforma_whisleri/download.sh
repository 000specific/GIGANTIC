#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Download Abeoforma whisleri data from FigShare
# Human: Eric Edsinger

# Special cases: genome is gzipped; no annotation file available.
# Outputs: genome.fasta, protein.faa, download_log.txt (no annotation.gff3)

set -euo pipefail

OUTPUT_DIRECTORY="$1"
REPOSITORY_URL="$2"
GENOME_URL="${3:-}"
ANNOTATION_URL="${4:-}"
PROTEIN_URL="${5:-}"

mkdir -p "${OUTPUT_DIRECTORY}"
LOG_FILE="${OUTPUT_DIRECTORY}/download_log.txt"

echo "  Downloading Abeoforma_whisleri..."

{
  echo "Species: Abeoforma_whisleri"
  echo "Repository: ${REPOSITORY_URL}"
  echo "Date: $(date)"
  echo ""
} > "${LOG_FILE}"

# Genome: assembly.fasta.gz (gzipped - decompress after download)
if [ -n "${GENOME_URL}" ]; then
  echo "  Downloading genome (gzipped)..."
  wget -q -O "${OUTPUT_DIRECTORY}/genome.fasta.gz" "${GENOME_URL}"
  echo "  Decompressing genome..."
  gunzip -f "${OUTPUT_DIRECTORY}/genome.fasta.gz"
  echo "Genome URL: ${GENOME_URL}" >> "${LOG_FILE}"
else
  echo "  No genome URL provided"
  echo "Genome: not available" >> "${LOG_FILE}"
fi

# Annotation: not available for this species
echo "  No annotation URL provided (not available for Abeoforma_whisleri)"
echo "Annotation: not available" >> "${LOG_FILE}"

# Protein: augustus.aa (plain text)
if [ -n "${PROTEIN_URL}" ]; then
  echo "  Downloading protein..."
  wget -q -O "${OUTPUT_DIRECTORY}/protein.faa" "${PROTEIN_URL}"
  echo "Protein URL: ${PROTEIN_URL}" >> "${LOG_FILE}"
else
  echo "  No protein URL provided"
  echo "Protein: not available" >> "${LOG_FILE}"
fi

echo "  Download log: ${LOG_FILE}"
