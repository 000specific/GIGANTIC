#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Download Styela plicata data from Zenodo/MATEdb2
# Human: Eric Edsinger

# Zenodo record: https://zenodo.org/records/13148652
# Direct download URLs provided by user
# NOTE: User's table had genome/GFF columns swapped - using correct extensions:
#   .fasta = genome, .gtf = annotation, .faa = protein
# Genome: https://zenodo.org/records/13148652/files/Styela_plicata.fasta?download=1
# GTF: https://zenodo.org/records/13148652/files/Styela_plicata.gtf?download=1
# Proteome: https://zenodo.org/records/13148652/files/Styela_plicata.faa?download=1
# Outputs: genome.fasta, annotation.gff3, protein.faa, download_log.txt

set -euo pipefail

OUTPUT_DIRECTORY="$1"
REPOSITORY_URL="${2:-https://zenodo.org/records/13148652}"

SPECIES="Styela_plicata"

# NOTE: Using file extensions to determine correct file types
# (user's spreadsheet had genome and GFF columns swapped for this species)
DIRECT_GENOME_URL="https://zenodo.org/records/13148652/files/Styela_plicata.fasta?download=1"
DIRECT_GTF_URL="https://zenodo.org/records/13148652/files/Styela_plicata.gtf?download=1"
DIRECT_PROTEIN_URL="https://zenodo.org/records/13148652/files/Styela_plicata.faa?download=1"

mkdir -p "${OUTPUT_DIRECTORY}"
LOG_FILE="${OUTPUT_DIRECTORY}/download_log.txt"

echo "  Downloading ${SPECIES} (v2 - Zenodo/MATEdb2 direct URLs)..."

{
    echo "Species: ${SPECIES}"
    echo "Repository: ${REPOSITORY_URL}"
    echo "Source: Zenodo record 13148652 (MATEdb2)"
    echo "Genome URL: ${DIRECT_GENOME_URL}"
    echo "GTF URL: ${DIRECT_GTF_URL}"
    echo "Protein URL: ${DIRECT_PROTEIN_URL}"
    echo "Date: $( date )"
    echo ""
} > "${LOG_FILE}"

# Genome
echo "  Downloading genome..."
wget -q -L -O "${OUTPUT_DIRECTORY}/genome.fasta" "${DIRECT_GENOME_URL}"
if [ -s "${OUTPUT_DIRECTORY}/genome.fasta" ]; then
    if file "${OUTPUT_DIRECTORY}/genome.fasta" | grep -q "gzip"; then
        mv "${OUTPUT_DIRECTORY}/genome.fasta" "${OUTPUT_DIRECTORY}/genome.fasta.gz"
        gunzip -f "${OUTPUT_DIRECTORY}/genome.fasta.gz"
    fi
    SCAFFOLD_COUNT=$( grep -c '^>' "${OUTPUT_DIRECTORY}/genome.fasta" 2>/dev/null || echo "0" )
    echo "  Genome: ${SCAFFOLD_COUNT} scaffolds"
    echo "Genome: downloaded (${SCAFFOLD_COUNT} scaffolds)" >> "${LOG_FILE}"
else
    echo "  WARNING: Genome download failed or empty"
    echo "Genome: download failed" >> "${LOG_FILE}"
fi

# GTF annotation (save as annotation.gff3 for pipeline consistency)
echo "  Downloading annotation (GTF)..."
wget -q -L -O "${OUTPUT_DIRECTORY}/annotation.gff3" "${DIRECT_GTF_URL}"
if [ -s "${OUTPUT_DIRECTORY}/annotation.gff3" ]; then
    if file "${OUTPUT_DIRECTORY}/annotation.gff3" | grep -q "gzip"; then
        mv "${OUTPUT_DIRECTORY}/annotation.gff3" "${OUTPUT_DIRECTORY}/annotation.gff3.gz"
        gunzip -f "${OUTPUT_DIRECTORY}/annotation.gff3.gz"
    fi
    echo "  Annotation downloaded (GTF format, saved as annotation.gff3)"
    echo "Annotation: downloaded (GTF format)" >> "${LOG_FILE}"
else
    echo "  WARNING: Annotation download failed or empty"
    echo "Annotation: download failed" >> "${LOG_FILE}"
fi

# Proteome
echo "  Downloading protein..."
wget -q -L -O "${OUTPUT_DIRECTORY}/protein.faa" "${DIRECT_PROTEIN_URL}"
if [ -s "${OUTPUT_DIRECTORY}/protein.faa" ]; then
    if file "${OUTPUT_DIRECTORY}/protein.faa" | grep -q "gzip"; then
        mv "${OUTPUT_DIRECTORY}/protein.faa" "${OUTPUT_DIRECTORY}/protein.faa.gz"
        gunzip -f "${OUTPUT_DIRECTORY}/protein.faa.gz"
    fi
    PROTEIN_COUNT=$( grep -c '^>' "${OUTPUT_DIRECTORY}/protein.faa" 2>/dev/null || echo "0" )
    echo "  Protein: ${PROTEIN_COUNT} sequences"
    echo "Protein: downloaded (${PROTEIN_COUNT} sequences)" >> "${LOG_FILE}"
else
    echo "  WARNING: Protein download failed or empty"
    echo "Protein: download failed" >> "${LOG_FILE}"
fi

echo "  Download log: ${LOG_FILE}"
