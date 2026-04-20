# workflow-COPYME-tree_visualization

GIGANTIC trees_gene_families STEP_3 workflow template. Renders phylogenetic trees (produced by STEP_2) as PDF + SVG using toytree.

## Purpose

Consumes tree newick files from:
- `../../output_to_input/<gene_family>/STEP_2-phylogenetic_analysis/`

Produces:
- `OUTPUT_pipeline/1-output/1_ai-visualization-<gene_family>-<method>.pdf`
- `OUTPUT_pipeline/1-output/1_ai-visualization-<gene_family>-<method>.svg`
- `OUTPUT_pipeline/1-output/1_ai-visualization_summary.md`

Symlinked into `../../../output_to_input/<gene_family>/STEP_3-tree_visualization/`.

## Usage

```bash
# 1. Copy the template (one workflow instance per gene family)
cp -r workflow-COPYME-tree_visualization workflow-RUN_1-tree_visualization
cd workflow-RUN_1-tree_visualization/

# 2. Configure (set gene family name to match STEP_2 run)
#    nano START_HERE-user_config.yaml

# 3. Run
bash RUN-workflow.sh
```

## What RUN-workflow.sh Does

1. Reads gene family name from `START_HERE-user_config.yaml`
2. Validates that STEP_2 output exists for this gene family
3. Activates the `aiG-trees_gene_families-visualization` conda env
   - Creates it if missing
   - Self-heals it if broken (from a prior partial install)
4. Runs Script 001 to render each tree file to PDF + SVG
5. Runs Script 002 to write the workflow run log
6. Creates symlinks in `output_to_input/<gene_family>/STEP_3-tree_visualization/`

## Soft-Fail Behavior

If rendering fails (toytree import error, corrupted newick, draw failure):
- Script 001 writes a placeholder text file documenting the failure
- Exits 0 (not 1)
- STEP_2 newick files remain the valid scientific artifact

This is intentional: **visualization is presentation, not science**. Rendering issues never invalidate the underlying trees.

## Directory Structure

```
workflow-COPYME-tree_visualization/
├── README.md                                  # This file
├── RUN-workflow.sh                            # Runner (broken-env detection + run)
├── START_HERE-user_config.yaml                # User config
├── INPUT_user/                                # (empty; reserved)
└── ai/
    ├── conda_environment.yml                  # aiG-trees_gene_families-visualization
    ├── AI_GUIDE-tree_visualization_workflow.md
    └── scripts/
        ├── 001_ai-python-render_trees.py      # Core renderer
        └── 002_ai-python-write_run_log.py
```

## Customizing Styling

Edit the `visualization:` block in `START_HERE-user_config.yaml`:

```yaml
visualization:
  show_tip_labels_max_tips: 500     # hide tip labels for trees > this
  color_tips_by_species: true
  tip_label_font_size_px: 11
  show_branch_support: true         # auto-detected from newick
  canvas_width_px: 1000
  canvas_height_per_tip_px: 20
  canvas_height_min_px: 900
```
