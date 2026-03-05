# Repository Genomes - Species69 Database Acquisition

## Overview

This subproject downloads genome assemblies, annotations, and protein sequences
from various external repositories (e.g., institutional genome portals, FigShare,
Dryad, species-specific databases) for species not available from NCBI or published
datasets. Each species may require custom download and processing scripts.

## Directory Structure

```
repository_genomes/
├── nf_workflow-COPYME_01-repository_genomes/     # Workflow template
│   ├── INPUT_user/
│   │   └── repository_genomes_manifest.tsv       # Species + repository URLs
│   ├── OUTPUT_pipeline/
│   │   ├── 1-output/{genus_species}/             # Raw downloads (per-species dirs)
│   │   │   ├── genome.fasta                      #   Genome assembly
│   │   │   ├── annotation.gff3 (or .gtf)        #   Gene annotation
│   │   │   ├── protein.faa                       #   Protein sequences (if available)
│   │   │   └── download_log.txt                  #   Download metadata
│   │   ├── 2-output/
│   │   │   ├── genome/                           # Genus_species-repository_genomes.fasta
│   │   │   ├── annotation/                       # Genus_species-repository_genomes.gff3/gtf
│   │   │   └── protein/                          # Genus_species-repository_genomes.faa
│   │   ├── 3-output/T1_proteomes/                # T1 proteomes (.aa)
│   │   └── 4-output/                             # Symlinks manifest
│   ├── ai/
│   │   ├── main.nf                               # NextFlow pipeline
│   │   ├── nextflow.config
│   │   └── scripts/
│   │       ├── 001_ai-bash-download_repository_genomes.sh  # Master download orchestrator
│   │       ├── 002_ai-python-organize_rename.py
│   │       ├── 003_ai-python-extract_longest_transcript_proteomes.py
│   │       ├── 004_ai-bash-create_output_to_input_symlinks.sh
│   │       └── per_species/                      # Per-species download scripts
│   │           ├── TEMPLATE_SPECIES/download.sh  # Template to copy for new species
│   │           ├── Beroe_ovata/download.sh       # (example, created as needed)
│   │           └── .../                          # One directory per species
│   ├── RUN_repository_genomes.sh
│   ├── RUN_repository_genomes.sbatch
│   └── repository_genomes_config.yaml
├── output_to_input/
│   └── T1_proteomes/                             # Symlinks to T1 proteomes
├── user_research/
│   └── README.md
└── README.md                                     # This file
```

## Quick Start

```bash
# 1. Copy the template to a run directory
cp -r nf_workflow-COPYME_01-repository_genomes nf_workflow-RUN_1_01-repository_genomes

# 2. Enter the run directory
cd nf_workflow-RUN_1_01-repository_genomes

# 3. Run locally
bash RUN_repository_genomes.sh

# 4. Or submit to SLURM
sbatch RUN_repository_genomes.sbatch
```

## Key Difference from kim_2025_genomes and ncbi_genomes

Unlike the other genome sources, repository genomes come from heterogeneous sources.
Each species may have:
- Different file formats (FASTA, GFF3, GTF, GenBank flat file)
- Different download methods (wget, curl, FTP, API)
- Different directory structures at the source
- Different protein file availability (may need gffread extraction)

The pipeline handles this via per-species download scripts in `ai/scripts/per_species/`.

## Pipeline Architecture

### Script 001: Master Download Orchestrator
`001_ai-bash-download_repository_genomes.sh` reads the manifest and loops over
all species. For each species, it looks for a per-species download script at:
```
ai/scripts/per_species/{genus_species}/download.sh
```

If the script exists, it runs it. If not, the species is **skipped** (not failed).
This allows incremental development -- add download scripts one species at a time.

Each per-species `download.sh` receives 5 arguments:
1. `output_dir` - Where to put files (`1-output/{genus_species}/`)
2. `repository_url` - Main repository URL
3. `genome_url` - Direct genome download URL (may be empty)
4. `annotation_url` - Direct annotation download URL (may be empty)
5. `protein_url` - Direct protein download URL (may be empty)

Expected output files in `output_dir`:
- `genome.fasta` - Genome assembly
- `annotation.gff3` or `annotation.gtf` - Gene annotation
- `protein.faa` - Protein sequences (if available)
- `download_log.txt` - What was downloaded and from where

### Script 002: Organize and Rename
Copies files from `1-output/{genus_species}/` into standardized directories:
- `2-output/genome/` - `{genus_species}-repository_genomes.fasta`
- `2-output/annotation/` - `{genus_species}-repository_genomes.gff3` (or `.gtf`)
- `2-output/protein/` - `{genus_species}-repository_genomes.faa`

### Script 003: Extract T1 Proteomes (Flexible)
Handles four input scenarios depending on available data:
- **Path A**: protein.faa + GFF3 -> filter for longest protein per gene
- **Path B**: protein.faa + GTF -> filter for longest protein per gene
- **Path C**: genome + annotation, no protein -> use gffread to extract+translate
- **Path D**: protein only, no annotation -> use all proteins (no T1 filtering)

### Script 004: Create Symlinks
Creates relative symlinks in `output_to_input/T1_proteomes/` pointing to
`OUTPUT_pipeline/3-output/T1_proteomes/` for downstream GIGANTIC subprojects.

## Creating a Per-Species Download Script

```bash
# 1. Copy the template
cp -r ai/scripts/per_species/TEMPLATE_SPECIES ai/scripts/per_species/Genus_species

# 2. Edit the download script
vi ai/scripts/per_species/Genus_species/download.sh

# 3. Update manifest with direct URLs (optional)
vi INPUT_user/repository_genomes_manifest.tsv
```

## Species (33 total)

| Source Type | Count | Examples |
|---|---|---|
| FigShare | 10 | Chromosphaera_perkinsii, Pirum_gemmata, ... |
| Zenodo | 6 | Styela_plicata, Hormiphora_californensis, ... |
| Dryad | 5 | Urechis_unicinctus, Berghia_stephanieae, ... |
| OIST Marine Genomics | 2 | Dicyema_japonicum, Phoronis_australis |
| GigaDB | 1 | Lissachatina_fulica |
| Lab databases | 3 | Beroe_ovata, Mnemiopsis_leidyi, Pleurobrachia_bachei |
| Other | 3 | Lingula_anatina, Nautilus_pompilius, ... |

## Downstream Access

T1 proteomes are available via symlinks at:
```
repository_genomes/output_to_input/T1_proteomes/
```
