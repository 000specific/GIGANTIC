#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Download Schmidtea mediterranea data from Zenodo (record 13798866)
# Human: Eric Edsinger

# Zenodo: https://zenodo.org/records/13798866
# Genome: schMedS3_h1.fa.gz (gzipped)
# Annotation: schMedS3_h1_ENCODE_hybrid_agat_hconf.gff3.gz (gzipped)
# Proteome: NA (not available from source)
# Outputs: genome.fasta, annotation.gff3, download_log.txt (no protein.faa)

set -euo pipefail

OUTPUT_DIRECTORY="$1"
REPOSITORY_URL="$2"
GENOME_URL="${3:-}"
ANNOTATION_URL="${4:-}"
PROTEIN_URL="${5:-}"

SPECIES="Schmidtea_mediterranea"

# User-provided direct URLs from Zenodo
DIRECT_GENOME_URL="https://zenodo.org/records/13798866/files/schMedS3_h1.fa.gz?download=1"
DIRECT_ANNOTATION_URL="https://zenodo.org/records/13798866/files/schMedS3_h1_ENCODE_hybrid_agat_hconf.gff3.gz?download=1"

mkdir -p "${OUTPUT_DIRECTORY}"
LOG_FILE="${OUTPUT_DIRECTORY}/download_log.txt"

echo "  Downloading ${SPECIES}..."

{
  echo "Species: ${SPECIES}"
  echo "Repository: ${REPOSITORY_URL}"
  echo "Source: Zenodo record 13798866"
  echo "Genome URL: ${DIRECT_GENOME_URL}"
  echo "Annotation URL: ${DIRECT_ANNOTATION_URL}"
  echo "Proteome: NA (not available from source)"
  echo "Date: $( date )"
  echo ""
} > "${LOG_FILE}"

# Genome (gzipped)
echo "  Downloading genome (gzipped)..."
wget -q -L -O "${OUTPUT_DIRECTORY}/genome.fasta.gz" "${DIRECT_GENOME_URL}"
if [ -s "${OUTPUT_DIRECTORY}/genome.fasta.gz" ]; then
  echo "  Decompressing genome..."
  gunzip -f "${OUTPUT_DIRECTORY}/genome.fasta.gz"
  echo "Genome: downloaded and decompressed" >> "${LOG_FILE}"
else
  echo "  WARNING: Genome download failed or empty"
  echo "Genome: download failed" >> "${LOG_FILE}"
fi

# Annotation (gzipped)
echo "  Downloading annotation (gzipped)..."
wget -q -L -O "${OUTPUT_DIRECTORY}/annotation.gff3.gz" "${DIRECT_ANNOTATION_URL}"
if [ -s "${OUTPUT_DIRECTORY}/annotation.gff3.gz" ]; then
  echo "  Decompressing annotation..."
  gunzip -f "${OUTPUT_DIRECTORY}/annotation.gff3.gz"
  echo "Annotation: downloaded and decompressed" >> "${LOG_FILE}"
else
  echo "  WARNING: Annotation download failed or empty"
  echo "Annotation: download failed" >> "${LOG_FILE}"
fi

# Proteome: NA (not available)
echo "  Proteome not available for ${SPECIES} (marked NA in source table)"
echo "Protein: NA (not available from source)" >> "${LOG_FILE}"
echo "  Note: protein may be extractable from genome+GFF using gffread in a later pipeline step" >> "${LOG_FILE}"

echo "  Download log: ${LOG_FILE}"
