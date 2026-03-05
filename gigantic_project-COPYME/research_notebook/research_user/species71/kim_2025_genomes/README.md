# kim_2025_genomes - Kim et al. 2025 Early Metazoa Genomes

**AI**: Claude Code | Opus 4 | 2026 February 11
**Human**: Eric Edsinger

---

## Purpose

The kim_2025_genomes subproject acquires genome and gene annotation data from Kim et al. 2025 and produces T1 (longest transcript per gene) proteomes for 7 early metazoa and outgroup species.

**Source**: Kim et al. 2025 "Evolutionary origin of animal genome regulation" - *Nature*
**Repository**: https://github.com/sebepedroslab/early-metazoa-3D-chromatin

---

## Species (7)

| Abbreviation | Species | Group |
|---|---|---|
| Cowc | *Capsaspora owczarzaki* | Ichthyosporean |
| Emue | *Ephydatia muelleri* | Sponge |
| HoiH23 | *Cladtertia collaboinventa* | Placozoan (formerly *Hoilungia hongkongensis* H23) |
| Mlei | *Mnemiopsis leidyi* | Ctenophore |
| Sarc | *Sphaeroforma arctica* | Ichthyosporean |
| Sros | *Salpingoeca rosetta* | Choanoflagellate |
| Tadh | *Trichoplax adhaerens* | Placozoan |

---

## Directory Structure

```
kim_2025_genomes/
├── README.md                          # This file
├── user_research/                     # Personal workspace
├── output_to_input/                   # Outputs for downstream subprojects
│   └── T1_proteomes/                 # Symlinks to OUTPUT_pipeline/3-output/T1_proteomes/
└── nf_workflow-COPYME_01-kim_2025_genomes/
    ├── README.md                      # Quick start guide
    ├── RUN_kim_2025_genomes.sh        # bash (local execution)
    ├── RUN_kim_2025_genomes.sbatch    # sbatch (SLURM execution)
    ├── kim_2025_genomes_config.yaml   # User configuration
    ├── INPUT_user/                    # (empty - no user input needed)
    ├── OUTPUT_pipeline/               # Generated outputs
    │   ├── 1-output/                  # Downloaded .gz files
    │   ├── 2-output/                  # Decompressed + renamed
    │   ├── 3-output/                  # T1 proteomes
    │   └── 4-output/                  # Symlink manifest
    └── ai/                            # Internal (don't touch)
        ├── main.nf                    # NextFlow pipeline
        ├── nextflow.config            # NextFlow settings
        └── scripts/                   # Bash/Python scripts
            ├── 001_ai-bash-download_source_data.sh
            ├── 002_ai-bash-unzip_rename_source_data.sh
            ├── 003_ai-python-extract_longest_transcript_proteomes.py
            └── 004_ai-bash-create_output_to_input_symlinks.sh
```

---

## Quick Start

```bash
cd nf_workflow-COPYME_01-kim_2025_genomes

# Local machine:
module load gffread
bash RUN_kim_2025_genomes.sh

# SLURM cluster (edit account/qos first):
sbatch RUN_kim_2025_genomes.sbatch
```

The pipeline will:
1. Download genome + gene annotation data from GitHub (~250 MB compressed)
2. Decompress and rename to `Genus_species-kim_2025` convention
3. Extract T1 (longest transcript per gene) proteomes using gffread
4. Symlink proteomes to `output_to_input/T1_proteomes/` for downstream subprojects

---

## Pipeline Steps

| Step | Script | Description | Output |
|---|---|---|---|
| 1 | `001_ai-bash-download_source_data.sh` | Download .gz files from GitHub | `OUTPUT_pipeline/1-output/` |
| 2 | `002_ai-bash-unzip_rename_source_data.sh` | Decompress and rename to Genus_species | `OUTPUT_pipeline/2-output/` |
| 3 | `003_ai-python-extract_longest_transcript_proteomes.py` | Extract T1 proteomes via gffread | `OUTPUT_pipeline/3-output/` |
| 4 | `004_ai-bash-create_output_to_input_symlinks.sh` | Symlink proteomes to output_to_input/ | `output_to_input/T1_proteomes/` |

---

## Output

### T1 Proteomes

**Location**: `nf_workflow-COPYME_01-kim_2025_genomes/OUTPUT_pipeline/3-output/T1_proteomes/`

```
Capsaspora_owczarzaki-kim_2025-T1_proteome.aa      (9,031 proteins)
Cladtertia_collaboinventa-kim_2025-T1_proteome.aa   (11,330 proteins)
Ephydatia_muelleri-kim_2025-T1_proteome.aa          (30,360 proteins)
Mnemiopsis_leidyi-kim_2025-T1_proteome.aa           (19,625 proteins)
Salpingoeca_rosetta-kim_2025-T1_proteome.aa         (11,624 proteins)
Sphaeroforma_arctica-kim_2025-T1_proteome.aa        (33,234 proteins)
Trichoplax_adhaerens-kim_2025-T1_proteome.aa        (11,522 proteins)
```

Header format: `>Genus_species_geneID_transcriptID`

---

## Dependencies

- NextFlow (>= 21.04.0)
- gffread (`module load gffread`)
- git (for GitHub download)
- Python 3
