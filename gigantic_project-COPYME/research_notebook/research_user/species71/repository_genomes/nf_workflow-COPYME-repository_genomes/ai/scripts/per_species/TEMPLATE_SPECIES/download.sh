#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 12 | Purpose: TEMPLATE per-species download script for repository genomes
# Human: Eric Edsinger

# =============================================================================
# TEMPLATE per-species download script
#
# Copy this directory to create a download script for a new species:
#   cp -r per_species/TEMPLATE_SPECIES per_species/Genus_species
#   Then edit per_species/Genus_species/download.sh
#
# This script is called by 001_ai-bash-download_repository_genomes.sh with:
#   bash download.sh <output_dir> <repository_url> <genome_url> <annotation_url> <protein_url>
#
# Arguments:
#   $1 = output_dir      - Where to put downloaded files (1-output/Genus_species/)
#   $2 = repository_url  - Main repository webpage URL
#   $3 = genome_url      - Direct URL to genome FASTA (may be empty)
#   $4 = annotation_url  - Direct URL to GFF3/GTF (may be empty)
#   $5 = protein_url     - Direct URL to protein FASTA (may be empty)
#
# Expected output files (create whichever are available):
#   ${output_dir}/genome.fasta      - Genome assembly
#   ${output_dir}/annotation.gff3   - GFF3 annotation (preferred)
#   ${output_dir}/annotation.gtf    - GTF annotation (if GFF3 not available)
#   ${output_dir}/protein.faa       - Protein sequences (if available)
#   ${output_dir}/download_log.txt  - Log of what was downloaded and from where
#
# If annotation or protein files are not publicly available, just download
# what you can. The pipeline will handle missing files gracefully.
# =============================================================================

set -euo pipefail

OUTPUT_DIRECTORY="$1"
REPOSITORY_URL="$2"
GENOME_URL="${3:-}"
ANNOTATION_URL="${4:-}"
PROTEIN_URL="${5:-}"

echo "  Downloading TEMPLATE_SPECIES..."

# Start download log
LOG_FILE="${OUTPUT_DIRECTORY}/download_log.txt"
echo "Species: TEMPLATE_SPECIES" > "${LOG_FILE}"
echo "Repository: ${REPOSITORY_URL}" >> "${LOG_FILE}"
echo "Date: $(date)" >> "${LOG_FILE}"
echo "" >> "${LOG_FILE}"

# Download genome
if [ -n "${GENOME_URL}" ]; then
    echo "  Downloading genome from: ${GENOME_URL}"
    echo "Genome URL: ${GENOME_URL}" >> "${LOG_FILE}"
    # wget -q -O "${OUTPUT_DIRECTORY}/genome.fasta.gz" "${GENOME_URL}"
    # gunzip "${OUTPUT_DIRECTORY}/genome.fasta.gz"
    echo "  TODO: Implement genome download"
else
    echo "  No genome URL provided"
    echo "Genome: not available" >> "${LOG_FILE}"
fi

# Download annotation
if [ -n "${ANNOTATION_URL}" ]; then
    echo "  Downloading annotation from: ${ANNOTATION_URL}"
    echo "Annotation URL: ${ANNOTATION_URL}" >> "${LOG_FILE}"
    # wget -q -O "${OUTPUT_DIRECTORY}/annotation.gff3.gz" "${ANNOTATION_URL}"
    # gunzip "${OUTPUT_DIRECTORY}/annotation.gff3.gz"
    echo "  TODO: Implement annotation download"
else
    echo "  No annotation URL provided"
    echo "Annotation: not available" >> "${LOG_FILE}"
fi

# Download protein
if [ -n "${PROTEIN_URL}" ]; then
    echo "  Downloading protein from: ${PROTEIN_URL}"
    echo "Protein URL: ${PROTEIN_URL}" >> "${LOG_FILE}"
    # wget -q -O "${OUTPUT_DIRECTORY}/protein.faa.gz" "${PROTEIN_URL}"
    # gunzip "${OUTPUT_DIRECTORY}/protein.faa.gz"
    echo "  TODO: Implement protein download"
else
    echo "  No protein URL provided"
    echo "Protein: not available" >> "${LOG_FILE}"
fi

echo "  Download log: ${LOG_FILE}"
