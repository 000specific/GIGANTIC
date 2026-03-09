# trees_gene_families - Gene Family Phylogenetic Analysis

Build phylogenetic trees for individual gene families across GIGANTIC project species.

## Overview

This subproject takes curated reference gene sequences (RGS), finds homologs across all project species via reciprocal best hit/family (RBH/RBF) BLAST, and builds phylogenetic trees.

Each gene family is a **self-contained unit** with its own copy of the three-step pipeline.

## Three-Step Pipeline

| Step | Name | Purpose |
|------|------|---------|
| STEP_1 | RGS Preparation | Validate reference gene set FASTA files |
| STEP_2 | Homolog Discovery | Find homologs via RBH/RBF BLAST |
| STEP_3 | Phylogenetic Analysis | Align, trim, build trees, visualize |

## Directory Structure

```
trees_gene_families/
├── gene_family_COPYME/                    # Template (copy this for each gene family)
│   ├── STEP_1-rgs_preparation/
│   │   └── workflow-COPYME-validate_rgs/
│   ├── STEP_2-homolog_discovery/
│   │   └── workflow-COPYME-rbh_rbf_homologs/
│   └── STEP_3-phylogenetic_analysis/
│       └── workflow-COPYME-phylogenetic_analysis/
│
├── gene_family-innexin_pannexin/          # User copy (example)
│   ├── STEP_1-rgs_preparation/
│   │   └── workflow-RUN_1-validate_rgs/
│   ├── STEP_2-homolog_discovery/
│   │   └── workflow-RUN_1-rbh_rbf_homologs/
│   └── STEP_3-phylogenetic_analysis/
│       └── workflow-RUN_1-phylogenetic_analysis/
│
├── output_to_input/                       # Shared outputs for downstream subprojects
├── upload_to_server/                      # Curated data for GIGANTIC server
├── research_notebook/                     # Personal notes and exploratory work
├── AI_GUIDE-trees_gene_families.md
└── README.md
```

## Quick Start

```bash
# 1. Copy the gene family template
cp -r gene_family_COPYME gene_family-innexin_pannexin

# 2. Run STEP_2 (STEP_1 validation is optional)
cd gene_family-innexin_pannexin/STEP_2-homolog_discovery/
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_1-rbh_rbf_homologs
cd workflow-RUN_1-rbh_rbf_homologs/
# Edit START_HERE-user_config.yaml (set gene_family name, rgs_file)
# Place RGS file and species_keeper_list.tsv in INPUT_user/
bash RUN-workflow.sh

# 3. Run STEP_3
cd ../../STEP_3-phylogenetic_analysis/
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

This keeps all three steps together for each gene family, making it easy to manage and track progress per family.

## Output Location

Final outputs appear in `output_to_input/` at the subproject root:

```
output_to_input/
├── STEP_1-rgs_preparation/rgs_fastas/<gene_family>/     # Validated RGS
├── STEP_2-homolog_discovery/ags_fastas/<gene_family>/   # Homolog sequences (AGS)
└── STEP_3-phylogenetic_analysis/trees/<gene_family>/    # Trees and visualizations
```

## Tree Methods Available (STEP_3)

| Method | Speed | Use When |
|--------|-------|----------|
| FastTree | Fast (minutes) | Default, exploratory analysis |
| IQ-TREE | Slow (hours-days) | Publication-quality, model selection |
| VeryFastTree | Very fast | Large datasets (>10,000 sequences) |
| PhyloBayes | Very slow (days-weeks) | Bayesian counterpoint to ML methods |

## For AI Assistants

See `AI_GUIDE-trees_gene_families.md` for detailed AI guidance.
