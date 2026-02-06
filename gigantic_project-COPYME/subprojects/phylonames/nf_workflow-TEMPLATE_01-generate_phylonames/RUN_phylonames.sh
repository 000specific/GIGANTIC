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
#   (This is a symlink pointing to the actual file in output/3-output/)
#
# Script outputs for transparency (in this workflow directory):
#   output/1-output/ - NCBI database download logs
#   output/2-output/ - Generated phylonames and master mapping
#   output/3-output/ - Project-specific mapping file (actual data)
#
# SYMLINK PATTERN:
# To avoid data duplication, output_to_input/ contains symlinks pointing to
# the actual files in output/3-output/. This allows downstream subprojects
# to access the data while keeping the canonical copy in the workflow output.
# For archiving, use `cp -L` or `rsync -L` to dereference symlinks.
#
# FOR HPC/SLURM USERS:
# Use the SLURM wrapper script instead:
#   sbatch SLURM_phylonames.sbatch
#
################################################################################

################################################################################
# CONFIGURATION
################################################################################

# Project name (used in output file naming)
# Edit this to match your project:
PROJECT_NAME="my_project"

# Species list file (relative to this directory)
# Edit this file with your species before running:
SPECIES_LIST="INPUT_user/species_list.txt"

# Output locations:
# Actual file is in output/3-output/ (workflow directory)
# Symlink is created in output_to_input/maps/ (subproject root) for downstream access
OUTPUT_FILE="output/3-output/${PROJECT_NAME}_map-genus_species_X_phylonames.tsv"
OUTPUT_LINK="../output_to_input/maps/${PROJECT_NAME}_map-genus_species_X_phylonames.tsv"

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

# Create output directories
mkdir -p "output/3-output"
mkdir -p "$(dirname ${OUTPUT_LINK})"

# Write actual file to output/3-output/
python3 ai_scripts/003_ai-python-create_species_mapping.py \
    --species-list "${SPECIES_LIST}" \
    --master-mapping "output/2-output/map-phyloname_X_ncbi_taxonomy_info.tsv" \
    --output "${OUTPUT_FILE}"
if [ $? -ne 0 ]; then
    echo "ERROR: Species mapping failed!"
    echo "Check that your species names are spelled correctly (Genus_species format)."
    exit 1
fi

# Create symlink in output_to_input/maps/ pointing to the actual file
# Use relative path from output_to_input/maps/ to the workflow output/3-output/
# Path: ../nf_workflow-TEMPLATE_01-generate_phylonames/output/3-output/filename
WORKFLOW_DIR_NAME=$(basename "${SCRIPT_DIR}")
RELATIVE_TARGET="../../${WORKFLOW_DIR_NAME}/output/3-output/${PROJECT_NAME}_map-genus_species_X_phylonames.tsv"

# Remove existing symlink if present (for re-runs)
rm -f "${OUTPUT_LINK}"

# Create the symlink
ln -s "${RELATIVE_TARGET}" "${OUTPUT_LINK}"
if [ $? -ne 0 ]; then
    echo "WARNING: Could not create symlink at ${OUTPUT_LINK}"
    echo "Copying file instead..."
    cp "${OUTPUT_FILE}" "${OUTPUT_LINK}"
fi

echo "Actual file: ${OUTPUT_FILE}"
echo "Symlink: ${OUTPUT_LINK}"
echo ""

# Success!
echo "========================================================================"
echo "SUCCESS! Phylonames workflow complete."
echo "========================================================================"
echo ""
echo "Your mapping file:"
echo "  Actual file: ${OUTPUT_FILE}"
echo "  Symlink:     ${OUTPUT_LINK}"
echo ""
echo "This file maps your species to their full phylonames."
echo "Other GIGANTIC subprojects will use the symlink in output_to_input/."
echo ""
echo "Next steps:"
echo "  1. Other subprojects can read from ${OUTPUT_LINK}"
echo "  2. Set up your proteome database using the phylonames for file naming"
echo ""
echo "Archiving note:"
echo "  Use 'cp -L' or 'rsync -L' to dereference symlinks when archiving."
echo ""
echo "Completed: $(date)"
echo "========================================================================"
