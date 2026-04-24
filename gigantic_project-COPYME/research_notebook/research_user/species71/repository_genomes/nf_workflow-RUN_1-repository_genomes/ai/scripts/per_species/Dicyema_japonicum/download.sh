#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Download Dicyema japonicum data from OIST Marine Genomics
# Human: Eric Edsinger

set -euo pipefail

OUTPUT_DIRECTORY="$1"
REPOSITORY_URL="$2"
GENOME_URL="${3:-}"
ANNOTATION_URL="${4:-}"
PROTEIN_URL="${5:-}"

mkdir -p "${OUTPUT_DIRECTORY}"
LOG_FILE="${OUTPUT_DIRECTORY}/download_log.txt"

echo "  Downloading Dicyema_japonicum..."

{
  echo "Species: Dicyema_japonicum"
  echo "Repository: ${REPOSITORY_URL}"
  echo "Date: $(date)"
  echo ""
} > "${LOG_FILE}"

# Genome: dicyema_japonicum_scaffold.fa.gz (gzipped)
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

# Annotation: dicyema_japonicum_genemodel.gff.gz (gzipped)
if [ -n "${ANNOTATION_URL}" ]; then
  echo "  Downloading annotation (gzipped)..."
  wget -q -O "${OUTPUT_DIRECTORY}/annotation.gff3.gz" "${ANNOTATION_URL}"
  echo "  Decompressing annotation..."
  gunzip -f "${OUTPUT_DIRECTORY}/annotation.gff3.gz"
  echo "Annotation URL: ${ANNOTATION_URL}" >> "${LOG_FILE}"
else
  echo "  No annotation URL provided"
  echo "Annotation: not available" >> "${LOG_FILE}"
fi

# Protein: dicyema_japonicum_genemodel_prot.fa.gz (gzipped)
if [ -n "${PROTEIN_URL}" ]; then
  echo "  Downloading protein (gzipped)..."
  wget -q -O "${OUTPUT_DIRECTORY}/protein.faa.gz" "${PROTEIN_URL}"
  echo "  Decompressing protein..."
  gunzip -f "${OUTPUT_DIRECTORY}/protein.faa.gz"
  echo "Protein URL: ${PROTEIN_URL}" >> "${LOG_FILE}"
else
  echo "  No protein URL provided"
  echo "Protein: not available" >> "${LOG_FILE}"
fi

echo "  Download log: ${LOG_FILE}"
