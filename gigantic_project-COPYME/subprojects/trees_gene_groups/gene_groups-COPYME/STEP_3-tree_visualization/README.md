# STEP_3: Tree Visualization

Render phylogenetic trees (produced by STEP_2) as PDF + SVG using toytree.

## Purpose

STEP_2 produces tree newick files — the scientific artifact. STEP_3 renders them as PDF and SVG figures for sharing and publication preparation.

This step is **decoupled** from STEP_2 deliberately: visualization is presentation, not science. A rendering issue never invalidates the underlying tree data.

## Quick Start

```bash
cp -r workflow-COPYME-tree_visualization workflow-RUN_1-tree_visualization
cd workflow-RUN_1-tree_visualization/
# Edit START_HERE-user_config.yaml (set gene_family.name to match STEP_2)
bash RUN-workflow.sh
```

## Prerequisites

- **STEP_2** must be complete for this gene group (tree newicks in `output_to_input/gene_groups-hugo_hgnc/STEP_2-phylogenetic_analysis/gene_group-<gene_family>/`)
- **Conda** available (env is created automatically on first run)

## Rendering Engine

Uses `toytree` + `toyplot` + `reportlab` (pure Python, no Qt). The conda env `aiG-trees_gene_groups-visualization` is created on first run. If the env is broken (e.g., from a prior failed install), `RUN-workflow.sh` detects this and rebuilds it automatically.

## What Gets Rendered

For each gene group, all tree methods that STEP_2 produced:

| Tree Method | Source File | Output |
|-------------|-------------|--------|
| FastTree | `*.fasttree` | `1_ai-visualization-<gene_family>-fasttree.pdf/.svg` |
| IQ-TREE | `*.treefile` | `1_ai-visualization-<gene_family>-iqtree.pdf/.svg` |
| VeryFastTree | `*.veryfasttree` | `1_ai-visualization-<gene_family>-veryfasttree.pdf/.svg` |
| PhyloBayes | `*.phylobayes.nwk` | `1_ai-visualization-<gene_family>-phylobayes.pdf/.svg` |

## Features

- **Species color-coding**: tip labels colored by species (parsed from GIGANTIC gene identifiers)
- **Branch support**: rendered when newick includes numeric node labels (bootstrap/aLRT/posterior)
- **Auto-scaling**: canvas sizes with tip count; tip labels auto-hidden for very large trees (>500 tips by default)
- **Soft-fail**: render failures write a placeholder + documented retry instructions; they never block downstream analysis

## Output

Rendered files are symlinked to:
- `../../output_to_input/gene_groups-hugo_hgnc/STEP_3-tree_visualization/gene_group-<gene_family>/`

## For AI Assistants

See `AI_GUIDE-phylogenetic_visualization.md` for detailed guidance.
