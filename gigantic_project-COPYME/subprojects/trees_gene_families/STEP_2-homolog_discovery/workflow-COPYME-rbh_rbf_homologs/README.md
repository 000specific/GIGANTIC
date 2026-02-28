# workflow-COPYME-rbh_rbf_homologs

**AI**: Claude Code | Opus 4.6 | 2026 February 27
**Human**: Eric Edsinger

---

## Purpose

STEP_2 workflow template for discovering homologs via Reciprocal Best Hit (RBH) / Reciprocal Best Fit (RBF) BLAST methodology for **one gene family per workflow copy**.

**Part of**: STEP_2-homolog_discovery (see `../README.md`)

---

## What This Workflow Does

1. **Database Setup** (Process 1)
   - Lists available BLAST protein databases from genomesDB

2. **Forward BLAST** (Processes 2-3)
   - BLASTs RGS against all project databases (script 002 + execute)
   - Extracts candidate gene sequences (CGS) from BLAST hits (script 004)

3. **RGS Genome BLAST** (Process 4)
   - BLASTs RGS against source genomes of RGS species (script 005 + execute)

4. **Reciprocal BLAST Preparation** (Process 5)
   - Lists RGS BLAST files and model organism FASTAs (script 007)
   - Maps RGS to reference genome identifiers (script 008)
   - Creates modified genomes with RGS sequences (script 009)
   - Combines and creates BLAST database for reciprocal search

5. **Reciprocal BLAST** (Processes 6-7)
   - Runs reciprocal BLAST: CGS full proteins vs RGS genome database (script 011 + execute)
   - Extracts reciprocal best hits (script 013)

6. **Finalization** (Processes 8-10)
   - Filters by species keeper list (script 014)
   - Remaps CGS identifiers to GIGANTIC phylonames (script 015)
   - Concatenates RGS + CGS into final AGS (script 016)

---

## Usage

**Copy this template for each gene family:**
```bash
# For innexin_pannexin:
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_01-rbh_rbf_homologs
cd workflow-RUN_01-rbh_rbf_homologs

# For piezo (separate copy):
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_02-rbh_rbf_homologs
```

**Configure your run:**
```bash
# Edit the configuration file - set gene_family name and rgs_file path
nano rbh_rbf_homologs_config.yaml
```

**Example rbh_rbf_homologs_config.yaml settings:**
```yaml
gene_family:
  name: "innexin_pannexin"
  rgs_file: "INPUT_user/rgs3-innexin_pannexin-uniprot-2025november01.aa"
```

**Prepare input files:**
```bash
# Place your RGS FASTA file in INPUT_user/
cp /path/to/your/rgs_file.aa INPUT_user/

# Create species keeper list (one Genus_species per line)
nano INPUT_user/species_keeper_list.tsv

# Create RGS species map if RGS uses short names (short_name<TAB>Genus_species)
nano INPUT_user/rgs_species_map.tsv
```

**Run locally:**
```bash
bash RUN-rbh_rbf_homologs.sh
```

**Run on SLURM:**
```bash
# Edit RUN-rbh_rbf_homologs.sbatch to set --account and --qos
sbatch RUN-rbh_rbf_homologs.sbatch
```

---

## Prerequisites

- **STEP_1-rgs_preparation** complete (provides validated RGS files)
- **genomesDB subproject** complete (provides BLAST databases and identifier mappings)
- **Conda environment** with `blastp`, `makeblastdb`, and `nextflow` installed
- **INPUT_user/** files prepared (RGS file, species keeper list, species map)

---

## Directory Structure

```
workflow-COPYME-rbh_rbf_homologs/
├── README.md                              # This file
├── RUN-rbh_rbf_homologs.sh               # Local runner (calls NextFlow)
├── RUN-rbh_rbf_homologs.sbatch           # SLURM wrapper
├── rbh_rbf_homologs_config.yaml          # User-editable configuration
├── INPUT_user/                            # User-provided inputs
│   ├── <rgs_file>.aa                      # RGS FASTA for this gene family
│   ├── species_keeper_list.tsv            # Species to keep in final output
│   └── rgs_species_map.tsv               # Short name to Genus_species mapping
├── OUTPUT_pipeline/                       # Workflow outputs (flat structure)
│   ├── 1-output/                          # BLAST database listing
│   ├── 2-output/                          # BLAST report listing
│   ├── 3-output/                          # BLAST reports (RGS vs project DB)
│   ├── 4-output/                          # Candidate gene sequences (CGS)
│   ├── 5-output/                          # RGS genome BLAST report listing
│   ├── 6-output/                          # RGS genome BLAST reports
│   ├── 7-output/                          # RBH species file listings
│   ├── 8-output/                          # RGS-to-genome identifier mapping
│   ├── 9-output/                          # Modified genomes
│   ├── 10-output/                         # Combined genomes + BLAST DB
│   ├── 11-output/                         # Reciprocal BLAST commands
│   ├── 12-output/                         # Reciprocal BLAST report
│   ├── 13-output/                         # Reciprocal best hit sequences
│   ├── 14-output/                         # Species-filtered sequences
│   ├── 15-output/                         # Remapped CGS identifiers
│   └── 16-output/                         # Final AGS (All Gene Set)
└── ai/
    ├── main.nf                            # NextFlow pipeline definition
    ├── nextflow.config                    # NextFlow settings
    └── scripts/
        ├── 001_ai-python-setup_block_directories.py
        ├── 002_ai-python-generate_blastp_commands-project_database.py
        ├── 004_ai-python-extract_gene_set_sequences.py
        ├── 005_ai-python-generate_blastp_commands-rgs_genomes.py
        ├── 007_ai-python-list_rgs_blast_files.py
        ├── 008_ai-python-map_rgs_to_reference_genomes.py
        ├── 009_ai-python-create_modified_genomes.py
        ├── 010_ai-python-generate_makeblastdb_commands.py
        ├── 011_ai-python-generate_reciprocal_blast_commands.py
        ├── 012_ai-bash-execute_reciprocal_blast.sh
        ├── 013_ai-python-extract_reciprocal_best_hits.py
        ├── 014_ai-python-filter_species_for_tree_building.py
        ├── 015_ai-python-remap_cgs_identifiers_to_gigantic.py
        └── 016_ai-python-concatenate_sequences.py
```

---

## Outputs

| Output | Location | Description |
|--------|----------|-------------|
| Database listing | `1-output/1_ai-list-projectdb-blastdbs` | Available BLAST databases |
| BLAST report list | `2-output/2_ai-list-projectdb-blast-reports` | Catalog of BLAST reports |
| BLAST reports | `3-output/3_ai-blast-report-*.blastp` | RGS vs project DB reports |
| CGS full sequences | `4-output/4_ai-cgs-*-fullseqs.aa` | Full-length candidate sequences |
| CGS hit regions | `4-output/4_ai-cgs-*-hitregions.aa` | BLAST hit region sequences |
| RGS genome reports | `6-output/6_ai-blast-report-*.blastp` | RGS vs RGS genome reports |
| RGS mapping | `8-output/8_ai-map-rgs-to-genome-identifiers.txt` | RGS-to-genome ID mapping |
| Modified genomes | `9-output/9_ai-*.aa-rgs` | Genomes with RGS sequences |
| Combined BLAST DB | `10-output/10_ai-rgs-all-genomes-combined-blastdb*` | Reciprocal BLAST database |
| Reciprocal report | `12-output/12_ai-reciprocal-blast-report.txt` | Reciprocal BLAST results |
| RBF sequences | `13-output/13_ai-rbf-*.aa` | Reciprocal best fit sequences |
| Filtered sequences | `14-output/14_ai-cgs-*-filtered.aa` | Species-filtered sequences |
| Remapped sequences | `15-output/15_ai-cgs-*-remapped.aa` | GIGANTIC phyloname identifiers |
| **Final AGS** | `16-output/16_ai-ags-*-homologs.aa` | **Final All Gene Set** |

---

## Next Step

After this workflow completes, copy the STEP_3 template and run phylogenetic analysis:
```bash
cd ../../STEP_3-phylogenetic_analysis/
cp -r workflow-COPYME-phylogenetic_analysis workflow-RUN_01-phylogenetic_analysis
```
