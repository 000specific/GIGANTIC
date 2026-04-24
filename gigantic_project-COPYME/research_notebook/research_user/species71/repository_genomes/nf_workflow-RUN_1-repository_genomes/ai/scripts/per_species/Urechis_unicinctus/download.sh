#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Download Urechis unicinctus from NCBI (GCA_025325755.1)
# Human: Eric Edsinger

# NCBI has this genome: GCA_025325755.1. Using datasets CLI instead of complex Dryad discovery.
# Outputs: genome.fasta, annotation.gff3, protein.faa, download_log.txt

set -euo pipefail

OUTPUT_DIRECTORY="$1"
REPOSITORY_URL="$2"
GENOME_URL="${3:-}"
ANNOTATION_URL="${4:-}"
PROTEIN_URL="${5:-}"

SPECIES="Urechis_unicinctus"
NCBI_ACCESSION="GCA_034190875.2"
DATASETS_CLI="/blue/moroz/share/edsinger/conda/envs/ncbi_datasets/bin/datasets"

# Resolve OUTPUT_DIRECTORY to absolute path before any cd
mkdir -p "${OUTPUT_DIRECTORY}"
OUTPUT_DIRECTORY="$( cd "${OUTPUT_DIRECTORY}" && pwd )"
LOG_FILE="${OUTPUT_DIRECTORY}/download_log.txt"
TEMP_DIR=$( mktemp -d )
trap 'rm -rf "${TEMP_DIR}"' EXIT

echo "  Downloading ${SPECIES}..."

{
  echo "Species: ${SPECIES}"
  echo "Repository: ${REPOSITORY_URL}"
  echo "NCBI accession: ${NCBI_ACCESSION}"
  echo "Note: Using NCBI instead of Dryad (simpler, more reliable)"
  echo "Date: $( date )"
  echo ""
} > "${LOG_FILE}"

# Check if NCBI datasets CLI is available
if [ ! -x "${DATASETS_CLI}" ]; then
  echo "  WARNING: datasets CLI not found at ${DATASETS_CLI}"
  echo "datasets: not available at ${DATASETS_CLI}" >> "${LOG_FILE}"
  exit 1
fi

# Use NCBI datasets to download genome, gff3, protein
echo "  Downloading from NCBI (genome, gff3, protein)..."
cd "${TEMP_DIR}"
"${DATASETS_CLI}" download genome accession "${NCBI_ACCESSION}" --include genome,gff3,protein 2>/dev/null || {
  echo "  ERROR: datasets download failed"
  echo "Download: failed" >> "${LOG_FILE}"
  exit 1
}

# Extract from zip
unzip -q -o ncbi_dataset.zip 2>/dev/null || true

# Find and copy genome
GENOME_FILE=$( find "${TEMP_DIR}" -type f -name "*.fna" 2>/dev/null | head -1 )
if [ -z "${GENOME_FILE}" ]; then
  GENOME_FILE=$( find "${TEMP_DIR}" -type f -name "*.fa" 2>/dev/null | head -1 )
fi
if [ -n "${GENOME_FILE}" ] && [ -f "${GENOME_FILE}" ]; then
  cp "${GENOME_FILE}" "${OUTPUT_DIRECTORY}/genome.fasta"
  echo "Genome: ${GENOME_FILE}" >> "${LOG_FILE}"
else
  echo "  WARNING: No genome file found in NCBI dataset"
  echo "Genome: not found" >> "${LOG_FILE}"
fi

# Find and copy annotation
ANNOT_FILE=$( find "${TEMP_DIR}" -type f -name "*.gff3" 2>/dev/null | head -1 )
if [ -z "${ANNOT_FILE}" ]; then
  ANNOT_FILE=$( find "${TEMP_DIR}" -type f -name "*.gff" 2>/dev/null | head -1 )
fi
if [ -n "${ANNOT_FILE}" ] && [ -f "${ANNOT_FILE}" ]; then
  cp "${ANNOT_FILE}" "${OUTPUT_DIRECTORY}/annotation.gff3"
  echo "Annotation: ${ANNOT_FILE}" >> "${LOG_FILE}"
else
  echo "  WARNING: No annotation file found"
  echo "Annotation: not found" >> "${LOG_FILE}"
fi

# Find and copy protein
PROTEIN_FILE=$( find "${TEMP_DIR}" -type f -name "*.faa" 2>/dev/null | head -1 )
if [ -z "${PROTEIN_FILE}" ]; then
  PROTEIN_FILE=$( find "${TEMP_DIR}" -type f \( -name "*.aa" -o -name "*.pep" \) 2>/dev/null | head -1 )
fi
if [ -n "${PROTEIN_FILE}" ] && [ -f "${PROTEIN_FILE}" ]; then
  cp "${PROTEIN_FILE}" "${OUTPUT_DIRECTORY}/protein.faa"
  echo "Protein: ${PROTEIN_FILE}" >> "${LOG_FILE}"
else
  echo "  WARNING: No protein file found"
  echo "Protein: not found" >> "${LOG_FILE}"
fi

echo "  Download log: ${LOG_FILE}"
