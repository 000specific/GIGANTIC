#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 09 | Purpose: Install SignalP 6 from manually downloaded package
# Human: Eric Edsinger

################################################################################
# DOWNLOAD_SOFTWARE-signalp.sh
################################################################################
#
# Installs SignalP 6 into the ai_gigantic_signalp conda environment.
#
# SignalP 6 requires a license from DTU - it cannot be freely downloaded.
# You must download the package manually before running this script.
#
# STEP 1: Register and download SignalP 6 from:
#   https://services.healthtech.dtu.dk/services/SignalP-6.0/
#
# STEP 2: Place the downloaded package in this directory:
#   BLOCK_signalp/software/signalp-6.0h.fast.tar.gz
#   (or whatever version you received)
#
# STEP 3: Run this script:
#   bash DOWNLOAD_SOFTWARE-signalp.sh
#
# WHAT THIS SCRIPT DOES:
#   1. Extracts the SignalP 6 package to software/signalp6_fast/
#   2. Creates a stable symlink: software/signalp -> signalp6_fast/
#   3. Installs SignalP into the ai_gigantic_signalp conda environment via pip
#
# AFTER RUNNING:
#   - SignalP 6 will be available as 'signalp6' command in the conda env
#   - Workflow configs reference the conda environment, not a path
#
################################################################################

set -e

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOFTWARE_DIR="${SCRIPT_DIR}/software"
CONDA_ENV="ai_gigantic_signalp"

echo "========================================================================"
echo "SignalP 6 Installation"
echo "========================================================================"
echo ""

# =============================================================================
# CHECK PREREQUISITES
# =============================================================================

# Check for conda
module load conda 2>/dev/null || true

if ! conda env list 2>/dev/null | grep -q "${CONDA_ENV}"; then
    echo "ERROR: Conda environment '${CONDA_ENV}' not found!"
    echo ""
    echo "Create it first:"
    echo "  mamba env create -f ../../../../conda_environments/ai_gigantic_signalp.yml"
    echo ""
    exit 1
fi

echo "Conda environment found: ${CONDA_ENV}"

# =============================================================================
# FIND SIGNALP PACKAGE
# =============================================================================

mkdir -p "${SOFTWARE_DIR}"

# Look for SignalP tarball in software/
SIGNALP_TARBALL=""
for f in "${SOFTWARE_DIR}"/signalp-*.tar.gz "${SOFTWARE_DIR}"/signalp6*.tar.gz; do
    if [ -f "$f" ]; then
        SIGNALP_TARBALL="$f"
        break
    fi
done

if [ -z "${SIGNALP_TARBALL}" ]; then
    echo ""
    echo "ERROR: No SignalP package found in ${SOFTWARE_DIR}/"
    echo ""
    echo "Please download SignalP 6 from DTU:"
    echo "  https://services.healthtech.dtu.dk/services/SignalP-6.0/"
    echo ""
    echo "Then place the .tar.gz file in:"
    echo "  ${SOFTWARE_DIR}/"
    echo ""
    echo "Expected filename pattern: signalp-6.0*.tar.gz"
    echo ""
    exit 1
fi

echo "Found SignalP package: $(basename "${SIGNALP_TARBALL}")"
echo ""

# =============================================================================
# EXTRACT PACKAGE
# =============================================================================

echo "Extracting SignalP..."
cd "${SOFTWARE_DIR}"

tar -xzf "$(basename "${SIGNALP_TARBALL}")"

# Find the extracted directory
SIGNALP_DIR=""
for d in signalp6* signalp-6*; do
    if [ -d "$d" ] && [ "$d" != "signalp" ]; then
        SIGNALP_DIR="$d"
        break
    fi
done

if [ -z "${SIGNALP_DIR}" ]; then
    echo "ERROR: Could not find extracted SignalP directory!"
    echo "Contents of ${SOFTWARE_DIR}:"
    ls -la
    exit 1
fi

echo "Extracted to: ${SIGNALP_DIR}"

# =============================================================================
# CREATE STABLE SYMLINK
# =============================================================================

SYMLINK_PATH="${SOFTWARE_DIR}/signalp"

if [ -L "${SYMLINK_PATH}" ]; then
    rm "${SYMLINK_PATH}"
fi

ln -sf "${SIGNALP_DIR}" "${SYMLINK_PATH}"
echo "Symlink: signalp -> ${SIGNALP_DIR}"

# =============================================================================
# INSTALL INTO CONDA ENVIRONMENT
# =============================================================================

echo ""
echo "Installing SignalP into conda environment: ${CONDA_ENV}"

conda activate "${CONDA_ENV}"

# SignalP 6 is typically installed via pip from the extracted directory
if [ -f "${SIGNALP_DIR}/setup.py" ] || [ -f "${SIGNALP_DIR}/pyproject.toml" ]; then
    pip install "${SIGNALP_DIR}/"
elif [ -f "${SIGNALP_DIR}/signalp6_fast_distilled/setup.py" ]; then
    pip install "${SIGNALP_DIR}/signalp6_fast_distilled/"
else
    echo ""
    echo "WARNING: Could not find setup.py or pyproject.toml in ${SIGNALP_DIR}/"
    echo "You may need to install manually:"
    echo "  conda activate ${CONDA_ENV}"
    echo "  pip install ${SOFTWARE_DIR}/${SIGNALP_DIR}/"
    echo ""
fi

conda deactivate 2>/dev/null || true

# =============================================================================
# VERIFY INSTALLATION
# =============================================================================

echo ""
echo "Verifying installation..."

conda activate "${CONDA_ENV}" 2>/dev/null
if command -v signalp6 &> /dev/null; then
    echo "SignalP 6 is available as 'signalp6'"
elif command -v signalp &> /dev/null; then
    echo "SignalP is available as 'signalp'"
else
    echo "WARNING: signalp6/signalp command not found in PATH after installation."
    echo "You may need to install manually. Check ${SIGNALP_DIR}/ for instructions."
fi
conda deactivate 2>/dev/null || true

# =============================================================================
# COMPLETION
# =============================================================================

echo ""
echo "========================================================================"
echo "SignalP 6 installation complete!"
echo "========================================================================"
echo ""
echo "Software directory: ${SOFTWARE_DIR}/${SIGNALP_DIR}"
echo "Stable symlink:     ${SYMLINK_PATH}"
echo "Conda environment:  ${CONDA_ENV}"
echo ""
echo "To test:"
echo "  conda activate ${CONDA_ENV}"
echo "  signalp6 --help"
echo ""
