# workflow-COPYME-tree_visualization

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent STEP: [`../README.md`](../README.md)
- Parent (template): [`../../../README.md`](../../../README.md)
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Reads from: `../../../../../output_to_input/<gene_group>/STEP_2-phylogenetic_analysis/`
- Outputs to: `../../../../../output_to_input/<gene_group>/STEP_3-tree_visualization/`

---

STEP_3 workflow template (orchestrator) for trees_gene_groups. Renders trees
produced by STEP_2 as PDF + SVG via toytree.

## Single user-runnable script

```bash
# 1. Copy this COPYME → RUN_NN at the same level
#    (e.g., inside gene_groups-<INSTANCE>/STEP_3-tree_visualization/):
cp -r workflow-COPYME-tree_visualization workflow-RUN_1-tree_visualization
cd workflow-RUN_1-tree_visualization

# 2. Edit START_HERE-user_config.yaml (set execution_mode, styling)

# 3. Run
bash RUN-workflow.sh
```

## What `RUN-workflow.sh` does (orchestrator)

1. Creates/heals the conda env `aiG-trees_gene_groups-visualization` once on the
   login node from `ai/conda_environment.yml` (broken-env self-heal: rebuilds if `bin/python` is missing)
2. Iterates the STEP_0 summary TSV (`gene_group_source_tsv` in config)
3. For each gene group **with STEP_2 newicks** at `step2_output_to_input_dir/gene_group-<name>/`:
   - Creates `gene_group-X/workflow-RUN_01-tree_visualization/` as a sibling at this STEP_3 directory level
   - Sed-patches `gene_family.name` in its YAML
4. Categorizes by RGS sequence count (small/large tier)
5. Dispatches per `execution_mode`:
   - `local` — sequential local renders (default; rendering is fast)
   - `slurm-standard` — 1 sbatch per gene group, standard QOS
   - `slurm-burst` — chunked, 1 sbatch per block, burst QOS

## Soft-Fail Behavior

Rendering errors write a placeholder and exit 0. STEP_2 newick files remain the
valid scientific artifact regardless of render outcome.

## Per-gene-group rendering (no nextflow)

Each per-gene-group RUN_01 runs two python scripts directly (no NextFlow — STEP_3 is a single lightweight process):
- `ai/scripts/001_ai-python-render_trees.py` — auto-discovers STEP_2 newicks, renders each to PDF + SVG (soft-fail)
- `ai/scripts/002_ai-python-write_run_log.py` — pipeline run log

## Configuration

| Setting | Choices | What |
|---------|---------|------|
| `execution_mode` | `local` \| `slurm-standard` \| `slurm-burst` | Dispatch strategy |
| `gene_group_source_tsv` | Path | STEP_0 summary |
| `step2_output_to_input_dir` | Path | Where STEP_2 newicks live |
| `large_threshold` | Integer | RGS seq count splitting small/large tiers |
| `slurm_*` | Strings/numbers | SLURM identifiers and resources per tier |
| `visualization.*` | Various | Tip-label visibility, colors, canvas sizes |

## Outputs

| Output | Location |
|--------|----------|
| PDF + SVG per (gene group × tree method) | `../gene_group-X/workflow-RUN_01-tree_visualization/OUTPUT_pipeline/1-output/1_ai-visualization-<gene_family>-<method>.{pdf,svg}` |
| Visualization summary | Same dir: `1_ai-visualization_summary.md` |
| Symlinks for server upload | `../../../../output_to_input/<source>/STEP_3-tree_visualization/gene_group-X/*.{pdf,svg}` |
| SLURM logs | `../slurm_logs/` (when execution_mode is slurm-*) |
