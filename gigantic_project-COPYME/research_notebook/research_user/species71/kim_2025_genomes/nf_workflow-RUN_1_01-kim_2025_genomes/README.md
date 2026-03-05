# Kim et al. 2025 Genomes - NextFlow Workflow

Download, decompress, rename, and extract T1 proteomes from Kim et al. 2025 early metazoa genome/gene annotation data.

## Quick Start

```bash
# Local execution
module load gffread
bash RUN_kim_2025_genomes.sh

# SLURM execution (edit account/qos in .sbatch first)
sbatch RUN_kim_2025_genomes.sbatch
```

No user input is needed - the pipeline downloads everything from GitHub.

## What This Does

| Step | Script | Description | Output |
|---|---|---|---|
| 1 | `001_ai-bash-download_source_data.sh` | Download .gz files from GitHub | `OUTPUT_pipeline/1-output/` |
| 2 | `002_ai-bash-unzip_rename_source_data.sh` | Decompress + rename to Genus_species | `OUTPUT_pipeline/2-output/` |
| 3 | `003_ai-python-extract_longest_transcript_proteomes.py` | Extract T1 proteomes via gffread | `OUTPUT_pipeline/3-output/` |
| 4 | `004_ai-bash-create_output_to_input_symlinks.sh` | Symlink proteomes for downstream | `output_to_input/T1_proteomes/` |

## Output

T1 proteomes at: `OUTPUT_pipeline/3-output/T1_proteomes/`

7 species, each with a `Genus_species-kim_2025-T1_proteome.aa` file.
Header format: `>Genus_species_geneID_transcriptID`

## Directory Structure

```
nf_workflow-COPYME_01-kim_2025_genomes/
├── RUN_kim_2025_genomes.sh          # Run locally
├── RUN_kim_2025_genomes.sbatch      # Run on SLURM
├── kim_2025_genomes_config.yaml     # Configuration
├── README.md                        # This file
├── INPUT_user/                      # (empty - no user input needed)
├── OUTPUT_pipeline/                 # Created by pipeline
│   ├── 1-output/                    # Downloaded .gz files
│   │   ├── genome/
│   │   └── gene_annotation/
│   ├── 2-output/                    # Decompressed + renamed
│   │   ├── genome/                  # Genus_species-kim_2025.fasta
│   │   └── gene_annotation/         # Genus_species-kim_2025.gtf
│   ├── 3-output/                    # T1 proteomes
│   │   ├── T1_proteomes/            # Genus_species-kim_2025-T1_proteome.aa
│   │   └── gffread_all_transcripts/ # Intermediate (all transcripts)
│   └── 4-output/                    # Symlink manifest
└── ai/                              # Internal (don't touch)
    ├── main.nf
    ├── nextflow.config
        └── scripts/
```

## Downstream Access

After the pipeline runs, T1 proteomes are accessible to other GIGANTIC subprojects via symlinks at:
```
kim_2025_genomes/output_to_input/T1_proteomes/*.aa
```

## Requirements

- NextFlow (>= 21.04.0)
- gffread (`module load gffread`)
- git (for GitHub download)
- Python 3

## Runtime

~40 seconds (most time is the GitHub download).
