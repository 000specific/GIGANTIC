#!/usr/bin/env bash
# AI: Claude Code | Opus 4 | 2026 February 11 17:45 | Purpose: Decompress and rename Kim et al. 2025 genome and gene annotation files to Genus_species convention
# Human: Eric Edsinger

# =============================================================================
# 002_ai-bash-unzip_rename_source_data.sh
#
# Decompresses (.gz) and renames genome FASTA and gene annotation GTF files
# from the Kim et al. 2025 repository abbreviations to standardized
# Genus_species-kim_2025 naming convention.
#
# Abbreviation -> Species mapping:
#   Cowc   -> Capsaspora_owczarzaki
#   Emue   -> Ephydatia_muelleri
#   HoiH23 -> Cladtertia_collaboinventa (formerly Hoilungia hongkongensis H23)
#   Mlei   -> Mnemiopsis_leidyi
#   Sarc   -> Sphaeroforma_arctica
#   Sros   -> Salpingoeca_rosetta
#   Tadh   -> Trichoplax_adhaerens
#
# Input:  1-output/genome/*.fasta.gz
#         1-output/gene_annotation/*.gtf.gz
#
# Output: 2-output/genome/Genus_species-kim_2025.fasta
#         2-output/gene_annotation/Genus_species-kim_2025.gtf
# =============================================================================

set -euo pipefail

# Directories - accept argument or default
INPUT_DIRECTORY="${1:-1-output}"
OUTPUT_DIRECTORY="2-output"

echo "============================================"
echo "002: Unzip and rename source data"
echo "============================================"
echo ""
echo "Input:  ${INPUT_DIRECTORY}"
echo "Output: ${OUTPUT_DIRECTORY}"
echo ""

INPUT_GENOME_DIRECTORY="${INPUT_DIRECTORY}/genome"
INPUT_ANNOTATION_DIRECTORY="${INPUT_DIRECTORY}/gene_annotation"
OUTPUT_GENOME_DIRECTORY="${OUTPUT_DIRECTORY}/genome"
OUTPUT_ANNOTATION_DIRECTORY="${OUTPUT_DIRECTORY}/gene_annotation"

# Verify input directories exist
if [ ! -d "${INPUT_GENOME_DIRECTORY}" ]; then
    echo "ERROR: Genome directory not found: ${INPUT_GENOME_DIRECTORY}"
    echo "Run 001_ai-bash-download_source_data.sh first."
    exit 1
fi

if [ ! -d "${INPUT_ANNOTATION_DIRECTORY}" ]; then
    echo "ERROR: Gene annotation directory not found: ${INPUT_ANNOTATION_DIRECTORY}"
    echo "Run 001_ai-bash-download_source_data.sh first."
    exit 1
fi

# Create output directories
mkdir -p "${OUTPUT_GENOME_DIRECTORY}"
mkdir -p "${OUTPUT_ANNOTATION_DIRECTORY}"

# =============================================================================
# Species mapping: original_prefix -> Genus_species
# =============================================================================

declare -A GENOME_MAP
GENOME_MAP["Cowc_gDNA"]="Capsaspora_owczarzaki"
GENOME_MAP["Emue_gDNA_23chromosomes"]="Ephydatia_muelleri"
GENOME_MAP["HoiH23_gDNA"]="Cladtertia_collaboinventa"
GENOME_MAP["Mlei_gDNA"]="Mnemiopsis_leidyi"
GENOME_MAP["Sarc_gDNA"]="Sphaeroforma_arctica"
GENOME_MAP["Sros_gDNA"]="Salpingoeca_rosetta"
GENOME_MAP["Tadh_gDNA"]="Trichoplax_adhaerens"

declare -A ANNOTATION_MAP
ANNOTATION_MAP["Cowc_gene_annot"]="Capsaspora_owczarzaki"
ANNOTATION_MAP["Emue_gene_annot"]="Ephydatia_muelleri"
ANNOTATION_MAP["HoiH23_gene_annot"]="Cladtertia_collaboinventa"
ANNOTATION_MAP["Mlei_gene_annot"]="Mnemiopsis_leidyi"
ANNOTATION_MAP["Mlei_gene_annot_NCBI_gene_names"]="Mnemiopsis_leidyi"
ANNOTATION_MAP["Sarc_gene_annot"]="Sphaeroforma_arctica"
ANNOTATION_MAP["Sros_gene_annot"]="Salpingoeca_rosetta"
ANNOTATION_MAP["Tadh_gene_annot"]="Trichoplax_adhaerens"

# =============================================================================
# Process genome FASTA files
# =============================================================================

echo "--- Processing genome FASTA files ---"
echo ""

for original_prefix in "${!GENOME_MAP[@]}"; do
    genus_species="${GENOME_MAP[${original_prefix}]}"
    input_file="${INPUT_GENOME_DIRECTORY}/${original_prefix}.fasta.gz"
    output_file="${OUTPUT_GENOME_DIRECTORY}/${genus_species}-kim_2025.fasta"

    if [ ! -f "${input_file}" ]; then
        echo "  WARNING: Source file not found: ${input_file}"
        continue
    fi

    echo "  Decompressing: ${original_prefix}.fasta.gz -> ${genus_species}-kim_2025.fasta"
    gunzip -c "${input_file}" > "${output_file}"
done

echo ""

# =============================================================================
# Process gene annotation GTF files
# =============================================================================

echo "--- Processing gene annotation GTF files ---"
echo ""

for original_prefix in "${!ANNOTATION_MAP[@]}"; do
    genus_species="${ANNOTATION_MAP[${original_prefix}]}"
    input_file="${INPUT_ANNOTATION_DIRECTORY}/${original_prefix}.gtf.gz"

    # Special handling for the NCBI gene names variant
    if [ "${original_prefix}" = "Mlei_gene_annot_NCBI_gene_names" ]; then
        output_file="${OUTPUT_ANNOTATION_DIRECTORY}/${genus_species}-kim_2025-ncbi_gene_names.gtf"
    else
        output_file="${OUTPUT_ANNOTATION_DIRECTORY}/${genus_species}-kim_2025.gtf"
    fi

    if [ ! -f "${input_file}" ]; then
        echo "  WARNING: Source file not found: ${input_file}"
        continue
    fi

    echo "  Decompressing: ${original_prefix}.gtf.gz -> $(basename ${output_file})"
    gunzip -c "${input_file}" > "${output_file}"
done

echo ""

# =============================================================================
# Verify output
# =============================================================================

echo "============================================"
echo "Unzip and rename complete."
echo "============================================"
echo ""

echo "--- Genomes (${OUTPUT_GENOME_DIRECTORY}/) ---"
ls -lh "${OUTPUT_GENOME_DIRECTORY}/"*.fasta 2>/dev/null || echo "  No .fasta files found"
echo ""

echo "--- Gene annotations (${OUTPUT_ANNOTATION_DIRECTORY}/) ---"
ls -lh "${OUTPUT_ANNOTATION_DIRECTORY}/"*.gtf 2>/dev/null || echo "  No .gtf files found"
echo ""

genome_count=$( ls -1 "${OUTPUT_GENOME_DIRECTORY}/"*.fasta 2>/dev/null | wc -l )
annotation_count=$( ls -1 "${OUTPUT_ANNOTATION_DIRECTORY}/"*.gtf 2>/dev/null | wc -l )
echo "Summary: ${genome_count} genome FASTA files, ${annotation_count} gene annotation GTF files"
echo ""
echo "Done!"
