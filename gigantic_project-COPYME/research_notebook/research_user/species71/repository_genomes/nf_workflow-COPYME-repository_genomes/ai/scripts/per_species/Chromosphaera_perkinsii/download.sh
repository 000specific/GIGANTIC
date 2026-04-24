#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Download Chromosphaera perkinsii data from FigShare
# Human: Eric Edsinger

set -euo pipefail

OUTPUT_DIRECTORY="$1"
REPOSITORY_URL="$2"
GENOME_URL="${3:-}"
ANNOTATION_URL="${4:-}"
PROTEIN_URL="${5:-}"

mkdir -p "${OUTPUT_DIRECTORY}"
LOG_FILE="${OUTPUT_DIRECTORY}/download_log.txt"

echo "  Downloading Chromosphaera_perkinsii..."

{
  echo "Species: Chromosphaera_perkinsii"
  echo "Repository: ${REPOSITORY_URL}"
  echo "Date: $(date)"
  echo ""
} > "${LOG_FILE}"

# Genome: Nk52_gDNA.fasta (plain text)
if [ -n "${GENOME_URL}" ]; then
  echo "  Downloading genome..."
  wget -q -O "${OUTPUT_DIRECTORY}/genome.fasta" "${GENOME_URL}"
  echo "Genome URL: ${GENOME_URL}" >> "${LOG_FILE}"
else
  echo "  No genome URL provided"
  echo "Genome: not available" >> "${LOG_FILE}"
fi

# Annotation: Nk52_long.annot.gff (plain text)
if [ -n "${ANNOTATION_URL}" ]; then
  echo "  Downloading annotation..."
  wget -q -O "${OUTPUT_DIRECTORY}/annotation.gff3" "${ANNOTATION_URL}"
  echo "Annotation URL: ${ANNOTATION_URL}" >> "${LOG_FILE}"
else
  echo "  No annotation URL provided"
  echo "Annotation: not available" >> "${LOG_FILE}"
fi

# Protein: Nk52_long.pep.fasta (plain text)
if [ -n "${PROTEIN_URL}" ]; then
  echo "  Downloading protein..."
  wget -q -O "${OUTPUT_DIRECTORY}/protein.faa" "${PROTEIN_URL}"
  echo "Protein URL: ${PROTEIN_URL}" >> "${LOG_FILE}"
else
  echo "  No protein URL provided"
  echo "Protein: not available" >> "${LOG_FILE}"
fi

echo "  Download log: ${LOG_FILE}"
