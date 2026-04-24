#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Download Hypsibius dujardini proteome (MATEdb2 fallback to NCBI GCA_002155985.1)
# Human: Eric Edsinger

# Strategy: Try MATEdb2 Zenodo first, then fall back to NCBI datasets
# Note: MATEdb2 tardigrada has HEXE1, PMET1, RVAR1 but NOT Hypsibius
# Note: This species is also known as Hypsibius exemplaris in NCBI
# NCBI fallback: GCA_002155985.1
# Outputs: protein.faa, download_log.txt (proteome-only)

set -uo pipefail

OUTPUT_DIRECTORY="$1"
REPOSITORY_URL="$2"
GENOME_URL="${3:-}"
ANNOTATION_URL="${4:-}"
PROTEIN_URL="${5:-}"

SPECIES="Hypsibius_dujardini"
NCBI_ACCESSION="GCA_002082055.1"
NCBI_DATASETS="/blue/moroz/share/edsinger/conda/envs/ncbi_datasets/bin/datasets"
MATEDB2_LINKS="https://raw.githubusercontent.com/MetazoaPhylogenomicsLab/MATEdb2/main/linksforMATEdb2.txt"
ZENODO_RECORD="13148652"

mkdir -p "${OUTPUT_DIRECTORY}"
LOG_FILE="${OUTPUT_DIRECTORY}/download_log.txt"
TEMP_DIR=$( mktemp -d )
trap 'rm -rf "${TEMP_DIR}"' EXIT

echo "  Downloading ${SPECIES}..."

{
  echo "Species: ${SPECIES}"
  echo "Repository: ${REPOSITORY_URL}"
  echo "NCBI Accession: ${NCBI_ACCESSION}"
  echo "Note: Also known as Hypsibius exemplaris in NCBI"
  echo "Date: $( date )"
  echo ""
} > "${LOG_FILE}"

PROTEIN_FOUND=false

# ============================================================
# STRATEGY 1: Try MATEdb2 (Zenodo) - brief attempt
# ============================================================
echo "  Trying MATEdb2 Zenodo..." >> "${LOG_FILE}"

# Download linksforMATEdb2.txt
wget -q -O "${TEMP_DIR}/linksforMATEdb2.txt" "${MATEDB2_LINKS}" 2>/dev/null || true

# Search for species code (try both dujardini and exemplaris)
CODE=""
if [ -s "${TEMP_DIR}/linksforMATEdb2.txt" ]; then
  CODE=$( grep -i "hypsibius\|dujardini\|exemplaris\|hduj\|hexe" "${TEMP_DIR}/linksforMATEdb2.txt" 2>/dev/null | head -1 | awk '{print $2}' || true )
fi
if [ -z "${CODE}" ]; then
  CODE="HDUJ1"
fi

# Try Zenodo direct download with common MATEdb2 filename patterns
for fname in "${CODE}"_longiso.pep "${CODE}"_longiso.pep.fasta "${CODE}"_longiso.aa "${CODE}"_proteins.faa "${CODE,,}"_longiso.pep; do
  ZENODO_URL="https://zenodo.org/records/${ZENODO_RECORD}/files/${fname}"
  if wget -q -O "${OUTPUT_DIRECTORY}/protein.faa" "${ZENODO_URL}" 2>/dev/null && [ -s "${OUTPUT_DIRECTORY}/protein.faa" ]; then
    echo "Protein source: MATEdb2 Zenodo (${ZENODO_URL})" >> "${LOG_FILE}"
    echo "  Proteome downloaded from MATEdb2 Zenodo"
    PROTEIN_FOUND=true
    break
  fi
done

# ============================================================
# STRATEGY 2: NCBI datasets (fallback)
# ============================================================
if [ "${PROTEIN_FOUND}" = false ]; then
  echo "  MATEdb2 not available for ${SPECIES}, trying NCBI ${NCBI_ACCESSION}..."
  echo "MATEdb2: not found for this species" >> "${LOG_FILE}"
  echo "Trying NCBI: ${NCBI_ACCESSION} (Hypsibius exemplaris)" >> "${LOG_FILE}"

  if [ -x "${NCBI_DATASETS}" ]; then
    # Download genome package with protein annotations and genome
    "${NCBI_DATASETS}" download genome accession "${NCBI_ACCESSION}" \
      --include genome,gff3,protein \
      --filename "${TEMP_DIR}/ncbi_dataset.zip" 2>> "${LOG_FILE}" || true

    if [ -s "${TEMP_DIR}/ncbi_dataset.zip" ]; then
      unzip -q -o "${TEMP_DIR}/ncbi_dataset.zip" -d "${TEMP_DIR}/ncbi_data" 2>/dev/null || true

      # Find protein file in NCBI datasets output
      NCBI_PROTEIN=$( find "${TEMP_DIR}/ncbi_data" -type f -name "protein.faa" 2>/dev/null | head -1 )
      if [ -z "${NCBI_PROTEIN}" ]; then
        NCBI_PROTEIN=$( find "${TEMP_DIR}/ncbi_data" -type f \( -name "*.faa" -o -name "*protein*" \) 2>/dev/null | head -1 )
      fi

      if [ -n "${NCBI_PROTEIN}" ] && [ -s "${NCBI_PROTEIN}" ]; then
        cp "${NCBI_PROTEIN}" "${OUTPUT_DIRECTORY}/protein.faa"
        echo "Protein source: NCBI datasets ${NCBI_ACCESSION} (Hypsibius exemplaris)" >> "${LOG_FILE}"
        echo "Protein file: ${NCBI_PROTEIN}" >> "${LOG_FILE}"
        echo "  Proteome downloaded from NCBI (${NCBI_ACCESSION}, Hypsibius exemplaris)"
        PROTEIN_FOUND=true
      else
        echo "  NCBI download succeeded but no protein file found in package"
        echo "NCBI: downloaded but no protein.faa found" >> "${LOG_FILE}"
        # Try to get genome at least
        NCBI_GENOME=$( find "${TEMP_DIR}/ncbi_data" -type f -name "*.fna" 2>/dev/null | head -1 )
        if [ -n "${NCBI_GENOME}" ] && [ -s "${NCBI_GENOME}" ]; then
          cp "${NCBI_GENOME}" "${OUTPUT_DIRECTORY}/genome.fasta"
          echo "Genome source: NCBI datasets ${NCBI_ACCESSION}" >> "${LOG_FILE}"
          echo "  Genome downloaded from NCBI (no protein available)"
        fi
        echo "=== NCBI package contents ===" >> "${LOG_FILE}"
        find "${TEMP_DIR}/ncbi_data" -type f | head -20 >> "${LOG_FILE}"
        echo "=== End NCBI contents ===" >> "${LOG_FILE}"
      fi
    else
      echo "  NCBI datasets download failed or empty"
      echo "NCBI: download failed" >> "${LOG_FILE}"
    fi
  else
    echo "  WARNING: NCBI datasets tool not found at ${NCBI_DATASETS}"
    echo "NCBI: datasets tool not found at ${NCBI_DATASETS}" >> "${LOG_FILE}"
  fi
fi

# ============================================================
# Result
# ============================================================
if [ "${PROTEIN_FOUND}" = true ] && [ -s "${OUTPUT_DIRECTORY}/protein.faa" ]; then
  PROTEIN_SEQS=$( grep -c "^>" "${OUTPUT_DIRECTORY}/protein.faa" || echo "0" )
  echo "Protein sequences: ${PROTEIN_SEQS}" >> "${LOG_FILE}"
  echo "  ${SPECIES}: ${PROTEIN_SEQS} protein sequences"
else
  echo "  WARNING: Could not find protein for ${SPECIES} from MATEdb2 or NCBI"
  echo "  Tried: MATEdb2 Zenodo ${ZENODO_RECORD}, NCBI ${NCBI_ACCESSION}"
  echo "  Genome may be available - check output directory"
  echo "Protein: not found" >> "${LOG_FILE}"
  # Don't fail - genome-only is OK
fi

echo "  Download log: ${LOG_FILE}"
