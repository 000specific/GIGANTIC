#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 05 | Purpose: One-click phylonames workflow execution
# Human: Eric Edsinger

################################################################################
# GIGANTIC Phylonames Workflow - RUN Script
################################################################################
#
# PURPOSE:
# This script runs the complete phylonames workflow with a single command.
# It downloads NCBI taxonomy, generates all phylonames, and creates your
# project-specific species mapping.
#
# USAGE:
#   bash RUN_phylonames.sh
#
# BEFORE RUNNING:
# 1. Edit INPUT_user/species_list.txt with your species (one per line)
# 2. Optionally edit phylonames_config.yaml if you need custom settings
#
# WHAT THIS SCRIPT DOES:
# 1. Downloads the latest NCBI taxonomy database (~2GB, takes a few minutes)
# 2. Generates phylonames for all NCBI species (~5-10 minutes)
# 3. Creates your project-specific mapping file
#
# OUTPUT:
# Your mapping file will be at (relative to subproject root):
#   output_to_input/maps/project_map-genus_species_X_phylonames.tsv
#
# Script outputs for transparency (in this workflow directory):
#   output/1-output/ - NCBI database download logs
#   output/2-output/ - Generated phylonames and master mapping
#   output/3-output/ - (empty - script 003 writes to output_to_input/)
#
# FOR HPC/SLURM USERS:
# If running on an HPC cluster, you may want to submit this as a job.
# Uncomment the SBATCH lines below and submit with: sbatch RUN_phylonames.sh
#
################################################################################

# Uncomment these lines for SLURM submission:
# #SBATCH --job-name=phylonames
# #SBATCH --account=YOUR_ACCOUNT
# #SBATCH --qos=YOUR_QOS
# #SBATCH --nodes=1
# #SBATCH --ntasks=1
# #SBATCH --cpus-per-task=2
# #SBATCH --mem=8gb
# #SBATCH --time=2:00:00
# #SBATCH --output=phylonames-%j.log

################################################################################
# CONFIGURATION
################################################################################

# Project name (used in output file naming)
# Edit this to match your project:
PROJECT_NAME="my_project"

# Species list file (relative to this directory)
# Edit this file with your species before running:
SPECIES_LIST="INPUT_user/species_list.txt"

# Output location for your mapping file:
# Note: output_to_input/ is at the subproject root (parent of this workflow directory)
OUTPUT_MAP="../output_to_input/maps/${PROJECT_NAME}_map-genus_species_X_phylonames.tsv"

################################################################################
# SCRIPT EXECUTION
################################################################################

echo "========================================================================"
echo "GIGANTIC Phylonames Workflow"
echo "========================================================================"
echo ""
echo "Project: ${PROJECT_NAME}"
echo "Species list: ${SPECIES_LIST}"
echo "Started: $(date)"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# Verify species list exists
if [ ! -f "${SPECIES_LIST}" ]; then
    echo "ERROR: Species list not found: ${SPECIES_LIST}"
    echo ""
    echo "Please create this file with your species, one per line."
    echo "Example:"
    echo "  Homo_sapiens"
    echo "  Aplysia_californica"
    echo "  Octopus_bimaculoides"
    echo ""
    exit 1
fi

echo "Species in your list:"
grep -v "^#" "${SPECIES_LIST}" | grep -v "^$" | head -10
SPECIES_COUNT=$(grep -v "^#" "${SPECIES_LIST}" | grep -v "^$" | wc -l)
echo "... (${SPECIES_COUNT} species total)"
echo ""

# Step 1: Download NCBI taxonomy (if not already downloaded)
echo "========================================================================"
echo "Step 1: Checking NCBI taxonomy database..."
echo "========================================================================"
if [ -L "database-ncbi_taxonomy_latest" ] || ls -d database-ncbi_taxonomy_* 1> /dev/null 2>&1; then
    echo "NCBI taxonomy database already exists. Skipping download."
    echo "To force re-download, delete the database-ncbi_taxonomy_* directories."
else
    echo "Downloading NCBI taxonomy database..."
    echo "This may take a few minutes depending on your connection speed."
    bash ai_scripts/001_ai-bash-download_ncbi_taxonomy.sh
    if [ $? -ne 0 ]; then
        echo "ERROR: NCBI taxonomy download failed!"
        exit 1
    fi
fi
echo ""

# Step 2: Generate all phylonames
echo "========================================================================"
echo "Step 2: Generating phylonames from NCBI taxonomy..."
echo "========================================================================"
echo "This may take 5-10 minutes for the full NCBI database."
python3 ai_scripts/002_ai-python-generate_phylonames.py
if [ $? -ne 0 ]; then
    echo "ERROR: Phyloname generation failed!"
    exit 1
fi
echo ""

# Step 3: Create project-specific mapping
echo "========================================================================"
echo "Step 3: Creating your project-specific species mapping..."
echo "========================================================================"
mkdir -p "$(dirname ${OUTPUT_MAP})"
python3 ai_scripts/003_ai-python-create_species_mapping.py \
    --species-list "${SPECIES_LIST}" \
    --master-mapping "output/2-output/map-phyloname_X_ncbi_taxonomy_info.tsv" \
    --output "${OUTPUT_MAP}"
if [ $? -ne 0 ]; then
    echo "ERROR: Species mapping failed!"
    echo "Check that your species names are spelled correctly (Genus_species format)."
    exit 1
fi
echo ""

# Success!
echo "========================================================================"
echo "SUCCESS! Phylonames workflow complete."
echo "========================================================================"
echo ""
echo "Your mapping file is at:"
echo "  ${OUTPUT_MAP}"
echo ""
echo "This file maps your species to their full phylonames."
echo "Other GIGANTIC subprojects will use this file."
echo ""
echo "Next steps:"
echo "  1. Copy ${OUTPUT_MAP} to your genomesDB subproject"
echo "  2. Set up your proteome database using the phylonames for file naming"
echo ""
echo "Completed: $(date)"
echo "========================================================================"
