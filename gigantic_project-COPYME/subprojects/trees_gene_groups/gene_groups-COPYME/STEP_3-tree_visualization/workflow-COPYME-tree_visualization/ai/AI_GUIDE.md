# AI Guide: tree_visualization Workflow (trees_gene_groups STEP_3)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent STEP guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md)
- Parent (template): [`../../../../README.md`](../../../../README.md)
- Workflow README: [`../README.md`](../README.md)
- Conda env: `aiG-trees_gene_groups-visualization`

---

**For AI Assistants**: Read `../../AI_GUIDE.md` first for STEP_3 concepts. This guide covers workflow execution.

**Location**: `gene_groups_COPYME/STEP_3-tree_visualization/workflow-COPYME-tree_visualization/`

---

## Single user-runnable script

The COPYME's `RUN-workflow.sh` is the ONE script the user invokes. Always orchestrator mode. User flow:

```bash
cp -r workflow-COPYME-tree_visualization workflow-RUN_1-tree_visualization
cd workflow-RUN_1-tree_visualization
# edit START_HERE-user_config.yaml
bash RUN-workflow.sh
```

## Orchestrator behavior

`RUN-workflow.sh` reads `START_HERE-user_config.yaml` and:

1. Creates the conda env `aiG-trees_gene_groups-visualization` ONCE on the
   login node, before any sbatch. Includes broken-env self-heal: if env dir
   exists but `bin/python` is missing, it rebuilds (common from a prior failed pip install).
2. Iterates `gene_group_source_tsv` (STEP_0 summary).
3. For each gene group with STEP_2 newicks at `step2_output_to_input_dir/gene_group-<name>/`:
   - Creates sibling `gene_group-X/workflow-RUN_01-tree_visualization/` at the parent STEP_3 dir level
   - Sed-patches `gene_family.name` in its YAML
   - Skips if no STEP_2 newicks for that gene group (STEP_2 not done yet)
4. Categorizes by RGS sequence count (small/large tier; both are small in resource terms).
5. Dispatches per `execution_mode`:
   - `local` — sequential renders (default; lightweight)
   - `slurm-standard` — 1 sbatch per gene group, standard QOS
   - `slurm-burst` — chunked, 1 sbatch per BLOCK, burst QOS

## Per-gene-group render (no NextFlow)

Each per-gene-group sub-RUN runs two python scripts directly:

| Script | Purpose | Fail mode |
|--------|---------|-----------|
| `ai/scripts/001_ai-python-render_trees.py` | Auto-discover STEP_2 newicks, render each to PDF + SVG | Soft-fail (writes placeholder, exits 0) |
| `ai/scripts/002_ai-python-write_run_log.py` | Pipeline run log | Hard-fail (propagates exit code) |

No NextFlow needed — rendering is single-process, lightweight.

## YAML schema (key fields)

```yaml
execution_mode: "local"
gene_group_source_tsv: "<path to STEP_0 summary>"
step2_output_to_input_dir: "<path to STEP_2 output_to_input dir>"
large_threshold: 50
slurm_account: "moroz"
slurm_qos_standard: "moroz"
slurm_qos_burst: "moroz-b"
small_cpus: 2; small_memory_gb: 8;  small_time_hours: 2; small_time_hours_burst: 12; small_burst_block_size: 50
large_cpus: 2; large_memory_gb: 16; large_time_hours: 4; large_time_hours_burst: 24; large_burst_block_size: 20

# Per-gene-group settings (template through to each RUN_01):
gene_family:    { name }
input:          { output_to_input_dir }
visualization:  { show_tip_labels_max_tips, color_tips_by_species, tip_label_font_size_px,
                  show_branch_support, branch_support_font_size_px,
                  canvas_width_px, canvas_height_per_tip_px, canvas_height_min_px }
output:         { base_dir }
```

## Conda env

`aiG-trees_gene_groups-visualization` — defined in `ai/conda_environment.yml`.

Pip-installed inside conda: toytree, toyplot, reportlab. Replaces ete3 (Qt-dependent, unstable on conda-forge).

Self-heal: if `bin/python` is missing from the env dir, rebuild from yml.

## Tip color coding

Species parsed from tip labels:
- RGS headers: `rgs_FAMILY-SPECIES-GENE-SOURCE-ID` → species from `parts[1]`
- Genome headers: `g_GENE-t_TRANSCRIPT-p_PROTEIN-n_...Genus_species` → Genus_species from taxonomy

Auto-hide tip labels for trees > `show_tip_labels_max_tips` (default 500).

## Verification (after a successful run)

```bash
# Count rendered files per gene group
for d in ../gene_group-*/workflow-RUN_01-tree_visualization/OUTPUT_pipeline/1-output; do
  echo "$d"
  ls "$d"/*.{pdf,svg} 2>/dev/null | wc -l
done

# Output_to_input symlinks
ls -l ../../../../output_to_input/<source>/STEP_3-tree_visualization/gene_group-*/
```
