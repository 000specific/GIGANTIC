# trees_gene_groups - Gene Group Phylogenetic Analysis

Build phylogenetic trees for gene groups across GIGANTIC project species. Gene groups are defined by external classification systems (e.g., HUGO HGNC, Pfam), in contrast to trees_gene_families where reference sequences are hand-curated per family.

## Overview

This subproject uses a **source-based architecture**: each gene group source (HGNC, Pfam, custom) gets its own directory with a source-specific STEP_0 (RGS generation) and shared STEP_1/STEP_2 pipelines (homolog discovery + tree building).

The homolog discovery and phylogenetic analysis pipelines are identical to those in trees_gene_families.

## Architecture

```
trees_gene_groups/
├── gene_groups-COPYME/              # Template for new sources
│   ├── STEP_0-placeholder/          # Source customizes this
│   ├── STEP_1-homolog_discovery/    # Shared pipeline
│   └── STEP_2-phylogenetic_analysis/# Shared pipeline
│
├── gene_groups-hugo_hgnc/           # HUGO HGNC (first source, ~1,974 groups)
│   ├── STEP_0-hgnc_gene_groups/     # Downloads HGNC, generates RGS
│   ├── STEP_1-homolog_discovery/    # Per-gene-group homolog finding
│   └── STEP_2-phylogenetic_analysis/# Per-gene-group tree building
│
└── output_to_input/                 # Final outputs (step-centric)
    └── gene_groups-hugo_hgnc/
        ├── STEP_0-hgnc_gene_groups/ # All RGS files
        ├── STEP_1-homolog_discovery/# Per-gene-group AGS
        └── STEP_2-phylogenetic_analysis/ # Per-gene-group trees
```

## Three-Step Pipeline (Per Source)

| Step | Name | Runs | Purpose |
|------|------|------|---------|
| STEP_0 | RGS Generation | Once per source | Download gene group definitions, generate RGS FASTA files |
| STEP_1 | Homolog Discovery | Per gene group | Find homologs via RBH/RBF BLAST, produce AGS |
| STEP_2 | Phylogenetic Analysis | Per gene group | Align, trim, build trees, visualize |

## Quick Start (HUGO HGNC)

```bash
# 1. Run STEP_0 (generates all ~1,974 RGS files)
cd gene_groups-hugo_hgnc/STEP_0-hgnc_gene_groups/
cp -r workflow-COPYME-hgnc_gene_groups workflow-RUN_01-hgnc_gene_groups
cd workflow-RUN_01-hgnc_gene_groups/
# Edit START_HERE-user_config.yaml (set human_proteome_path)
bash RUN-workflow.sh

# 2. Run STEP_1 for ALL gene groups (burst mode)
cd ../../
bash RUN-setup_and_submit_step1_burst.sh

# Or for a single gene group:
bash RUN-setup_and_submit_step1_burst.sh --gene-group fascin_family

# 3. Run STEP_2 for all completed STEP_1 gene groups (burst mode)
bash RUN-setup_and_submit_step2_burst.sh

# Or for a single gene group:
bash RUN-setup_and_submit_step2_burst.sh --gene-group fascin_family
```

## Batch Processing (Burst Scripts)

Burst scripts at the source level (`gene_groups-hugo_hgnc/`) automate the copy-configure-submit workflow for all gene groups:

- **`RUN-setup_and_submit_step1_burst.sh`** - Reads STEP_0 summary, sets up and submits STEP_1 for all gene groups
- **`RUN-setup_and_submit_step2_burst.sh`** - Finds completed STEP_1 outputs, sets up and submits STEP_2

**Options**: `--dry-run`, `--setup-only`, `--submit-only`, `--gene-group NAME`

## Prerequisites

- **genomesDB** subproject must be complete (BLAST databases required)
- **phylonames** subproject must be complete (species naming)
- Conda environment: `ai_gigantic_trees_gene_families` (see `../../conda_environments/`)

## Adding a New Gene Group Source

```bash
cp -r gene_groups-COPYME gene_groups-pfam
# Replace STEP_0-placeholder with source-specific RGS generation
# Adjust paths in STEP_1 and STEP_2 configs
# Create AI_GUIDE-pfam.md
```

## Tree Methods Available (STEP_2)

| Method | Speed | Use When |
|--------|-------|----------|
| FastTree | Fast (minutes) | Default, exploratory analysis |
| IQ-TREE | Slow (hours-days) | Publication-quality, model selection |
| VeryFastTree | Very fast | Large datasets (>10,000 sequences) |
| PhyloBayes | Very slow (days-weeks) | Bayesian counterpoint to ML methods |

## Current Sources

| Source | Gene Groups | Status |
|--------|-------------|--------|
| HUGO HGNC | ~1,974 protein-coding groups | STEP_0 complete, STEP_1 all submitted, STEP_2 burst script ready |

## For AI Assistants

See `AI_GUIDE-trees_gene_groups.md` for detailed AI guidance.
