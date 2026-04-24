#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 11 17:45 | Purpose: Download genome and gene annotation data from Kim et al. 2025 GitHub repository
# Human: Eric Edsinger

# =============================================================================
# 001_ai-bash-download_source_data.sh
#
# Downloads genome FASTA and gene annotation GTF files from the
# sebepedroslab/early-metazoa-3D-chromatin GitHub repository (Kim et al. 2025).
#
# Source: https://github.com/sebepedroslab/early-metazoa-3D-chromatin
# Paper:  Kim et al. 2025 "Evolutionary origin of animal genome regulation"
#         Nature, https://www.nature.com/articles/s41586-025-08960-w
#
# Species downloaded (7 total):
#   Cowc   = Capsaspora owczarzaki (ichthyosporean)
#   Emue   = Ephydatia muelleri (sponge)
#   HoiH23 = Cladtertia collaboinventa (placozoan, formerly Hoilungia hongkongensis H23)
#   Mlei   = Mnemiopsis leidyi (ctenophore)
#   Sarc   = Sphaeroforma arctica (ichthyosporean)
#   Sros   = Salpingoeca rosetta (choanoflagellate)
#   Tadh   = Trichoplax adhaerens (placozoan)
#
# Output:
#   1-output/genome/*.fasta.gz
#   1-output/gene_annotation/*.gtf.gz
# =============================================================================

set -euo pipefail

GITHUB_REPO="https://github.com/sebepedroslab/early-metazoa-3D-chromatin.git"
OUTPUT_DIRECTORY="1-output"
TEMP_CLONE_DIRECTORY=".temp_github_clone"

echo "============================================"
echo "001: Download Kim et al. 2025 source data"
echo "============================================"
echo ""
echo "Source repository: ${GITHUB_REPO}"
echo "Output directory:  ${OUTPUT_DIRECTORY}"
echo ""

# Clean up any previous temporary clone
if [ -d "${TEMP_CLONE_DIRECTORY}" ]; then
    echo "Cleaning up previous temporary clone..."
    rm -rf "${TEMP_CLONE_DIRECTORY}"
fi

# Step 1: Shallow clone with sparse checkout (minimal download)
echo "Step 1: Cloning repository (sparse checkout, depth=1)..."
git clone \
    --no-checkout \
    --depth 1 \
    --filter=blob:none \
    "${GITHUB_REPO}" \
    "${TEMP_CLONE_DIRECTORY}"

# Step 2: Configure sparse checkout for just the two data directories
echo "Step 2: Configuring sparse checkout for data/genome and data/gene_annotation..."
cd "${TEMP_CLONE_DIRECTORY}"
git sparse-checkout init --cone
git sparse-checkout set data/genome data/gene_annotation
git checkout main
cd ..

# Step 3: Copy downloaded data to output directory
echo "Step 3: Copying data to ${OUTPUT_DIRECTORY}/..."
mkdir -p "${OUTPUT_DIRECTORY}"
cp -r "${TEMP_CLONE_DIRECTORY}/data/genome" "${OUTPUT_DIRECTORY}/"
cp -r "${TEMP_CLONE_DIRECTORY}/data/gene_annotation" "${OUTPUT_DIRECTORY}/"

# Step 4: Clean up temporary clone
echo "Step 4: Cleaning up temporary clone..."
rm -rf "${TEMP_CLONE_DIRECTORY}"

# Verify downloads
echo ""
echo "============================================"
echo "Download complete. Files:"
echo "============================================"
echo ""
echo "--- Genomes (${OUTPUT_DIRECTORY}/genome/) ---"
ls -lh "${OUTPUT_DIRECTORY}/genome/"
echo ""
echo "--- Gene annotations (${OUTPUT_DIRECTORY}/gene_annotation/) ---"
ls -lh "${OUTPUT_DIRECTORY}/gene_annotation/"
echo ""
echo "Done!"
