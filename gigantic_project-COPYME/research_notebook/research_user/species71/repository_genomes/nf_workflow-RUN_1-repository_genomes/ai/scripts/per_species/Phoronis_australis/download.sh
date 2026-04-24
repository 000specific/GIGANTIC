#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Download Phoronis australis data from OIST Marine Genomics
# Human: Eric Edsinger

# OIST Marine Genomics Unit: genome, annotation, and protein (all gzipped).
# Outputs: genome.fasta, annotation.gff3, protein.faa, download_log.txt

set -euo pipefail

OUTPUT_DIRECTORY="$1"
REPOSITORY_URL="$2"
GENOME_URL="${3:-}"
ANNOTATION_URL="${4:-}"
PROTEIN_URL="${5:-}"

SPECIES="Phoronis_australis"
DIRECT_GENOME_URL="https://marinegenomics.oist.jp/pau_v2/download/pau_genome_v2.0.fa.gz"
DIRECT_ANNOTATION_URL="https://marinegenomics.oist.jp/pau_v2/download/51_pau_v2.gff.gz"
DIRECT_PROTEIN_URL="https://marinegenomics.oist.jp/pau_v2/download/pau_genome_v2.0_prot.fa.gz"

mkdir -p "${OUTPUT_DIRECTORY}"
LOG_FILE="${OUTPUT_DIRECTORY}/download_log.txt"

echo "  Downloading ${SPECIES}..."

{
  echo "Species: ${SPECIES}"
  echo "Repository: ${REPOSITORY_URL}"
  echo "Source: OIST Marine Genomics Unit"
  echo "Genome URL: ${DIRECT_GENOME_URL}"
  echo "Annotation URL: ${DIRECT_ANNOTATION_URL}"
  echo "Protein URL: ${DIRECT_PROTEIN_URL}"
  echo "Date: $( date )"
  echo ""
} > "${LOG_FILE}"

# Genome: gzipped FASTA
echo "  Downloading genome (gzipped)..."
wget -q -O "${OUTPUT_DIRECTORY}/genome.fasta.gz" "${DIRECT_GENOME_URL}"
echo "  Decompressing genome..."
gunzip -f "${OUTPUT_DIRECTORY}/genome.fasta.gz"
echo "Genome URL: ${DIRECT_GENOME_URL}" >> "${LOG_FILE}"

# Annotation: gzipped GFF
echo "  Downloading annotation (gzipped)..."
wget -q -O "${OUTPUT_DIRECTORY}/annotation.gff3.gz" "${DIRECT_ANNOTATION_URL}"
echo "  Decompressing annotation..."
gunzip -f "${OUTPUT_DIRECTORY}/annotation.gff3.gz"
echo "Annotation URL: ${DIRECT_ANNOTATION_URL}" >> "${LOG_FILE}"

# Protein: gzipped FASTA
echo "  Downloading protein (gzipped)..."
wget -q -O "${OUTPUT_DIRECTORY}/protein.faa.gz" "${DIRECT_PROTEIN_URL}"
echo "  Decompressing protein..."
gunzip -f "${OUTPUT_DIRECTORY}/protein.faa.gz"
echo "Protein URL: ${DIRECT_PROTEIN_URL}" >> "${LOG_FILE}"

echo "  Download log: ${LOG_FILE}"
