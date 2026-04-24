#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Download Lissachatina fulica from GigaDB (dataset 100647)
# Human: Eric Edsinger

# Lissachatina fulica (giant African land snail) is NOT at NCBI.
# Primary source: GigaDB dataset 100647
# FTP: ftp://parrot.genomics.cn/gigadb/pub/10.5524/100001_101000/100647/
# If FTP fails, marks as needing user input.
# Outputs: genome.fasta, annotation.gff3, protein.faa, download_log.txt

set -uo pipefail

OUTPUT_DIRECTORY="$1"
REPOSITORY_URL="$2"
GENOME_URL="${3:-}"
ANNOTATION_URL="${4:-}"
PROTEIN_URL="${5:-}"

SPECIES="Lissachatina_fulica"

mkdir -p "${OUTPUT_DIRECTORY}"
OUTPUT_DIRECTORY="$( cd "${OUTPUT_DIRECTORY}" && pwd )"
LOG_FILE="${OUTPUT_DIRECTORY}/download_log.txt"

echo "  Downloading ${SPECIES}..."

{
  echo "Species: ${SPECIES}"
  echo "Repository: ${REPOSITORY_URL}"
  echo "Source: GigaDB dataset 100647"
  echo "Note: Not available at NCBI. Using GigaDB FTP."
  echo "Date: $( date )"
  echo ""
} > "${LOG_FILE}"

# Try GigaDB FTP for genome
GIGADB_FTP="ftp://parrot.genomics.cn/gigadb/pub/10.5524/100001_101000/100647"

echo "  Trying GigaDB FTP download..."
# Try to list FTP directory
if wget -q --spider "${GIGADB_FTP}/" 2>/dev/null; then
  echo "  GigaDB FTP accessible, downloading..."
  # Download genome
  wget -q -O "${OUTPUT_DIRECTORY}/genome.fasta.gz" "${GIGADB_FTP}/Lissachatina_fulica_genome.fa.gz" 2>/dev/null || true
  if [ -s "${OUTPUT_DIRECTORY}/genome.fasta.gz" ]; then
    gunzip -f "${OUTPUT_DIRECTORY}/genome.fasta.gz"
    echo "Genome: GigaDB FTP" >> "${LOG_FILE}"
  fi
  # Download annotation
  wget -q -O "${OUTPUT_DIRECTORY}/annotation.gff3.gz" "${GIGADB_FTP}/Lissachatina_fulica.gff3.gz" 2>/dev/null || true
  if [ -s "${OUTPUT_DIRECTORY}/annotation.gff3.gz" ]; then
    gunzip -f "${OUTPUT_DIRECTORY}/annotation.gff3.gz"
    echo "Annotation: GigaDB FTP" >> "${LOG_FILE}"
  fi
  # Download protein
  wget -q -O "${OUTPUT_DIRECTORY}/protein.faa.gz" "${GIGADB_FTP}/Lissachatina_fulica_protein.fa.gz" 2>/dev/null || true
  if [ -s "${OUTPUT_DIRECTORY}/protein.faa.gz" ]; then
    gunzip -f "${OUTPUT_DIRECTORY}/protein.faa.gz"
    echo "Protein: GigaDB FTP" >> "${LOG_FILE}"
  fi
else
  echo "  GigaDB FTP not accessible"
fi

# Check what we got
GOT_FILES=0
[ -s "${OUTPUT_DIRECTORY}/genome.fasta" ] && GOT_FILES=1
[ -s "${OUTPUT_DIRECTORY}/protein.faa" ] && GOT_FILES=1

if [ "${GOT_FILES}" -eq 0 ]; then
  echo ""
  echo "  *** USER INPUT NEEDED for ${SPECIES} ***"
  echo "  GigaDB FTP download failed or returned empty files."
  echo "  Please download manually from: http://gigadb.org/dataset/100647"
  echo "  Place files as:"
  echo "    ${OUTPUT_DIRECTORY}/genome.fasta"
  echo "    ${OUTPUT_DIRECTORY}/annotation.gff3"
  echo "    ${OUTPUT_DIRECTORY}/protein.faa"
  echo "USER INPUT NEEDED: Manual download from GigaDB" >> "${LOG_FILE}"
fi

echo "  Download log: ${LOG_FILE}"
