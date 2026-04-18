#!/bin/bash
# AI: Claude Code | Opus 4.6 (1M context) | 2026 April 18 | Purpose: Run EvidentialGene T0/T1 proteome extraction
# Human: Eric Edsinger

################################################################################
# GIGANTIC EvidentialGene T0/T1 Proteome Extraction - Local Execution
################################################################################
#
# PURPOSE:
# Extract T0 (main+alt) and T1 (main only) proteomes from an EvidentialGene
# okayset okay.aa file. The T1 proteome is what most GIGANTIC analyses need.
#
# USAGE:
#   bash RUN-workflow.sh
#
# BEFORE RUNNING:
# 1. Edit START_HERE-user_config.yaml with your species name and okay.aa path
# 2. Ensure the evigene okay.aa file exists at the configured path
#
# OUTPUTS:
#   OUTPUT_pipeline/1-output/{species_name}-T1.aa    Main transcripts only
#   OUTPUT_pipeline/1-output/{species_name}-T0.aa    Main + alt transcripts
#   OUTPUT_pipeline/1-output/1_ai-summary-evigene_extraction.tsv  Summary report
#
################################################################################

echo "========================================================================"
echo "GIGANTIC EvidentialGene T0/T1 Proteome Extraction"
echo "========================================================================"
echo ""
echo "Started: $(date)"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "${SCRIPT_DIR}"

# Prevent NextFlow from phoning home (consistency across GIGANTIC workflows)
export NXF_OFFLINE=true

# ============================================================================
# Read Configuration
# ============================================================================

CONFIG_FILE="START_HERE-user_config.yaml"

if [ ! -f "${CONFIG_FILE}" ]; then
    echo "ERROR: Configuration file not found: ${CONFIG_FILE}"
    echo "Copy START_HERE-user_config.yaml and edit it with your settings."
    exit 1
fi

# Parse YAML values (simple grep-based for flat YAML)
SPECIES_NAME=$(grep "name:" "${CONFIG_FILE}" | head -1 | sed 's/.*name: *"//' | sed 's/".*//')
EVIGENE_OKAY_AA=$(grep "evigene_okay_aa:" "${CONFIG_FILE}" | head -1 | sed 's/.*evigene_okay_aa: *"//' | sed 's/".*//')
OUTPUT_BASE_DIR=$(grep "base_dir:" "${CONFIG_FILE}" | head -1 | sed 's/.*base_dir: *"//' | sed 's/".*//')

# Default output directory if not set
if [ -z "${OUTPUT_BASE_DIR}" ]; then
    OUTPUT_BASE_DIR="OUTPUT_pipeline"
fi

echo "Configuration:"
echo "  Species name:     ${SPECIES_NAME}"
echo "  Evigene okay.aa:  ${EVIGENE_OKAY_AA}"
echo "  Output directory:  ${OUTPUT_BASE_DIR}"
echo ""

# ============================================================================
# Validate Configuration
# ============================================================================

if [ "${SPECIES_NAME}" == "Genus_species" ] || [ -z "${SPECIES_NAME}" ]; then
    echo "ERROR: Please set your species name in ${CONFIG_FILE}"
    echo "       Replace 'Genus_species' with your actual species name."
    exit 1
fi

if [ ! -f "${EVIGENE_OKAY_AA}" ]; then
    echo "ERROR: Evigene okay.aa file not found: ${EVIGENE_OKAY_AA}"
    echo "       Check the path in ${CONFIG_FILE}"
    exit 1
fi

# ============================================================================
# Activate GIGANTIC Environment
# ============================================================================

ENV_NAME="ai_gigantic_genomesdb"
ENV_YML="../../../../conda_environments/${ENV_NAME}.yml"

module load conda 2>/dev/null || true

if ! command -v conda &> /dev/null; then
    echo "ERROR: conda not found!"
    echo "On HPC (HiPerGator): module load conda"
    exit 1
fi

# Create environment on-demand if it does not exist
if ! conda env list 2>/dev/null | grep -q "^${ENV_NAME} "; then
    echo "Environment '${ENV_NAME}' not found. Creating on-demand..."
    echo ""
    if [ ! -f "${ENV_YML}" ]; then
        echo "ERROR: Environment spec not found at: ${ENV_YML}"
        echo "Attempting to run with current environment..."
    else
        if command -v mamba &> /dev/null; then
            mamba env create -f "${ENV_YML}" -y
        else
            conda env create -f "${ENV_YML}" -y
        fi
        echo ""
        echo "Environment '${ENV_NAME}' created successfully."
        echo ""
    fi
fi

# Activate the environment
if conda activate "${ENV_NAME}" 2>/dev/null; then
    echo "Activated conda environment: ${ENV_NAME}"
else
    echo "WARNING: Could not activate '${ENV_NAME}'. Continuing with current environment."
fi
echo ""

# ============================================================================
# Create Output Directory
# ============================================================================

OUTPUT_DIR="${OUTPUT_BASE_DIR}/1-output"
mkdir -p "${OUTPUT_DIR}"

# ============================================================================
# Run Extraction Script
# ============================================================================

echo "Running EvidentialGene T0/T1 extraction..."
echo ""

python3 ai/scripts/001_ai-python-extract_evigene_T0_T1_proteomes.py \
    --input-fasta "${EVIGENE_OKAY_AA}" \
    --species-name "${SPECIES_NAME}" \
    --output-dir "${OUTPUT_DIR}"

SCRIPT_EXIT_CODE=$?

echo ""
if [ $SCRIPT_EXIT_CODE -ne 0 ]; then
    echo "========================================================================"
    echo "FAILED! Extraction script exited with code ${SCRIPT_EXIT_CODE}"
    echo "Check logs above for details."
    echo "========================================================================"
    exit $SCRIPT_EXIT_CODE
fi

echo "========================================================================"
echo "SUCCESS!"
echo ""
echo "Output files:"
echo "  ${OUTPUT_DIR}/${SPECIES_NAME}-T1.aa    Main transcripts only (use this for GIGANTIC)"
echo "  ${OUTPUT_DIR}/${SPECIES_NAME}-T0.aa    Main + alt transcripts"
echo "  ${OUTPUT_DIR}/1_ai-summary-evigene_extraction.tsv  Summary report"
echo ""
echo "Next step:"
echo "  Add the T1.aa file to your STEP_1 source manifest as the proteome path"
echo "  for this species."
echo "========================================================================"
echo "Completed: $(date)"

# ============================================================================
# Deactivate Conda Environment
# ============================================================================
conda deactivate 2>/dev/null || true
