#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Download Mnemiopsis leidyi data from NHGRI Mnemiopsis Genome Project
# Human: Eric Edsinger

# Direct file URLs (CGI download pages return HTML, not FASTA).
# Genome: MlScaffold09.nt.gz (gzipped nucleotide scaffolds)
# Protein: ML2.2.aa.gz (gzipped amino acid gene models)
# No annotation file available.
# Outputs: genome.fasta, protein.faa, download_log.txt (no annotation.gff3)

set -euo pipefail

OUTPUT_DIRECTORY="$1"
REPOSITORY_URL="$2"
GENOME_URL="${3:-}"
ANNOTATION_URL="${4:-}"
PROTEIN_URL="${5:-}"

SPECIES="Mnemiopsis_leidyi"
DIRECT_GENOME_URL="https://research.nhgri.nih.gov/mnemiopsis/download/genome/MlScaffold09.nt.gz"
DIRECT_PROTEIN_URL="https://research.nhgri.nih.gov/mnemiopsis/download/proteome/ML2.2.aa.gz"

mkdir -p "${OUTPUT_DIRECTORY}"
LOG_FILE="${OUTPUT_DIRECTORY}/download_log.txt"

echo "  Downloading ${SPECIES}..."

{
  echo "Species: ${SPECIES}"
  echo "Repository: ${REPOSITORY_URL}"
  echo "Note: Using direct file URLs (CGI pages return HTML, not data)"
  echo "Genome direct URL: ${DIRECT_GENOME_URL}"
  echo "Protein direct URL: ${DIRECT_PROTEIN_URL}"
  echo "Date: $( date )"
  echo ""
} > "${LOG_FILE}"

# Genome: gzipped FASTA - download, gunzip, rename
echo "  Downloading genome (gzipped)..."
wget -q -O "${OUTPUT_DIRECTORY}/genome.fasta.gz" "${DIRECT_GENOME_URL}"
echo "  Decompressing genome..."
gunzip -f "${OUTPUT_DIRECTORY}/genome.fasta.gz"
echo "Genome URL: ${DIRECT_GENOME_URL}" >> "${LOG_FILE}"

# Annotation: not available for this species
echo "  No annotation available for ${SPECIES}"
echo "Annotation: not available" >> "${LOG_FILE}"

# Protein: gzipped amino acid file - download, gunzip, rename
echo "  Downloading protein (gzipped)..."
wget -q -O "${OUTPUT_DIRECTORY}/protein.faa.gz" "${DIRECT_PROTEIN_URL}"
echo "  Decompressing protein..."
gunzip -f "${OUTPUT_DIRECTORY}/protein.faa.gz"
echo "Protein URL: ${DIRECT_PROTEIN_URL}" >> "${LOG_FILE}"

echo "  Download log: ${LOG_FILE}"
