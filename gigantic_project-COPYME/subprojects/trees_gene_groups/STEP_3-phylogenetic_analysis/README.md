# STEP_3: Phylogenetic Analysis

Build phylogenetic trees from homolog sequences identified in STEP_2.

## Purpose

Takes the All Gene Set (AGS) from STEP_2, aligns sequences with MAFFT, trims with ClipKit, builds trees with one or more methods, and generates visualizations.

## Quick Start

```bash
cp -r workflow-COPYME-phylogenetic_analysis workflow-RUN_01-phylogenetic_analysis
cd workflow-RUN_01-phylogenetic_analysis/
# Edit phylogenetic_analysis_config.yaml (set gene_group name, choose tree methods)
bash RUN-workflow.sh
```

## Prerequisites

- STEP_2 must be complete for the same gene group (AGS file in output_to_input)

## Tree Methods

| Method | Default | Speed | Use When |
|--------|---------|-------|----------|
| FastTree | ON | Minutes | Default, exploratory |
| IQ-TREE | OFF | Hours-days | Publication-quality |
| VeryFastTree | OFF | Very fast | Large datasets (>10,000 seqs) |
| PhyloBayes | OFF | Days-weeks | Bayesian counterpoint |

Enable/disable methods in `phylogenetic_analysis_config.yaml`.

## Output

Trees and visualizations are copied to:
- `output_to_input/trees/<gene_group>/`

## For AI Assistants

See `AI_GUIDE-phylogenetic_analysis.md` for detailed AI guidance.
