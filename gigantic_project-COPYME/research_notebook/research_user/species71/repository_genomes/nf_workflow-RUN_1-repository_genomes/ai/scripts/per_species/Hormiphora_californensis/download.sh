#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Download Hormiphora californensis data from GitHub conchoecia/hormiphora
# Human: Eric Edsinger

# Special case: genome and release archive are separate downloads.
# Genome from raw GitHub; annotation and protein both extracted from release tar.gz.
# $3=genome_url, $4=release_archive_url (contains annotation.gff3 + protein.faa), $5=unused

set -euo pipefail

OUTPUT_DIRECTORY="$1"
REPOSITORY_URL="$2"
GENOME_URL="${3:-}"
ANNOTATION_URL="${4:-}"
PROTEIN_URL="${5:-}"

mkdir -p "${OUTPUT_DIRECTORY}"
LOG_FILE="${OUTPUT_DIRECTORY}/download_log.txt"

echo "  Downloading Hormiphora_californensis..."

{
  echo "Species: Hormiphora_californensis"
  echo "Repository: ${REPOSITORY_URL}"
  echo "Date: $(date)"
  echo ""
} > "${LOG_FILE}"

# Genome: UCSC_Hcal_v1.fa.gz (gzipped) - direct download from GitHub raw
if [ -n "${GENOME_URL}" ]; then
  echo "  Downloading genome (gzipped)..."
  wget -q -L -O "${OUTPUT_DIRECTORY}/genome.fasta.gz" "${GENOME_URL}"
  echo "  Decompressing genome..."
  gunzip -f "${OUTPUT_DIRECTORY}/genome.fasta.gz"
  echo "Genome URL: ${GENOME_URL}" >> "${LOG_FILE}"
else
  echo "  No genome URL provided"
  echo "Genome: not available" >> "${LOG_FILE}"
fi

# Annotation and protein: both from release archive (Hcv1av93_release.tar.gz)
# $4 (ANNOTATION_URL) holds the release archive URL for this species
if [ -n "${ANNOTATION_URL}" ]; then
  echo "  Downloading release archive (annotation + protein)..."
  wget -q -L -O "${OUTPUT_DIRECTORY}/release.tar.gz" "${ANNOTATION_URL}"
  echo "  Extracting annotation and protein from archive..."
  tar -xzf "${OUTPUT_DIRECTORY}/release.tar.gz" -C "${OUTPUT_DIRECTORY}"
  # Extract paths: Hcv1av93_release/Hcv1av93.gff.gz, Hcv1av93_release/Hcv1av93_model_proteins.pep.gz
  if [ -f "${OUTPUT_DIRECTORY}/Hcv1av93_release/Hcv1av93.gff.gz" ]; then
    gunzip -f "${OUTPUT_DIRECTORY}/Hcv1av93_release/Hcv1av93.gff.gz"
    mv "${OUTPUT_DIRECTORY}/Hcv1av93_release/Hcv1av93.gff" "${OUTPUT_DIRECTORY}/annotation.gff3"
  fi
  if [ -f "${OUTPUT_DIRECTORY}/Hcv1av93_release/Hcv1av93_model_proteins.pep.gz" ]; then
    gunzip -f "${OUTPUT_DIRECTORY}/Hcv1av93_release/Hcv1av93_model_proteins.pep.gz"
    mv "${OUTPUT_DIRECTORY}/Hcv1av93_release/Hcv1av93_model_proteins.pep" "${OUTPUT_DIRECTORY}/protein.faa"
  fi
  echo "  Cleaning up archive and extracted directory..."
  rm -rf "${OUTPUT_DIRECTORY}/release.tar.gz" "${OUTPUT_DIRECTORY}/Hcv1av93_release"
  echo "Annotation + Protein from release URL: ${ANNOTATION_URL}" >> "${LOG_FILE}"
else
  echo "  No release archive URL provided"
  echo "Annotation: not available" >> "${LOG_FILE}"
  echo "Protein: not available" >> "${LOG_FILE}"
fi

echo "  Download log: ${LOG_FILE}"
