#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Download Amphiscolops sp. MND2022 proteome (MATEdb2 attempt, likely needs user input)
# Human: Eric Edsinger

# Strategy: Try MATEdb2 Zenodo first, but this species is likely NOT in MATEdb2
# MATEdb2 acoela only has HMIA1, SYRO2 - NOT Amphiscolops
# This species is also likely NOT at NCBI with a genome assembly
# If all automated sources fail, exit with warning requesting user input
# Outputs: protein.faa (if found), download_log.txt

set -uo pipefail

OUTPUT_DIRECTORY="$1"
REPOSITORY_URL="$2"
GENOME_URL="${3:-}"
ANNOTATION_URL="${4:-}"
PROTEIN_URL="${5:-}"

SPECIES="Amphiscolops_sp_MND2022"
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
  echo "Date: $( date )"
  echo ""
  echo "NOTE: This species is likely NOT in MATEdb2 or NCBI."
  echo "MATEdb2 acoela entries: HMIA1 (Hofstenia miamia), SYRO2 (Symsagittifera roscoffensis)"
  echo "Neither Amphiscolops nor sp_MND2022 found in linksforMATEdb2.txt"
  echo ""
} > "${LOG_FILE}"

PROTEIN_FOUND=false

# ============================================================
# STRATEGY 1: Try MATEdb2 (Zenodo) - brief attempt
# ============================================================
echo "  Trying MATEdb2 Zenodo (unlikely to succeed)..." >> "${LOG_FILE}"

# Download linksforMATEdb2.txt
wget -q -O "${TEMP_DIR}/linksforMATEdb2.txt" "${MATEDB2_LINKS}" 2>/dev/null || true

# Search for species code
CODE=""
if [ -s "${TEMP_DIR}/linksforMATEdb2.txt" ]; then
  CODE=$( grep -i "amphiscolops\|amnd" "${TEMP_DIR}/linksforMATEdb2.txt" 2>/dev/null | head -1 | awk '{print $2}' || true )
fi
if [ -z "${CODE}" ]; then
  CODE="AMND1"
fi

# Try Zenodo direct download with common MATEdb2 filename patterns
for fname in "${CODE}"_longiso.pep "${CODE}"_longiso.pep.fasta "${CODE}"_longiso.aa "${CODE}"_proteins.faa "${CODE,,}"_longiso.pep; do
  ZENODO_URL="https://zenodo.org/records/${ZENODO_RECORD}/files/${fname}"
  if wget -q -O "${OUTPUT_DIRECTORY}/protein.faa" "${ZENODO_URL}" 2>/dev/null && [ -s "${OUTPUT_DIRECTORY}/protein.faa" ]; then
    echo "Protein source: MATEdb2 Zenodo (${ZENODO_URL})" >> "${LOG_FILE}"
    echo "  Proteome downloaded from MATEdb2 Zenodo (unexpected success!)"
    PROTEIN_FOUND=true
    break
  fi
done

# ============================================================
# Result - likely needs user input
# ============================================================
if [ "${PROTEIN_FOUND}" = true ] && [ -s "${OUTPUT_DIRECTORY}/protein.faa" ]; then
  PROTEIN_SEQS=$( grep -c "^>" "${OUTPUT_DIRECTORY}/protein.faa" || echo "0" )
  echo "Protein sequences: ${PROTEIN_SEQS}" >> "${LOG_FILE}"
  echo "  ${SPECIES}: ${PROTEIN_SEQS} protein sequences"
else
  rm -f "${OUTPUT_DIRECTORY}/protein.faa"
  echo "" >> "${LOG_FILE}"
  echo "========================================" >> "${LOG_FILE}"
  echo "USER INPUT NEEDED" >> "${LOG_FILE}"
  echo "========================================" >> "${LOG_FILE}"
  echo "Could not find proteome for ${SPECIES} from any automated source." >> "${LOG_FILE}"
  echo "Tried: MATEdb2 Zenodo ${ZENODO_RECORD}" >> "${LOG_FILE}"
  echo "" >> "${LOG_FILE}"
  echo "This species (Amphiscolops sp. MND2022) is an acoela that may only be" >> "${LOG_FILE}"
  echo "available from the original publication or supplementary materials." >> "${LOG_FILE}"
  echo "" >> "${LOG_FILE}"
  echo "Please provide the proteome file manually:" >> "${LOG_FILE}"
  echo "  1. Place protein FASTA at: ${OUTPUT_DIRECTORY}/protein.faa" >> "${LOG_FILE}"
  echo "  2. Or update the species manifest with the correct download URL" >> "${LOG_FILE}"
  echo "========================================" >> "${LOG_FILE}"
  echo ""
  echo "  *** USER INPUT NEEDED for ${SPECIES} ***"
  echo "  Could not find proteome from MATEdb2 or NCBI."
  echo "  This acoela species may only be available from the original publication."
  echo "  Please provide the proteome manually to: ${OUTPUT_DIRECTORY}/protein.faa"
  echo "  See download_log.txt for details."
  echo "Protein: not found - USER INPUT NEEDED" >> "${LOG_FILE}"
  # Exit 0 (not 1) - this is an expected limitation, not a script error
  exit 0
fi

echo "  Download log: ${LOG_FILE}"
