# NCBI Genomes Workflow - COPYME_01

## Overview

NextFlow pipeline that downloads genome assemblies, GFF3 annotations, and protein
sequences from NCBI for 34 species, organizes them with GIGANTIC naming conventions,
and extracts T1 (longest transcript per gene) proteomes.

## Pipeline Steps

| Process | Script | Description | Output |
|---------|--------|-------------|--------|
| 1 | `001_ai-bash-download_ncbi_datasets.sh` | Download from NCBI using datasets CLI | `1-output/downloads/*.zip` |
| 2 | `002_ai-python-unzip_organize_rename.py` | Unzip + rename to GIGANTIC convention | `2-output/{genome,gff3,protein}/` |
| 3 | `003_ai-python-extract_longest_transcript_proteomes.py` | Extract T1 proteomes via GFF3 mappings | `3-output/T1_proteomes/*.aa` |
| 4 | `004_ai-bash-create_output_to_input_symlinks.sh` | Symlink T1 to output_to_input | `4-output/symlinks_manifest.tsv` |

## Usage

### Local Execution
```bash
bash RUN_ncbi_genomes.sh
```

### SLURM Execution
```bash
sbatch RUN_ncbi_genomes.sbatch
```

## Requirements

- **NextFlow** (conda env: `ai_nextflow`)
- **NCBI datasets CLI** (conda env: `ncbi_datasets`)
- **Python 3** (standard library only -- no extra packages needed)

## Input

**`INPUT_user/ncbi_genomes_manifest.tsv`**: Tab-separated manifest with columns:
- `genus_species`: Species name (e.g., `Homo_sapiens`)
- `accession`: NCBI assembly accession (e.g., `GCF_000001405.40`)

34 species total (31 RefSeq + 3 GenBank).

## Output

### OUTPUT_pipeline/1-output/downloads/
Raw zip files from NCBI datasets CLI (one per species).

### OUTPUT_pipeline/2-output/
Organized and renamed files:
- `genome/Genus_species-ncbi_genomes.fasta` - Genome assemblies
- `gff3/Genus_species-ncbi_genomes.gff3` - GFF3 annotations
- `protein/Genus_species-ncbi_genomes.faa` - All protein sequences from NCBI

### OUTPUT_pipeline/3-output/T1_proteomes/
T1 proteomes (longest protein per gene):
- `Genus_species-ncbi_genomes-T1_proteome.aa`
- Header format: `>Genus_species-ncbi_genomes|protein_id|gene_id`

### OUTPUT_pipeline/4-output/
Symlink manifest tracking all links created in `output_to_input/`.

## T1 Extraction Method

Unlike `kim_2025_genomes` (which uses `gffread` to translate from genome + GTF),
this pipeline uses NCBI's pre-computed protein FASTA files and filters them:

1. Parse GFF3 to build gene -> mRNA -> CDS -> protein_id mapping
2. Read NCBI protein.faa for all protein sequences
3. For each gene, keep only the longest protein (T1)

This approach uses NCBI's own translations, which are curated and validated.

## Configuration

Edit `ncbi_genomes_config.yaml` to change output directory settings.
Do NOT edit `ai/nextflow.config` directly.

## SLURM Resources

- Time: 4 hours
- Memory: 16 GB
- CPUs: 4
- Estimated disk: ~10-15 GB (downloads + extracted files)

## Estimated Runtime

- Downloads: 15-60 minutes (depends on network speed; Homo sapiens is ~1GB alone)
- Unzip + rename: 5-10 minutes
- T1 extraction: 5-15 minutes
- Total: ~30 minutes to 2 hours
