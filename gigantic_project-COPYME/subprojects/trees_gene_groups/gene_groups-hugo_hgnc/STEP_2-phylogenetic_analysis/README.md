# STEP_2: Phylogenetic Analysis

Build phylogenetic trees from homolog sequences identified in STEP_1.

## Purpose

Takes the All Gene Set (AGS) from STEP_1, aligns sequences with MAFFT, trims with ClipKit, builds trees with one or more methods, and generates visualizations.

## Quick Start

```bash
cp -r workflow-COPYME-phylogenetic_analysis workflow-RUN_01-phylogenetic_analysis
cd workflow-RUN_01-phylogenetic_analysis/
# Edit START_HERE-user_config.yaml (set gene_family name, choose tree methods)
bash RUN-workflow.sh
```

## Prerequisites

- STEP_1 must be complete for the same gene family (AGS file in output_to_input/<gene_family>/STEP_1-homolog_discovery/)

## Tree Methods

| Method | Default | Speed | Use When |
|--------|---------|-------|----------|
| FastTree | ON | Minutes | Default, exploratory |
| IQ-TREE | OFF | Hours-days | Publication-quality |
| VeryFastTree | OFF | Very fast | Large datasets (>10,000 seqs) |
| PhyloBayes | OFF | Days-weeks | Bayesian counterpoint |

Enable/disable methods in `START_HERE-user_config.yaml`.

## Output

Trees and visualizations are copied to:
- `../../output_to_input/<gene_family>/STEP_2-phylogenetic_analysis/`

## For AI Assistants

See `AI_GUIDE-phylogenetic_analysis.md` for detailed AI guidance.
