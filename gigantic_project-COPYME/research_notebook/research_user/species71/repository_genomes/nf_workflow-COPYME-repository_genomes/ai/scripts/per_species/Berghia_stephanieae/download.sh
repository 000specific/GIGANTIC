#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Download Berghia stephanieae from Dryad (doi:10.6076/D1BS33)
# Human: Eric Edsinger

# Two separate ZIP files: genome (9_final_genome_files.zip) and gene predictions (3_braker_prediction.zip)
# Outputs: genome.fasta, annotation.gff3, protein.faa, download_log.txt

set -uo pipefail

OUTPUT_DIRECTORY="$1"
REPOSITORY_URL="$2"
GENOME_URL="${3:-https://datadryad.org/downloads/file_stream/2803879}"
ANNOTATION_URL="${4:-}"
PROTEIN_URL="${5:-https://datadryad.org/downloads/file_stream/2803874}"

SPECIES="Berghia_stephanieae"

mkdir -p "${OUTPUT_DIRECTORY}"
LOG_FILE="${OUTPUT_DIRECTORY}/download_log.txt"
TEMP_DIR=$( mktemp -d )
trap 'rm -rf "${TEMP_DIR}"' EXIT

echo "  Downloading ${SPECIES}..."

{
  echo "Species: ${SPECIES}"
  echo "Repository: ${REPOSITORY_URL}"
  echo "Source: Dryad doi:10.6076/D1BS33"
  echo "Date: $( date )"
  echo ""
} > "${LOG_FILE}"

# Download genome ZIP (9_final_genome_files.zip)
echo "  Downloading genome ZIP..."
wget -q -L -O "${TEMP_DIR}/genome.zip" "${GENOME_URL}"
unzip -q -o "${TEMP_DIR}/genome.zip" -d "${TEMP_DIR}/genome_extract"

# Find genome FASTA (*.fa or *.fasta)
GENOME_FILE=$( find "${TEMP_DIR}/genome_extract" -type f \( -name "*.fa" -o -name "*.fasta" \) 2>/dev/null | head -1 )
if [ -n "${GENOME_FILE}" ] && [ -f "${GENOME_FILE}" ]; then
  cp "${GENOME_FILE}" "${OUTPUT_DIRECTORY}/genome.fasta"
  echo "Genome: ${GENOME_FILE}" >> "${LOG_FILE}"
else
  echo "  WARNING: No genome FASTA found in genome ZIP"
  echo "Genome: not found" >> "${LOG_FILE}"
fi

# Download gene predictions ZIP (3_braker_prediction.zip) - contains annotation and protein
echo "  Downloading gene predictions ZIP..."
wget -q -L -O "${TEMP_DIR}/predictions.zip" "${PROTEIN_URL}"
unzip -q -o "${TEMP_DIR}/predictions.zip" -d "${TEMP_DIR}/predictions_extract"

# Find annotation (augustus.anysupport.gff3 or *.gff3)
ANNOT_FILE=$( find "${TEMP_DIR}/predictions_extract" -type f \( -name "*.gff3" -o -name "*.gff" \) 2>/dev/null | head -1 )
if [ -n "${ANNOT_FILE}" ] && [ -f "${ANNOT_FILE}" ]; then
  cp "${ANNOT_FILE}" "${OUTPUT_DIRECTORY}/annotation.gff3"
  echo "Annotation: ${ANNOT_FILE}" >> "${LOG_FILE}"
else
  echo "  WARNING: No annotation GFF3 found"
  echo "Annotation: not found" >> "${LOG_FILE}"
fi

# Find protein (augustus.hints.anysupport.aa or *.aa)
PROTEIN_FILE=$( find "${TEMP_DIR}/predictions_extract" -type f \( -name "*.aa" -o -name "*.pep" -o -name "*protein*" \) 2>/dev/null | grep -v -i "cds" | head -1 )
if [ -n "${PROTEIN_FILE}" ] && [ -f "${PROTEIN_FILE}" ]; then
  cp "${PROTEIN_FILE}" "${OUTPUT_DIRECTORY}/protein.faa"
  echo "Protein: ${PROTEIN_FILE}" >> "${LOG_FILE}"
else
  echo "  WARNING: No protein file found"
  echo "Protein: not found" >> "${LOG_FILE}"
fi

echo "  Download log: ${LOG_FILE}"
