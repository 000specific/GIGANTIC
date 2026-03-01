# trees_gene_groups - Gene Group Phylogenetic Analysis

Build phylogenetic trees for gene groups (orthogroup-derived sets) across GIGANTIC project species.

## Overview

This subproject takes curated reference gene sequences (RGS), finds homologs across all project species via reciprocal best hit/family (RBH/RBF) BLAST, and builds phylogenetic trees. It uses the identical pipeline as trees_gene_families but operates on gene groups rather than individually curated gene families.

## Three-Step Pipeline

| Step | Name | Purpose |
|------|------|---------|
| STEP_1 | RGS Preparation | Validate reference gene set FASTA files |
| STEP_2 | Homolog Discovery | Find homologs via RBH/RBF BLAST |
| STEP_3 | Phylogenetic Analysis | Align, trim, build trees, visualize |

## Quick Start

```bash
# 1. Run STEP_2 (STEP_1 is optional)
cd STEP_2-homolog_discovery/
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_01-rbh_rbf_homologs
cd workflow-RUN_01-rbh_rbf_homologs/
# Edit rbh_rbf_homologs_config.yaml (set gene_group name, rgs_file)
# Place RGS file and species_keeper_list.tsv in INPUT_user/
bash RUN-workflow.sh

# 2. Run STEP_3
cd ../../STEP_3-phylogenetic_analysis/
cp -r workflow-COPYME-phylogenetic_analysis workflow-RUN_01-phylogenetic_analysis
cd workflow-RUN_01-phylogenetic_analysis/
# Edit phylogenetic_analysis_config.yaml (set gene_group name, choose tree methods)
bash RUN-workflow.sh
```

## Prerequisites

- **genomesDB** subproject must be complete (BLAST databases required)
- **phylonames** subproject must be complete (species naming)
- Conda environment: `ai_gigantic_trees_gene_groups` (see `../../conda_environments/`)

## One Gene Group Per Run

Each workflow copy processes one gene group. To analyze multiple groups:

```bash
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_01-rbh_rbf_homologs  # group_1
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_02-rbh_rbf_homologs  # group_2
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_03-rbh_rbf_homologs  # group_3
```

## Output Location

Final outputs appear in `output_to_input/`:

```
output_to_input/
├── step_1/rgs_fastas/<gene_group>/     # Validated RGS
├── step_2/ags_fastas/<gene_group>/     # Homolog sequences (AGS)
└── step_3/trees/<gene_group>/          # Trees and visualizations
```

## Tree Methods Available (STEP_3)

| Method | Speed | Use When |
|--------|-------|----------|
| FastTree | Fast (minutes) | Default, exploratory analysis |
| IQ-TREE | Slow (hours-days) | Publication-quality, model selection |
| VeryFastTree | Very fast | Large datasets (>10,000 sequences) |
| PhyloBayes | Very slow (days-weeks) | Bayesian counterpoint to ML methods |

## For AI Assistants

See `AI_GUIDE-trees_gene_groups.md` for detailed AI guidance.
