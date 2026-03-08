#!/bin/bash
# AI: Claude Code | Opus 4.6 | 2026 March 07 | Purpose: Download and install InterProScan locally for BLOCK_interproscan workflows
# Human: Eric Edsinger

################################################################################
# DOWNLOAD_SOFTWARE-interproscan.sh
################################################################################
#
# Downloads and installs InterProScan from the EBI FTP server into a local
# software/ directory within BLOCK_interproscan/. All workflow runs (RUN_1,
# RUN_2, etc.) share this single installation.
#
# InterProScan is NOT recommended to install via conda - the official download
# from EBI is the supported installation method.
#
# Source: https://www.ebi.ac.uk/interpro/about/interproscan/
#
# USAGE:
#   bash DOWNLOAD_SOFTWARE-interproscan.sh
#
# WHAT THIS SCRIPT DOES:
#   1. Downloads InterProScan tarball from EBI FTP
#   2. Extracts to software/interproscan-{version}/
#   3. Creates a stable symlink: software/interproscan -> interproscan-{version}/
#   4. Runs InterProScan's initial setup (index databases)
#
# AFTER RUNNING:
#   - Workflow configs should point to: ../software/interproscan
#   - This path remains stable across version updates
#
# TO UPDATE INTERPROSCAN:
#   1. Change INTERPROSCAN_VERSION below
#   2. Re-run this script
#   3. The symlink will be updated to the new version
#
# REQUIREMENTS:
#   - wget or curl
#   - tar
#   - Java 11+ (required by InterProScan 5)
#
################################################################################

set -e

# =============================================================================
# CONFIGURATION - Update version here when upgrading
# =============================================================================

INTERPROSCAN_VERSION="5.72-103.0"

# =============================================================================
# DERIVED PATHS
# =============================================================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOFTWARE_DIR="${SCRIPT_DIR}/software"
INTERPROSCAN_DIRNAME="interproscan-${INTERPROSCAN_VERSION}"
INTERPROSCAN_TARBALL="${INTERPROSCAN_DIRNAME}-64-bit.tar.gz"
INTERPROSCAN_TARBALL_MD5="${INTERPROSCAN_TARBALL}.md5"
DOWNLOAD_URL="https://ftp.ebi.ac.uk/pub/software/unix/iprscan/5/${INTERPROSCAN_VERSION}/${INTERPROSCAN_TARBALL}"
MD5_URL="https://ftp.ebi.ac.uk/pub/software/unix/iprscan/5/${INTERPROSCAN_VERSION}/${INTERPROSCAN_TARBALL_MD5}"
INSTALL_DIR="${SOFTWARE_DIR}/${INTERPROSCAN_DIRNAME}"
SYMLINK_PATH="${SOFTWARE_DIR}/interproscan"

echo "========================================================================"
echo "InterProScan Download and Installation"
echo "========================================================================"
echo ""
echo "Version:     ${INTERPROSCAN_VERSION}"
echo "Install to:  ${INSTALL_DIR}"
echo "Symlink:     ${SYMLINK_PATH}"
echo ""

# =============================================================================
# CHECK PREREQUISITES
# =============================================================================

# Check for Java
if ! command -v java &> /dev/null; then
    echo "ERROR: Java is not available!"
    echo "InterProScan 5 requires Java 11 or later."
    echo ""
    echo "On HiPerGator, try:  module load java"
    echo ""
    exit 1
fi

JAVA_VERSION=$( java -version 2>&1 | head -1 )
echo "Java found: ${JAVA_VERSION}"

# Check for download tool
if command -v wget &> /dev/null; then
    DOWNLOADER="wget"
elif command -v curl &> /dev/null; then
    DOWNLOADER="curl"
else
    echo "ERROR: Neither wget nor curl is available!"
    exit 1
fi
echo "Download tool: ${DOWNLOADER}"
echo ""

# =============================================================================
# CHECK IF ALREADY INSTALLED
# =============================================================================

if [ -d "${INSTALL_DIR}" ] && [ -f "${INSTALL_DIR}/interproscan.sh" ]; then
    echo "InterProScan ${INTERPROSCAN_VERSION} is already installed at:"
    echo "  ${INSTALL_DIR}"
    echo ""
    echo "Symlink: ${SYMLINK_PATH}"
    echo ""
    echo "To force re-installation, remove the directory first:"
    echo "  rm -rf ${INSTALL_DIR}"
    echo "  bash $0"
    echo ""
    exit 0
fi

# =============================================================================
# CREATE SOFTWARE DIRECTORY
# =============================================================================

mkdir -p "${SOFTWARE_DIR}"
cd "${SOFTWARE_DIR}"

# =============================================================================
# DOWNLOAD INTERPROSCAN
# =============================================================================

echo "Downloading InterProScan ${INTERPROSCAN_VERSION}..."
echo "URL: ${DOWNLOAD_URL}"
echo ""
echo "NOTE: This is a large download (~15 GB). Please be patient."
echo ""

if [ "${DOWNLOADER}" = "wget" ]; then
    wget -c "${DOWNLOAD_URL}"
    wget -c "${MD5_URL}"
elif [ "${DOWNLOADER}" = "curl" ]; then
    curl -C - -L -O "${DOWNLOAD_URL}"
    curl -C - -L -O "${MD5_URL}"
fi

# =============================================================================
# VERIFY MD5 CHECKSUM
# =============================================================================

echo ""
echo "Verifying MD5 checksum..."

if command -v md5sum &> /dev/null; then
    if md5sum -c "${INTERPROSCAN_TARBALL_MD5}"; then
        echo "Checksum verified successfully."
    else
        echo "ERROR: MD5 checksum verification failed!"
        echo "The download may be corrupted. Please delete and re-download:"
        echo "  rm ${INTERPROSCAN_TARBALL}"
        echo "  bash $0"
        exit 1
    fi
else
    echo "WARNING: md5sum not available - skipping checksum verification."
    echo "Proceeding with installation anyway."
fi

# =============================================================================
# EXTRACT
# =============================================================================

echo ""
echo "Extracting InterProScan (this may take several minutes)..."

tar -xzf "${INTERPROSCAN_TARBALL}"

if [ ! -d "${INTERPROSCAN_DIRNAME}" ]; then
    echo "ERROR: Expected directory ${INTERPROSCAN_DIRNAME} not found after extraction!"
    echo "Contents of ${SOFTWARE_DIR}:"
    ls -la
    exit 1
fi

echo "Extraction complete."

# =============================================================================
# INITIAL SETUP - Index databases
# =============================================================================

echo ""
echo "Running InterProScan initial setup (indexing databases)..."
echo "This may take 10-20 minutes."
echo ""

cd "${INTERPROSCAN_DIRNAME}"

# InterProScan ships with a setup script that indexes the databases
if [ -f "setup.py" ]; then
    python3 setup.py interproscan.properties
elif [ -f "initial_setup.py" ]; then
    python3 initial_setup.py
else
    echo "WARNING: No setup script found. Database indexing may be needed manually."
    echo "Check the InterProScan documentation for your version."
fi

cd "${SOFTWARE_DIR}"

# =============================================================================
# CREATE STABLE SYMLINK
# =============================================================================

echo ""
echo "Creating stable symlink..."

# Remove existing symlink if present
if [ -L "${SYMLINK_PATH}" ]; then
    rm "${SYMLINK_PATH}"
fi

ln -sf "${INTERPROSCAN_DIRNAME}" "${SYMLINK_PATH}"
echo "  ${SYMLINK_PATH} -> ${INTERPROSCAN_DIRNAME}"

# =============================================================================
# CLEAN UP TARBALL (optional - comment out to keep)
# =============================================================================

echo ""
echo "Cleaning up downloaded tarball..."
rm -f "${INTERPROSCAN_TARBALL}"
rm -f "${INTERPROSCAN_TARBALL_MD5}"

# =============================================================================
# VERIFY INSTALLATION
# =============================================================================

echo ""
echo "Verifying installation..."

if [ -f "${SYMLINK_PATH}/interproscan.sh" ]; then
    echo "InterProScan executable found: ${SYMLINK_PATH}/interproscan.sh"
else
    echo "ERROR: interproscan.sh not found at ${SYMLINK_PATH}/interproscan.sh"
    echo "Installation may have failed."
    exit 1
fi

# =============================================================================
# COMPLETION
# =============================================================================

echo ""
echo "========================================================================"
echo "InterProScan ${INTERPROSCAN_VERSION} installed successfully!"
echo "========================================================================"
echo ""
echo "Installation directory: ${INSTALL_DIR}"
echo "Stable symlink:         ${SYMLINK_PATH}"
echo ""
echo "For workflow configs, use this path:"
echo "  interproscan_install_path: ../software/interproscan"
echo ""
echo "To test the installation:"
echo "  ${SYMLINK_PATH}/interproscan.sh --version"
echo ""
