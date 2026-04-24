#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: Download Membranipora membranacea GFF + proteome from Dryad (genome already from NCBI)
# Human: Eric Edsinger

# Dryad dataset: https://datadryad.org/stash/landing/show?id=doi%3A10.5061%2Fdryad.76hdr7t3f
# Direct download URLs provided by user (file_stream format)
# Genome: ALREADY EXISTS from NCBI GCA_914767715.1 (Darwin Tree of Life)
# GFF: https://datadryad.org/downloads/file_stream/3248912
# Proteome: https://datadryad.org/downloads/file_stream/3248910
# Outputs: annotation.gff3, protein.faa, download_log.txt (genome.fasta already present)

set -euo pipefail

OUTPUT_DIRECTORY="$1"
REPOSITORY_URL="${2:-https://datadryad.org/stash/landing/show?id=doi%3A10.5061%2Fdryad.76hdr7t3f}"

SPECIES="Membranipora_membranacea"

DIRECT_GFF_URL="https://datadryad.org/downloads/file_stream/3248912"
DIRECT_PROTEIN_URL="https://datadryad.org/downloads/file_stream/3248910"

mkdir -p "${OUTPUT_DIRECTORY}"
LOG_FILE="${OUTPUT_DIRECTORY}/download_log.txt"

echo "  Downloading ${SPECIES} annotation + protein (v2 - Dryad file_stream URLs)..."
echo "  (genome.fasta already exists from NCBI GCA_914767715.1)"

{
    echo "Species: ${SPECIES}"
    echo "Repository: ${REPOSITORY_URL}"
    echo "Source: Dryad doi:10.5061/dryad.76hdr7t3f (direct file_stream URLs)"
    echo "Genome: already present from NCBI GCA_914767715.1 (Darwin Tree of Life)"
    echo "GFF URL: ${DIRECT_GFF_URL}"
    echo "Protein URL: ${DIRECT_PROTEIN_URL}"
    echo "Date: $( date )"
    echo ""
} >> "${LOG_FILE}"

# Check existing genome
if [ -s "${OUTPUT_DIRECTORY}/genome.fasta" ]; then
    SCAFFOLD_COUNT=$( grep -c '^>' "${OUTPUT_DIRECTORY}/genome.fasta" 2>/dev/null || echo "0" )
    echo "  Genome already present: ${SCAFFOLD_COUNT} scaffolds"
    echo "Genome: already present (${SCAFFOLD_COUNT} scaffolds, NCBI GCA_914767715.1)" >> "${LOG_FILE}"
else
    echo "  WARNING: genome.fasta not found!"
    echo "Genome: NOT FOUND (expected from NCBI download)" >> "${LOG_FILE}"
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
