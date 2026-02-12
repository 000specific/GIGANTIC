#!/bin/bash
# AI: Claude Code | Opus 4.5 | 2026 February 12 | Purpose: Create all GIGANTIC conda environments
# Human: Eric Edsinger

################################################################################
# GIGANTIC Environment Setup Script
################################################################################
#
# PURPOSE:
# Create all conda environments needed for GIGANTIC subprojects.
# Run this ONCE after copying gigantic_project-COPYME to start a new project.
#
# USAGE:
#   bash RUN-setup_environments.sh [OPTIONS]
#
# OPTIONS:
#   --list        List all environments without creating them
#   --env NAME    Create only the specified environment
#   --force       Recreate environments even if they exist
#   --help        Show this help message
#
# REQUIREMENTS:
#   - conda or mamba must be available
#   - On HiPerGator: run "module load conda" first
#
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory (project root)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ENV_DIR="${SCRIPT_DIR}/conda_environments"

# Options
LIST_ONLY=false
SINGLE_ENV=""
FORCE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --list)
            LIST_ONLY=true
            shift
            ;;
        --env)
            SINGLE_ENV="$2"
            shift 2
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help|-h)
            head -30 "$0" | grep -E "^#" | sed 's/^# //' | sed 's/^#//'
            exit 0
            ;;
        *)
            echo -e "${RED}ERROR: Unknown option: $1${NC}"
            echo "Use --help to see available options."
            exit 1
            ;;
    esac
done

echo "========================================================================"
echo "GIGANTIC Environment Setup"
echo "========================================================================"
echo ""

# Check for conda environments directory
if [ ! -d "$ENV_DIR" ]; then
    echo -e "${RED}ERROR: conda_environments/ directory not found!${NC}"
    echo "Expected at: ${ENV_DIR}"
    exit 1
fi

# Try to load conda module (for HPC systems)
module load conda 2>/dev/null || true

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo -e "${RED}ERROR: conda not found!${NC}"
    echo ""
    echo "Please install conda or load it via module:"
    echo "  On HiPerGator: module load conda"
    echo "  Or install: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Check for mamba (faster than conda)
if command -v mamba &> /dev/null; then
    INSTALLER="mamba"
    echo "Using mamba for faster installation"
else
    INSTALLER="conda"
    echo "Using conda (tip: install mamba for faster installation)"
fi
echo ""

# Find all environment files
ENV_FILES=$(find "$ENV_DIR" -name "ai_gigantic_*.yml" -type f | sort)

if [ -z "$ENV_FILES" ]; then
    echo -e "${YELLOW}No environment files found in ${ENV_DIR}${NC}"
    exit 0
fi

# List mode
if $LIST_ONLY; then
    echo "Available GIGANTIC environments:"
    echo ""
    for yml_file in $ENV_FILES; do
        env_name=$(grep "^name:" "$yml_file" | awk '{print $2}')
        basename_file=$(basename "$yml_file")

        # Check if already exists
        if conda env list | grep -q "^${env_name} "; then
            status="${GREEN}[exists]${NC}"
        else
            status="${YELLOW}[not created]${NC}"
        fi

        printf "  %-35s %s\n" "$env_name" "$status"
    done
    echo ""
    echo "To create all environments: bash RUN-setup_environments.sh"
    echo "To create one environment:  bash RUN-setup_environments.sh --env ai_gigantic_phylonames"
    exit 0
fi

# Track results
created_count=0
skipped_count=0
failed_count=0

# Create environments
for yml_file in $ENV_FILES; do
    env_name=$(grep "^name:" "$yml_file" | awk '{print $2}')
    basename_file=$(basename "$yml_file")

    # Skip if not the requested environment
    if [ -n "$SINGLE_ENV" ] && [ "$env_name" != "$SINGLE_ENV" ]; then
        continue
    fi

    echo "----------------------------------------"
    echo "Environment: $env_name"
    echo "File: $basename_file"
    echo ""

    # Check if environment already exists
    if conda env list | grep -q "^${env_name} "; then
        if $FORCE; then
            echo -e "${YELLOW}Removing existing environment...${NC}"
            conda env remove -n "$env_name" -y
        else
            echo -e "${GREEN}Already exists. Skipping.${NC}"
            echo "(use --force to recreate)"
            skipped_count=$((skipped_count + 1))
            continue
        fi
    fi

    # Create the environment
    echo "Creating environment..."
    if $INSTALLER env create -f "$yml_file" -y; then
        echo -e "${GREEN}Created successfully!${NC}"
        created_count=$((created_count + 1))
    else
        echo -e "${RED}Failed to create environment!${NC}"
        failed_count=$((failed_count + 1))
    fi
done

# Summary
echo ""
echo "========================================================================"
echo "SUMMARY"
echo "========================================================================"
echo "Created: ${created_count}"
echo "Skipped (already exist): ${skipped_count}"
echo "Failed: ${failed_count}"
echo ""

if [ $created_count -gt 0 ] || [ $skipped_count -gt 0 ]; then
    echo "To activate an environment:"
    echo "  conda activate ai_gigantic_phylonames"
    echo ""
    echo "Then run a workflow:"
    echo "  cd subprojects/x_phylonames/nf_workflow-COPYME_01-generate_phylonames/"
    echo "  bash RUN-phylonames.sh"
fi

if [ $failed_count -gt 0 ]; then
    echo -e "${RED}Some environments failed to create. Check errors above.${NC}"
    exit 1
fi

echo "========================================================================"
