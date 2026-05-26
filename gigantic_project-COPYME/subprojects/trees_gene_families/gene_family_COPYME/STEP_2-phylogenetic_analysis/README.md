# STEP_2: Phylogenetic Analysis

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 February (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (subproject): [`../../README.md`](../../README.md) — trees_gene_families overview
- STEP-level AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)
- Workflow template: [`workflow-COPYME-phylogenetic_analysis/`](workflow-COPYME-phylogenetic_analysis/)
- Reads FROM: `../../../output_to_input/<gene_family>/STEP_1-homolog_discovery/` (final AGS from STEP_1)
- Outputs TO: `../../../output_to_input/<gene_family>/STEP_2-phylogenetic_analysis/` — newick trees + alignments
- Downstream STEP: `../STEP_3-tree_visualization/` for PDF/SVG rendering
- 9 scripts (001-006, with 005 a/b/c/d for FastTree/IQ-TREE/VeryFastTree/PhyloBayes); 006 = `write_run_log` (canonical final per §45)

---

Build phylogenetic trees from homolog sequences identified in STEP_1.

## Purpose

Takes the All Gene Set (AGS) from STEP_1, aligns sequences with MAFFT, trims with ClipKit, and builds trees with one or more methods.

Tree visualization (PDF/SVG rendering) is handled by the separate **STEP_3-tree_visualization** workflow, which consumes the newick files produced here.

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

Alignments and tree newick files are symlinked to:
- `../../output_to_input/<gene_family>/STEP_2-phylogenetic_analysis/`

These are then picked up by `STEP_3-tree_visualization` for PDF/SVG rendering.

## For AI Assistants

See `AI_GUIDE.md` for detailed AI guidance.
