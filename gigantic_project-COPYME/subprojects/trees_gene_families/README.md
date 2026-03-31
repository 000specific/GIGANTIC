# trees_gene_families - Gene Family Phylogenetic Analysis

Build phylogenetic trees for individual gene families across GIGANTIC project species.

**Current scale**: 76 gene family analyses covering channels, receptors, enzymes (kinases, phosphatases), ligands, transporters, transcription factors, and structural proteins.

## Overview

This subproject takes curated reference gene sequences (RGS), finds homologs across all project species via reciprocal best hit/family (RBH/RBF) BLAST, and builds phylogenetic trees.

Each gene family is a **self-contained unit** with its own copy of the two-step pipeline.

The full workflow has three phases:

| Phase | Where | Purpose |
|-------|-------|---------|
| RGS Preparation | `research_notebook/` | Source, curate, and format reference gene sequences |
| STEP_1 | `gene_family-*/STEP_1-homolog_discovery/` | Validate RGS, find homologs via RBH/RBF BLAST |
| STEP_2 | `gene_family-*/STEP_2-phylogenetic_analysis/` | Align, trim, build trees, visualize |

## RGS Preparation (Before the Pipeline)

Before running the two-step pipeline, RGS FASTA files must be prepared in GIGANTIC standard format. This happens in `research_notebook/`.

**RGS filename format**: `rgs_<category>-<source_species>-<description>.aa`

**RGS header format**: `>rgs_<family_subfamily>-<species>-<gene>-<source>-<accession>`

Within each dash-separated field, only letters, numbers, and underscores are allowed. See `research_notebook/README.md` for full specification and examples.

**RGS sources include**: HGNC gene groups, UniProt, kinase/phosphatome databases, and curated sets from prior GIGANTIC work. Conversion scripts in `research_notebook/rgs_from_before/rgs_for_trees/` reformat legacy headers to GIGANTIC standard and produce mapping TSVs for traceability.

## Two-Step Pipeline

| Step | Name | Purpose |
|------|------|---------|
| STEP_1 | Homolog Discovery | Validate RGS, find homologs via RBH/RBF BLAST |
| STEP_2 | Phylogenetic Analysis | Align, trim, build trees, visualize |

**Note**: RGS validation is built into STEP_1 as its first process. If validation fails, the pipeline stops immediately before expensive BLAST runs.

## Directory Structure

```
trees_gene_families/
├── gene_family_COPYME/                    # Template (copy this for each gene family)
│   ├── STEP_1-homolog_discovery/
│   │   └── workflow-COPYME-rbh_rbf_homologs/
│   └── STEP_2-phylogenetic_analysis/
│       └── workflow-COPYME-phylogenetic_analysis/
│
├── gene_family-innexin_pannexin/          # User copy (example)
│   ├── STEP_1-homolog_discovery/
│   │   └── workflow-RUN_1-rbh_rbf_homologs/
│   └── STEP_2-phylogenetic_analysis/
│       └── workflow-RUN_1-phylogenetic_analysis/
│
├── output_to_input/                       # Shared outputs for downstream subprojects
├── upload_to_server/                      # Curated data for GIGANTIC server
├── research_notebook/                     # Personal notes and exploratory work
├── slurm_logs/                            # SLURM job logs from burst submissions
├── RUN-setup_and_submit_step1_burst.sh             # Burst: set up + submit STEP_1 (original RGS set)
├── RUN-setup_and_submit_step2_burst.sh             # Burst: set up + submit STEP_2 (with size filter)
├── RUN-setup_and_submit_new_rgs_31mar2026_burst.sh # Burst: STEP_1 for new RGS set (TRP, kinome, phosphatome, etc.)
├── RUN-clean_and_record_subproject.sh              # Cleanup temp files + record AI sessions
├── RUN-update_upload_to_server.sh                  # Update upload_to_server/ symlinks
├── AI_GUIDE-trees_gene_families.md
└── README.md
```

## Quick Start

```bash
# 1. Copy the gene family template
cp -r gene_family_COPYME gene_family-innexin_pannexin

# 2. Run STEP_1 (includes RGS validation + homolog discovery)
cd gene_family-innexin_pannexin/STEP_1-homolog_discovery/
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_1-rbh_rbf_homologs
cd workflow-RUN_1-rbh_rbf_homologs/
# Edit START_HERE-user_config.yaml (set gene_family name, rgs_file)
# Place RGS file and species_keeper_list.tsv in INPUT_user/
bash RUN-workflow.sh

# 3. Run STEP_2
cd ../../STEP_2-phylogenetic_analysis/
cp -r workflow-COPYME-phylogenetic_analysis workflow-RUN_1-phylogenetic_analysis
cd workflow-RUN_1-phylogenetic_analysis/
# Edit START_HERE-user_config.yaml (set gene_family name, choose tree methods)
bash RUN-workflow.sh
```

## Prerequisites

- **genomesDB** subproject must be complete (BLAST databases required)
- **phylonames** subproject must be complete (species naming)
- Conda environment: `ai_gigantic_trees_gene_families` (see `../../conda_environments/`)

## One Gene Family Per Directory

Each `gene_family-[name]/` directory is a complete, self-contained unit. To analyze multiple families, create multiple copies:

```bash
cp -r gene_family_COPYME gene_family-innexin_pannexin
cp -r gene_family_COPYME gene_family-wnt_ligands
cp -r gene_family_COPYME gene_family-nhr_nuclear_hormone_receptors
```

This keeps both steps together for each gene family, making it easy to manage and track progress per family.

## Output Location

Final outputs appear in `output_to_input/` at the subproject root:

```
output_to_input/
├── <gene_family>/
│   ├── STEP_1-homolog_discovery/   # Homolog sequences (AGS) - symlinks to workflow outputs
│   └── STEP_2-phylogenetic_analysis/   # Trees and visualizations - symlinks to workflow outputs
```

## Tree Methods Available (STEP_2)

| Method | Speed | Use When |
|--------|-------|----------|
| FastTree | Fast (minutes) | Default, exploratory analysis |
| IQ-TREE | Slow (hours-days) | Publication-quality, model selection |
| VeryFastTree | Very fast | Large datasets (>10,000 sequences) |
| PhyloBayes | Very slow (days-weeks) | Bayesian counterpoint to ML methods |

## Burst Mode: Running Multiple Gene Families on SLURM

When analyzing many gene families, manually copying templates and submitting jobs one at a time is tedious. Two **burst scripts** automate this entire process:

### RUN-setup_and_submit_step1_burst.sh

Automates STEP_1 (homolog discovery) for all gene families at once.

**What it does for each gene family:**
1. Creates `gene_family-[name]/` from `gene_family_COPYME/` template (if it doesn't exist)
2. Creates `workflow-RUN_1-rbh_rbf_homologs` from the COPYME workflow
3. Copies the RGS FASTA file and species keeper list into `INPUT_user/`
4. Updates `START_HERE-user_config.yaml` with gene family name and RGS file path
5. Submits a SLURM job

**Gene families are defined in the script** as a list pairing each gene family name with its RGS file. To add or remove gene families, edit the `GENE_FAMILIES` array in the script.

**User-configurable settings** (edit at top of script):
| Setting | Default | Purpose |
|---------|---------|---------|
| `SLURM_ACCOUNT` | moroz | SLURM account for billing |
| `SLURM_QOS` | moroz-b | SLURM quality of service (burst) |
| `SLURM_MEM` | 112gb | Memory per job (BLAST is memory-intensive) |
| `SLURM_TIME` | 24:00:00 | Wall time per job |
| `SLURM_CPUS` | 15 | CPUs per job (parallel BLAST) |

**Usage:**
```bash
# Preview what would happen (no changes made)
bash RUN-setup_and_submit_step1_burst.sh --dry-run

# Set up directories only (don't submit jobs yet)
bash RUN-setup_and_submit_step1_burst.sh --setup-only

# Submit jobs for already-set-up directories
bash RUN-setup_and_submit_step1_burst.sh --submit-only

# Full run: set up + submit everything
bash RUN-setup_and_submit_step1_burst.sh
```

### RUN-setup_and_submit_step2_burst.sh

Automates STEP_2 (phylogenetic analysis) for gene families that completed STEP_1.

**What it does for each gene family:**
1. Checks that STEP_1 completed (AGS file exists in `output_to_input/`)
2. Checks AGS sequence count against the `MAX_SEQS` size filter
3. Creates `workflow-RUN_1-phylogenetic_analysis` from the COPYME workflow
4. Updates `START_HERE-user_config.yaml` with gene family name
5. Submits a SLURM job

**Size filtering**: STEP_2 runtime scales significantly with AGS sequence count (MAFFT alignment and tree building). The `MAX_SEQS` setting (default: 2000) skips gene families that are too large for burst QOS. These larger families need dedicated SLURM jobs with more memory and time.

**User-configurable settings** (edit at top of script):
| Setting | Default | Purpose |
|---------|---------|---------|
| `SLURM_ACCOUNT` | moroz | SLURM account for billing |
| `SLURM_QOS` | moroz-b | SLURM quality of service (burst) |
| `SLURM_MEM` | 64gb | Memory per job |
| `SLURM_TIME` | 24:00:00 | Wall time per job |
| `SLURM_CPUS` | 8 | CPUs per job |
| `MAX_SEQS` | 2000 | Skip gene families with more AGS sequences than this |

**Usage:**
```bash
# Preview what would happen
bash RUN-setup_and_submit_step2_burst.sh --dry-run

# Set up directories only
bash RUN-setup_and_submit_step2_burst.sh --setup-only

# Submit jobs for already-set-up directories
bash RUN-setup_and_submit_step2_burst.sh --submit-only

# Override the size filter (e.g., only families <= 500 sequences)
bash RUN-setup_and_submit_step2_burst.sh --max-seqs 500

# Full run with default size filter
bash RUN-setup_and_submit_step2_burst.sh
```

### RUN-setup_and_submit_new_rgs_31mar2026_burst.sh

Same pattern as the STEP_1 burst script, but for **new RGS files** prepared in `research_notebook/rgs_from_before/rgs_for_trees/new_rgs_31mar2026/`. This script:

1. Automatically derives gene family names from RGS filenames
2. Creates gene_family directories from the COPYME template
3. Populates INPUT_user/ with the RGS file, species keeper list, and species map
4. Submits SLURM burst jobs

**Default burst resources** (configurable at top of script):
| Setting | Default | Purpose |
|---------|---------|---------|
| `SLURM_CPUS` | 100 | CPUs per job |
| `SLURM_MEM` | 750gb | Memory per job |
| `SLURM_TIME` | 96:00:00 | Wall time per job |

This script serves as a **template** for creating burst scripts for future RGS batches. Copy it, update the `RGS_SOURCE_DIR` path, and adjust SLURM resources as needed.

### Typical Workflow

```bash
# 1. Run all STEP_1 jobs (no size filter needed - BLAST scales with database, not RGS)
bash RUN-setup_and_submit_step1_burst.sh

# 2. Wait for STEP_1 to finish, then check AGS sizes
find -L output_to_input/*/STEP_1-homolog_discovery/ -name "*.aa" | \
    while read f; do echo "$(grep -c '>' "$f")  $f"; done | sort -n

# 3. Burst small/medium families through STEP_2
bash RUN-setup_and_submit_step2_burst.sh

# 4. Large families (above MAX_SEQS) need dedicated SLURM with more resources
#    Set up their workflow directories manually or with --setup-only,
#    then submit individually with appropriate resource requests
```

### SLURM Logs

All burst job logs go to `slurm_logs/` at the subproject root:
- STEP_1: `slurm_logs/step1_<gene_family>-<jobid>.log`
- STEP_2: `slurm_logs/step2_<gene_family>-<jobid>.log`

## For AI Assistants

See `AI_GUIDE-trees_gene_families.md` for detailed AI guidance.
