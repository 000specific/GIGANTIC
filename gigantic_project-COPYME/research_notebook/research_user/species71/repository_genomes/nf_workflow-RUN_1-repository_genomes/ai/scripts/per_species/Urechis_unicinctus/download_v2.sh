#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Download Urechis unicinctus data from Dryad (direct file_stream URLs)
# Human: Eric Edsinger

# Dryad dataset: https://datadryad.org/stash/dataset/doi:10.5061/dryad.brv15dvhv
# Direct download URLs provided by user (file_stream format bypasses 403 blocks)
# Genome: https://datadryad.org/downloads/file_stream/3240525
# GFF: https://datadryad.org/downloads/file_stream/3240526
# Proteome: https://datadryad.org/downloads/file_stream/3240524
# Outputs: genome.fasta, annotation.gff3, protein.faa, download_log.txt

set -euo pipefail

OUTPUT_DIRECTORY="$1"
REPOSITORY_URL="${2:-https://datadryad.org/stash/dataset/doi:10.5061/dryad.brv15dvhv}"

SPECIES="Urechis_unicinctus"

DIRECT_GENOME_URL="https://datadryad.org/downloads/file_stream/3240525"
DIRECT_GFF_URL="https://datadryad.org/downloads/file_stream/3240526"
DIRECT_PROTEIN_URL="https://datadryad.org/downloads/file_stream/3240524"

mkdir -p "${OUTPUT_DIRECTORY}"
LOG_FILE="${OUTPUT_DIRECTORY}/download_log.txt"

echo "  Downloading ${SPECIES} (v2 - direct Dryad file_stream URLs)..."

{
    echo "Species: ${SPECIES}"
    echo "Repository: ${REPOSITORY_URL}"
    echo "Source: Dryad doi:10.5061/dryad.brv15dvhv (direct file_stream URLs)"
    echo "Genome URL: ${DIRECT_GENOME_URL}"
    echo "GFF URL: ${DIRECT_GFF_URL}"
    echo "Protein URL: ${DIRECT_PROTEIN_URL}"
    echo "Date: $( date )"
    echo ""
} > "${LOG_FILE}"

# Genome
echo "  Downloading genome..."
wget -q -L --no-check-certificate -O "${OUTPUT_DIRECTORY}/genome.fasta.tmp" "${DIRECT_GENOME_URL}" 2>/dev/null
if [ -s "${OUTPUT_DIRECTORY}/genome.fasta.tmp" ]; then
    # Check if gzipped
    if file "${OUTPUT_DIRECTORY}/genome.fasta.tmp" | grep -q "gzip"; then
        mv "${OUTPUT_DIRECTORY}/genome.fasta.tmp" "${OUTPUT_DIRECTORY}/genome.fasta.gz"
        gunzip -f "${OUTPUT_DIRECTORY}/genome.fasta.gz"
        echo "Genome: downloaded and decompressed" >> "${LOG_FILE}"
    else
        mv "${OUTPUT_DIRECTORY}/genome.fasta.tmp" "${OUTPUT_DIRECTORY}/genome.fasta"
        echo "Genome: downloaded successfully" >> "${LOG_FILE}"
    fi
    SCAFFOLD_COUNT=$( grep -c '^>' "${OUTPUT_DIRECTORY}/genome.fasta" 2>/dev/null || echo "0" )
    echo "  Genome: ${SCAFFOLD_COUNT} scaffolds"
    echo "Genome scaffolds: ${SCAFFOLD_COUNT}" >> "${LOG_FILE}"
else
    echo "  WARNING: Genome download failed or empty"
    echo "Genome: download failed" >> "${LOG_FILE}"
    rm -f "${OUTPUT_DIRECTORY}/genome.fasta.tmp"
fi

# GFF annotation
echo "  Downloading annotation..."
wget -q -L --no-check-certificate -O "${OUTPUT_DIRECTORY}/annotation.gff3.tmp" "${DIRECT_GFF_URL}" 2>/dev/null
if [ -s "${OUTPUT_DIRECTORY}/annotation.gff3.tmp" ]; then
    if file "${OUTPUT_DIRECTORY}/annotation.gff3.tmp" | grep -q "gzip"; then
        mv "${OUTPUT_DIRECTORY}/annotation.gff3.tmp" "${OUTPUT_DIRECTORY}/annotation.gff3.gz"
        gunzip -f "${OUTPUT_DIRECTORY}/annotation.gff3.gz"
        echo "Annotation: downloaded and decompressed" >> "${LOG_FILE}"
    else
        mv "${OUTPUT_DIRECTORY}/annotation.gff3.tmp" "${OUTPUT_DIRECTORY}/annotation.gff3"
        echo "Annotation: downloaded successfully" >> "${LOG_FILE}"
    fi
    echo "  Annotation downloaded"
else
    echo "  WARNING: Annotation download failed or empty"
    echo "Annotation: download failed" >> "${LOG_FILE}"
    rm -f "${OUTPUT_DIRECTORY}/annotation.gff3.tmp"
fi

# Proteome
echo "  Downloading protein..."
wget -q -L --no-check-certificate -O "${OUTPUT_DIRECTORY}/protein.faa.tmp" "${DIRECT_PROTEIN_URL}" 2>/dev/null
if [ -s "${OUTPUT_DIRECTORY}/protein.faa.tmp" ]; then
    if file "${OUTPUT_DIRECTORY}/protein.faa.tmp" | grep -q "gzip"; then
        mv "${OUTPUT_DIRECTORY}/protein.faa.tmp" "${OUTPUT_DIRECTORY}/protein.faa.gz"
        gunzip -f "${OUTPUT_DIRECTORY}/protein.faa.gz"
        echo "Protein: downloaded and decompressed" >> "${LOG_FILE}"
    else
        mv "${OUTPUT_DIRECTORY}/protein.faa.tmp" "${OUTPUT_DIRECTORY}/protein.faa"
        echo "Protein: downloaded successfully" >> "${LOG_FILE}"
    fi
    PROTEIN_COUNT=$( grep -c '^>' "${OUTPUT_DIRECTORY}/protein.faa" 2>/dev/null || echo "0" )
    echo "  Protein: ${PROTEIN_COUNT} sequences"
    echo "Protein sequences: ${PROTEIN_COUNT}" >> "${LOG_FILE}"
else
    echo "  WARNING: Protein download failed or empty"
    echo "Protein: download failed" >> "${LOG_FILE}"
    rm -f "${OUTPUT_DIRECTORY}/protein.faa.tmp"
fi

echo "  Download log: ${LOG_FILE}"
