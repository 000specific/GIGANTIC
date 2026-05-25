# STEP_3 — Tree Visualization

Per-source STEP_3: render the tree newicks produced by STEP_2 as PDF + SVG using
toytree (pure Python, no Qt).

## Single user-runnable script

```bash
# 1. Inside the per-source instance (e.g., gene_groups-<INSTANCE>/STEP_3-tree_visualization/),
#    copy the COPYME → RUN_NN at the same level:
cp -r workflow-COPYME-tree_visualization workflow-RUN_1-tree_visualization

# 2. Edit RUN's config (execution_mode, styling):
cd workflow-RUN_1-tree_visualization
# edit START_HERE-user_config.yaml

# 3. Run
bash RUN-workflow.sh
```

`RUN-workflow.sh` is an **orchestrator** that processes all gene groups with
STEP_2 newick output:

1. Creates the conda env once on the login node (or self-heals a broken env)
2. For each gene group with newicks at `output_to_input/<source>/STEP_2-phylogenetic_analysis/gene_group-<name>/`:
   creates `gene_group-X/workflow-RUN_01-tree_visualization/` as a sibling
3. Dispatches per `execution_mode`:
   - `local` — sequential renders (default; rendering is lightweight)
   - `slurm-standard` — one sbatch per gene group, standard QOS
   - `slurm-burst` — chunked, one sbatch per block, burst QOS

## Prerequisites

STEP_2 must have completed for at least some gene groups (newick files present).
Gene groups without STEP_2 newicks are skipped.

## Rendering engine

`toytree` + `toyplot` + `reportlab` — pure Python, no Qt/PyQt5. Replaces ete3
which had recurring install-instability problems.

## Soft-fail behavior

STEP_3 rendering is **soft-fail by design**: a render failure writes a
placeholder text file and exits 0. STEP_2 newicks remain the valid scientific
artifact regardless of rendering outcome.

## Output

| Output | Location |
|--------|----------|
| Rendered PDFs/SVGs | `../gene_group-X/workflow-RUN_01-tree_visualization/OUTPUT_pipeline/1-output/1_ai-visualization-<gene_family>-<method>.{pdf,svg}` |
| Symlinks for server upload | `../../../../output_to_input/<source>/STEP_3-tree_visualization/gene_group-X/*.{pdf,svg}` |

## See also

- `AI_GUIDE-phylogenetic_visualization.md` — detailed AI guide
- `workflow-COPYME-tree_visualization/ai/AI_GUIDE-tree_visualization_workflow.md` — workflow execution guide
