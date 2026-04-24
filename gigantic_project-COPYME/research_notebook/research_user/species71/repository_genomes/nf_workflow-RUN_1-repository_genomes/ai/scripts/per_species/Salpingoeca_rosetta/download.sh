#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Download Salpingoeca rosetta from Dryad (doi:10.5061/dryad.dncjsxm47, Schultz et al. 2023)
# Human: Eric Edsinger

# Dryad shared genomes.tar.gz: Ancient gene linkages paper, chromosome-scale genomes
# Outputs: genome.fasta, annotation.gff3, protein.faa, download_log.txt

set -uo pipefail

OUTPUT_DIRECTORY="$1"
REPOSITORY_URL="$2"
GENOME_URL="${3:-}"
ANNOTATION_URL="${4:-}"
PROTEIN_URL="${5:-}"

SPECIES="Salpingoeca_rosetta"
ARCHIVE_URL="${GENOME_URL:-https://datadryad.org/downloads/file_stream/2198368}"

mkdir -p "${OUTPUT_DIRECTORY}"
LOG_FILE="${OUTPUT_DIRECTORY}/download_log.txt"
TEMP_DIR=$( mktemp -d )
trap 'rm -rf "${TEMP_DIR}"' EXIT

# Shared cache to avoid re-downloading 2.63 GB archive for each Dryad species
CACHE_DIR="${OUTPUT_DIRECTORY}/../_dryad_schultz_cache"
mkdir -p "${CACHE_DIR}"

echo "  Downloading ${SPECIES}..."

{
  echo "Species: ${SPECIES}"
  echo "Repository: ${REPOSITORY_URL}"
  echo "Archive URL: ${ARCHIVE_URL}"
  echo "Date: $( date )"
  echo ""
} > "${LOG_FILE}"

# Download shared genomes.tar.gz (use cache if available)
if [ -f "${CACHE_DIR}/genomes.tar.gz" ] && [ -s "${CACHE_DIR}/genomes.tar.gz" ]; then
  echo "  Using cached genomes.tar.gz from ${CACHE_DIR}"
else
  echo "  Downloading genomes.tar.gz (2.63 GB) to shared cache..."
  rm -f "${CACHE_DIR}/genomes.tar.gz"
  wget -q -L --no-check-certificate -O "${CACHE_DIR}/genomes.tar.gz" "${ARCHIVE_URL}"
  # Validate download is not empty
  if [ ! -s "${CACHE_DIR}/genomes.tar.gz" ]; then
    echo "  WARNING: Downloaded genomes.tar.gz is 0 bytes!"
    echo "  Dryad may block automated downloads (403 Forbidden)."
    echo "  *** USER INPUT NEEDED for ${SPECIES} ***"
    echo "  Please download manually from: ${REPOSITORY_URL}"
    echo "  Place genomes.tar.gz into: ${CACHE_DIR}/"
    echo "  Then re-run this pipeline."
    echo "USER INPUT NEEDED: Dryad download blocked (403 Forbidden)" >> "${LOG_FILE}"
    echo "Manual download URL: ${REPOSITORY_URL}" >> "${LOG_FILE}"
    rm -f "${CACHE_DIR}/genomes.tar.gz"
    exit 0
  fi
  ARCHIVE_SIZE=$( stat --format=%s "${CACHE_DIR}/genomes.tar.gz" 2>/dev/null || stat -f%z "${CACHE_DIR}/genomes.tar.gz" 2>/dev/null || echo "unknown" )
  echo "  Downloaded archive size: ${ARCHIVE_SIZE} bytes"
  echo "Archive size: ${ARCHIVE_SIZE} bytes" >> "${LOG_FILE}"
fi

# Extract archive (use cached extraction if available)
if [ -d "${CACHE_DIR}/extracted" ]; then
  echo "  Using cached extraction..."
else
  echo "  Extracting archive to shared cache..."
  mkdir -p "${CACHE_DIR}/extracted"
  tar xzf "${CACHE_DIR}/genomes.tar.gz" -C "${CACHE_DIR}/extracted"
fi

# Find species-specific files (Salpingoeca, salpingoeca, Sros, sros, rosetta)
# Use -path to restrict search to species-specific subdirectories
SEARCH_DIR="${CACHE_DIR}/extracted"

# Debug: list archive contents into log so we can see what's inside
echo "" >> "${LOG_FILE}"
echo "=== Archive contents (first 50 files) ===" >> "${LOG_FILE}"
find "${SEARCH_DIR}" -type f | head -50 >> "${LOG_FILE}"
echo "=== End archive contents ===" >> "${LOG_FILE}"
echo "" >> "${LOG_FILE}"

# Decompress any .gz files in the extraction directory
echo "  Decompressing any .gz files in extracted archive..."
find "${SEARCH_DIR}" -type f -name "*.gz" -exec gunzip -kf {} \; 2>/dev/null || true

# Find genome (search for .fasta, .fa, .fna extensions)
GENOME_FILE=$( find "${SEARCH_DIR}" -type f \( -path "*Salpingoeca*" -o -path "*salpingoeca*" -o -path "*Sros*" -o -path "*sros*" -o -path "*rosetta*" \) \( -name "*gDNA*" -o -name "*assembly*" -o -name "*genome*" \) \( -name "*.fasta" -o -name "*.fa" -o -name "*.fna" \) 2>/dev/null | head -1 )
if [ -z "${GENOME_FILE}" ]; then
  # Broader search: any fasta-like file associated with the species (largest = likely genome)
  GENOME_FILE=$( find "${SEARCH_DIR}" -type f \( -path "*Salpingoeca*" -o -path "*salpingoeca*" -o -path "*Sros*" -o -path "*sros*" -o -path "*rosetta*" \) \( -name "*.fasta" -o -name "*.fa" -o -name "*.fna" \) -exec wc -c {} \; 2>/dev/null | sort -rn | head -1 | awk '{print $2}' )
fi
if [ -z "${GENOME_FILE}" ]; then
  # Broadest search: any fasta-like file anywhere (for unknown archive structures)
  GENOME_FILE=$( find "${SEARCH_DIR}" -type f \( -name "*gDNA*" -o -name "*assembly*" -o -name "*genome*" \) \( -name "*.fasta" -o -name "*.fa" -o -name "*.fna" \) 2>/dev/null | head -1 )
fi
if [ -n "${GENOME_FILE}" ] && [ -f "${GENOME_FILE}" ]; then
  cp "${GENOME_FILE}" "${OUTPUT_DIRECTORY}/genome.fasta"
  echo "Genome: ${GENOME_FILE}" >> "${LOG_FILE}"
else
  echo "  WARNING: No genome file found for ${SPECIES}"
  echo "Genome: not found" >> "${LOG_FILE}"
fi

# Find annotation (search for .gff, .gff3, .gtf extensions)
ANNOT_FILE=$( find "${SEARCH_DIR}" -type f \( -path "*Salpingoeca*" -o -path "*salpingoeca*" -o -path "*Sros*" -o -path "*sros*" -o -path "*rosetta*" \) \( -name "*.gff" -o -name "*.gff3" -o -name "*.gtf" \) 2>/dev/null | head -1 )
if [ -z "${ANNOT_FILE}" ]; then
  # Broader: any annotation file in archive
  ANNOT_FILE=$( find "${SEARCH_DIR}" -type f \( -name "*.gff" -o -name "*.gff3" -o -name "*.gtf" \) 2>/dev/null | head -1 )
fi
if [ -n "${ANNOT_FILE}" ] && [ -f "${ANNOT_FILE}" ]; then
  cp "${ANNOT_FILE}" "${OUTPUT_DIRECTORY}/annotation.gff3"
  echo "Annotation: ${ANNOT_FILE}" >> "${LOG_FILE}"
else
  echo "  WARNING: No annotation file found for ${SPECIES}"
  echo "Annotation: not found" >> "${LOG_FILE}"
fi

# Find protein (search for .fasta, .fa, .faa, .pep extensions)
PROTEIN_FILE=$( find "${SEARCH_DIR}" -type f \( -path "*Salpingoeca*" -o -path "*salpingoeca*" -o -path "*Sros*" -o -path "*sros*" -o -path "*rosetta*" \) \( -name "*pep*" -o -name "*protein*" -o -name "*proteome*" \) \( -name "*.fasta" -o -name "*.fa" -o -name "*.faa" -o -name "*.pep" \) 2>/dev/null | grep -v -i "cds" | head -1 || true )
if [ -z "${PROTEIN_FILE}" ]; then
  PROTEIN_FILE=$( find "${SEARCH_DIR}" -type f \( -path "*Salpingoeca*" -o -path "*salpingoeca*" -o -path "*Sros*" -o -path "*sros*" -o -path "*rosetta*" \) \( -name "*pep*" -o -name "*protein*" -o -name "*proteome*" -o -name "*.faa" -o -name "*.pep" \) 2>/dev/null | grep -v -i "cds" | head -1 || true )
fi
if [ -z "${PROTEIN_FILE}" ]; then
  # Broadest: any protein-like file in archive
  PROTEIN_FILE=$( find "${SEARCH_DIR}" -type f \( -name "*pep*" -o -name "*protein*" -o -name "*proteome*" -o -name "*.faa" -o -name "*.pep" \) 2>/dev/null | grep -v -i "cds" | head -1 || true )
fi
if [ -n "${PROTEIN_FILE}" ] && [ -f "${PROTEIN_FILE}" ]; then
  cp "${PROTEIN_FILE}" "${OUTPUT_DIRECTORY}/protein.faa"
  echo "Protein: ${PROTEIN_FILE}" >> "${LOG_FILE}"
else
  echo "  WARNING: No protein file found for ${SPECIES}"
  echo "Protein: not found" >> "${LOG_FILE}"
fi

echo "  Download log: ${LOG_FILE}"
