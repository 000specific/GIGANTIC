#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 05 | Purpose: Download NCBI taxonomy database with versioning
# Human: Eric Edsinger

################################################################################
# SCRIPT PURPOSE (For Non-Programmers):
# ----------------------------------------------------------------------------
# This script downloads the NCBI taxonomy database from the internet.
# The NCBI (National Center for Biotechnology Information) maintains a
# comprehensive database of all known species and their taxonomic relationships.
#
# WHAT IT DOES:
# 1. Creates a versioned directory with current date and time
# 2. Downloads the NCBI "new_taxdump" archive
# 3. Extracts the taxonomy files
# 4. Records metadata (date, checksums) for reproducibility
#
# THE DATA: Contains classification information for millions of species:
# - Kingdom, Phylum, Class, Order, Family, Genus, Species
# - Taxonomic IDs (unique numbers for each organism)
# - Alternative names and synonyms
#
# VERSION TRACKING: Each download creates a unique directory:
#   database-ncbi_taxonomy_20260205_143052/
# This ensures you can trace exactly which taxonomy version was used.
################################################################################

################################################################################
# TECHNICAL NOTES (For Python/CS Experts):
# ----------------------------------------------------------------------------
# - Uses wget for reliable FTP downloads with retry logic
# - Creates timestamped directories for version tracking
# - Records MD5 checksums for file integrity verification
# - Downloads to current working directory by default
# - The rankedlineage.dmp file is the primary input for phyloname generation
################################################################################

set -e  # Exit on any error

# Configuration
NCBI_FTP_URL="ftp://ftp.ncbi.nih.gov/pub/taxonomy/new_taxdump/new_taxdump.tar.gz"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
DATABASE_DIR="database-ncbi_taxonomy_${TIMESTAMP}"
METADATA_FILE="${DATABASE_DIR}/download_metadata.txt"

echo "============================================================"
echo "NCBI Taxonomy Download Script"
echo "============================================================"
echo ""
echo "Timestamp (UTC): ${TIMESTAMP}"
echo "Target directory: ${DATABASE_DIR}"
echo ""

# Create versioned database directory
echo "Creating database directory..."
mkdir -p "${DATABASE_DIR}"

# Change to database directory
cd "${DATABASE_DIR}"

# Record download metadata
echo "Recording metadata..."
cat > "download_metadata.txt" << EOF
NCBI Taxonomy Database Download Metadata
========================================
Download timestamp (UTC): $(date -u +"%Y-%m-%d %H:%M:%S")
Download timestamp (local): $(date +"%Y-%m-%d %H:%M:%S %Z")
Source URL: ${NCBI_FTP_URL}
Target directory: ${DATABASE_DIR}
Downloaded by: GIGANTIC phylonames subproject
Script: 001_ai-bash-download_ncbi_taxonomy.sh
EOF

# Download the taxonomy archive
echo ""
echo "Downloading NCBI taxonomy database..."
echo "Source: ${NCBI_FTP_URL}"
echo "This may take a few minutes depending on connection speed..."
echo ""

# Use wget with retry logic for reliable FTP downloads
wget --tries=3 \
     --waitretry=10 \
     --timeout=60 \
     --progress=bar:force \
     "${NCBI_FTP_URL}" \
     -O new_taxdump.tar.gz

# Record download checksum
echo ""
echo "Recording checksums..."
md5sum new_taxdump.tar.gz >> download_metadata.txt
echo "" >> download_metadata.txt

# Extract the archive
echo ""
echo "Extracting taxonomy files..."
tar -xzf new_taxdump.tar.gz

# Record extracted file sizes
echo "Extracted files:" >> download_metadata.txt
ls -lh *.dmp >> download_metadata.txt 2>/dev/null || echo "No .dmp files found" >> download_metadata.txt

# Verify critical file exists
if [ ! -f "rankedlineage.dmp" ]; then
    echo "ERROR: rankedlineage.dmp not found after extraction!"
    echo "This file is required for phyloname generation."
    exit 1
fi

# Clean up archive to save space (optional - comment out to keep)
echo ""
echo "Cleaning up archive..."
rm -f new_taxdump.tar.gz

# Return to original directory
cd ..

# Create symlink to latest database
echo ""
echo "Creating symlink to latest database..."
rm -f database-ncbi_taxonomy_latest
ln -s "${DATABASE_DIR}" database-ncbi_taxonomy_latest

# Summary
echo ""
echo "============================================================"
echo "Download Complete!"
echo "============================================================"
echo ""
echo "Database directory: ${DATABASE_DIR}"
echo "Symlink created: database-ncbi_taxonomy_latest -> ${DATABASE_DIR}"
echo ""
echo "Key files downloaded:"
ls -lh "${DATABASE_DIR}"/*.dmp 2>/dev/null | head -5
echo ""
echo "Metadata recorded in: ${DATABASE_DIR}/download_metadata.txt"
echo ""
echo "Next step: Run 002_ai-python-generate_phylonames.py"
echo "============================================================"
