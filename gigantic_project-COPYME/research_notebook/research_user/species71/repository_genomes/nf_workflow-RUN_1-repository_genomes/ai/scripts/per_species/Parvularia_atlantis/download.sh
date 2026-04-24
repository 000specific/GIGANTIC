#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Download Parvularia atlantis from FigShare (article 19895962)
# Human: Eric Edsinger

# FigShare ZIP archive: genome, annotation, protein in single ZIP
# Outputs: genome.fasta, annotation.gff3, protein.faa, download_log.txt

set -uo pipefail

OUTPUT_DIRECTORY="$1"
REPOSITORY_URL="$2"
GENOME_URL="${3:-}"
ANNOTATION_URL="${4:-}"
PROTEIN_URL="${5:-}"

SPECIES="Parvularia_atlantis"
ZIP_URL="${GENOME_URL:-https://ndownloader.figshare.com/files/35315719}"

mkdir -p "${OUTPUT_DIRECTORY}"
LOG_FILE="${OUTPUT_DIRECTORY}/download_log.txt"
TEMP_DIR=$( mktemp -d )
trap 'rm -rf "${TEMP_DIR}"' EXIT

echo "  Downloading ${SPECIES}..."

{
  echo "Species: ${SPECIES}"
  echo "Repository: ${REPOSITORY_URL}"
  echo "ZIP URL: ${ZIP_URL}"
  echo "Date: $( date )"
  echo ""
} > "${LOG_FILE}"

# Download ZIP
echo "  Downloading ZIP archive..."
wget -q -O "${TEMP_DIR}/${SPECIES}.zip" "${ZIP_URL}"
unzip -q -o "${TEMP_DIR}/${SPECIES}.zip" -d "${TEMP_DIR}"

# Find genome (gDNA, assembly, or genome in name; else largest fasta)
GENOME_FILE=$( find "${TEMP_DIR}" -type f \( -name "*gDNA*" -o -name "*assembly*" -o -name "*genome*" \) -name "*.fasta" 2>/dev/null | head -1 )
if [ -z "${GENOME_FILE}" ]; then
  GENOME_FILE=$( find "${TEMP_DIR}" -type f -name "*.fasta" -exec wc -c {} \; 2>/dev/null | sort -rn | head -1 | awk '{print $2}' )
fi
if [ -n "${GENOME_FILE}" ] && [ -f "${GENOME_FILE}" ]; then
  cp "${GENOME_FILE}" "${OUTPUT_DIRECTORY}/genome.fasta"
  echo "Genome: ${GENOME_FILE}" >> "${LOG_FILE}"
else
  echo "  WARNING: No genome file found in archive"
  echo "Genome: not found in archive" >> "${LOG_FILE}"
fi

# Find annotation (GFF/GFF3)
ANNOT_FILE=$( find "${TEMP_DIR}" -type f \( -name "*.gff" -o -name "*.gff3" \) 2>/dev/null | head -1 )
if [ -n "${ANNOT_FILE}" ] && [ -f "${ANNOT_FILE}" ]; then
  cp "${ANNOT_FILE}" "${OUTPUT_DIRECTORY}/annotation.gff3"
  echo "Annotation: ${ANNOT_FILE}" >> "${LOG_FILE}"
else
  echo "  WARNING: No annotation file found in archive"
  echo "Annotation: not found in archive" >> "${LOG_FILE}"
fi

# Find protein (pep or protein in name; MUST be FASTA format: .fasta, .fa, .faa, .pep; exclude .gff/.gff3/.gtf)
PROTEIN_FILE=$( find "${TEMP_DIR}" -type f \( -name "*pep*" -o -name "*protein*" \) \( -name "*.fasta" -o -name "*.fa" -o -name "*.faa" -o -name "*.pep" \) 2>/dev/null | grep -v -i "cds" | grep -v -i "\.gff" | head -1 || true )
if [ -z "${PROTEIN_FILE}" ]; then
  # Broader search: any FASTA-like file with protein/pep keywords (exclude GFF annotations)
  PROTEIN_FILE=$( find "${TEMP_DIR}" -type f \( -name "*.fasta" -o -name "*.fa" -o -name "*.faa" -o -name "*.pep" \) 2>/dev/null | grep -i -E "pep|protein|correctedprotein" | grep -v -i "cds" | head -1 || true )
fi
if [ -n "${PROTEIN_FILE}" ] && [ -f "${PROTEIN_FILE}" ]; then
  cp "${PROTEIN_FILE}" "${OUTPUT_DIRECTORY}/protein.faa"
  echo "Protein: ${PROTEIN_FILE}" >> "${LOG_FILE}"
else
  echo "  WARNING: No protein file found in archive"
  echo "Protein: not found in archive" >> "${LOG_FILE}"
fi

echo "  Download log: ${LOG_FILE}"
