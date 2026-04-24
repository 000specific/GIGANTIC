#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Download Pictodentalium vernedei data from FigShare private link
# Human: Eric Edsinger

# FigShare private link: https://figshare.com/s/b9a58037afb9cd3b60d5
# Direct URLs provided by user with private_link parameter
# Outputs: genome.fasta, annotation.gff3, protein.faa, download_log.txt

set -euo pipefail

OUTPUT_DIRECTORY="$1"
REPOSITORY_URL="$2"
GENOME_URL="${3:-}"
ANNOTATION_URL="${4:-}"
PROTEIN_URL="${5:-}"

SPECIES="Pictodentalium_vernedei"

# User-provided direct URLs (FigShare private link)
# NOTE: Must use ndownloader.figshare.com format (not figshare.com/ndownloader/)
# The figshare.com/ndownloader/ format returns HTTP 202 with empty content
DIRECT_GENOME_URL="https://ndownloader.figshare.com/files/38684090?private_link=b9a58037afb9cd3b60d5"
DIRECT_ANNOTATION_URL="https://ndownloader.figshare.com/files/38684084?private_link=b9a58037afb9cd3b60d5"
DIRECT_PROTEIN_URL="https://ndownloader.figshare.com/files/38684092?private_link=b9a58037afb9cd3b60d5"

mkdir -p "${OUTPUT_DIRECTORY}"
LOG_FILE="${OUTPUT_DIRECTORY}/download_log.txt"

echo "  Downloading ${SPECIES}..."

{
  echo "Species: ${SPECIES}"
  echo "Repository: ${REPOSITORY_URL}"
  echo "Source: FigShare private link b9a58037afb9cd3b60d5"
  echo "Genome URL: ${DIRECT_GENOME_URL}"
  echo "Annotation URL: ${DIRECT_ANNOTATION_URL}"
  echo "Protein URL: ${DIRECT_PROTEIN_URL}"
  echo "Date: $( date )"
  echo ""
} > "${LOG_FILE}"

# Genome
echo "  Downloading genome..."
wget -q -L -O "${OUTPUT_DIRECTORY}/genome.fasta" "${DIRECT_GENOME_URL}"
if [ -s "${OUTPUT_DIRECTORY}/genome.fasta" ]; then
  # Check if gzipped (FigShare sometimes serves compressed)
  if file "${OUTPUT_DIRECTORY}/genome.fasta" | grep -q "gzip"; then
    mv "${OUTPUT_DIRECTORY}/genome.fasta" "${OUTPUT_DIRECTORY}/genome.fasta.gz"
    gunzip -f "${OUTPUT_DIRECTORY}/genome.fasta.gz"
  fi
  echo "Genome: downloaded successfully" >> "${LOG_FILE}"
else
  echo "  WARNING: Genome download failed or empty"
  echo "Genome: download failed" >> "${LOG_FILE}"
fi

# Annotation (GFF)
echo "  Downloading annotation..."
wget -q -L -O "${OUTPUT_DIRECTORY}/annotation.gff3" "${DIRECT_ANNOTATION_URL}"
if [ -s "${OUTPUT_DIRECTORY}/annotation.gff3" ]; then
  if file "${OUTPUT_DIRECTORY}/annotation.gff3" | grep -q "gzip"; then
    mv "${OUTPUT_DIRECTORY}/annotation.gff3" "${OUTPUT_DIRECTORY}/annotation.gff3.gz"
    gunzip -f "${OUTPUT_DIRECTORY}/annotation.gff3.gz"
  fi
  echo "Annotation: downloaded successfully" >> "${LOG_FILE}"
else
  echo "  WARNING: Annotation download failed or empty"
  echo "Annotation: download failed" >> "${LOG_FILE}"
fi

# Proteome
echo "  Downloading protein..."
wget -q -L -O "${OUTPUT_DIRECTORY}/protein.faa" "${DIRECT_PROTEIN_URL}"
if [ -s "${OUTPUT_DIRECTORY}/protein.faa" ]; then
  if file "${OUTPUT_DIRECTORY}/protein.faa" | grep -q "gzip"; then
    mv "${OUTPUT_DIRECTORY}/protein.faa" "${OUTPUT_DIRECTORY}/protein.faa.gz"
    gunzip -f "${OUTPUT_DIRECTORY}/protein.faa.gz"
  fi
  PROTEIN_COUNT=$( grep -c '^>' "${OUTPUT_DIRECTORY}/protein.faa" 2>/dev/null || echo "0" )
  echo "Protein: downloaded successfully (${PROTEIN_COUNT} sequences)" >> "${LOG_FILE}"
  echo "  ${SPECIES}: ${PROTEIN_COUNT} protein sequences"
else
  echo "  WARNING: Protein download failed or empty"
  echo "Protein: download failed" >> "${LOG_FILE}"
fi

echo "  Download log: ${LOG_FILE}"
