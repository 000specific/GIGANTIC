# AI Guide: tree_visualization Workflow

**For AI Assistants**: Read `../../AI_GUIDE-phylogenetic_visualization.md` first for STEP_3 concepts. This guide covers workflow execution specifics.

**Location**: `STEP_3-tree_visualization/workflow-COPYME-tree_visualization/ai/`

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| Project overview | `../../../../AI_GUIDE-project.md` |
| Subproject concepts | `../../../AI_GUIDE-trees_gene_groups.md` |
| STEP_3 concepts, why separated from STEP_2 | `../../AI_GUIDE-phylogenetic_visualization.md` |
| Workflow execution (this file) | This file |

---

## Architecture

Two scripts, plain bash orchestration (no NextFlow — this workflow is single-process and lightweight):

```
RUN-workflow.sh
  ├── validates STEP_2 output exists
  ├── creates/heals conda env (aiG-trees_gene_groups-visualization)
  ├── runs 001_ai-python-render_trees.py (soft-fail)
  ├── runs 002_ai-python-write_run_log.py
  └── creates symlinks in output_to_input/
```

## Script Pipeline

| Script | Purpose | Fail Mode |
|--------|---------|-----------|
| 001_ai-python-render_trees.py | Discover STEP_2 newicks, render each to PDF + SVG | Soft-fail (writes placeholder, exits 0) |
| 002_ai-python-write_run_log.py | Write timestamped run log to ai/logs/ | Hard-fail (propagates exit code) |

## Expected Runtime

- Small gene groups (< 100 tips): seconds
- Medium (100-500 tips): seconds to minutes
- Large (> 1000 tips): minutes
- Very large (> 10,000 tips): minutes (labels auto-hidden)

## User Workflow

### Step 1: Copy Template

```bash
cp -r workflow-COPYME-tree_visualization workflow-RUN_1-tree_visualization
cd workflow-RUN_1-tree_visualization/
```

### Step 2: Configure

Edit `START_HERE-user_config.yaml`:

```yaml
gene_family:
  name: "innexin_pannexin"   # must match STEP_2 output dir

input:
  output_to_input_dir: "../../../output_to_input"

visualization:
  show_tip_labels_max_tips: 500
  color_tips_by_species: true
  show_branch_support: true
  # ... other styling options
```

### Step 3: Run

```bash
bash RUN-workflow.sh
```

## Verification Commands

```bash
# Verify STEP_2 outputs are in place
find -L ../../../../output_to_input/gene_groups-hugo_hgnc/STEP_2-phylogenetic_analysis/gene_group-<gene_family>/ -name "*.treefile" -o -name "*.fasttree"

# Check conda env health
conda activate aiG-trees_gene_groups-visualization
python3 -c "import toytree, toyplot, reportlab; print('env OK')"

# Inspect rendered outputs
ls OUTPUT_pipeline/1-output/
cat OUTPUT_pipeline/1-output/1_ai-visualization_summary.md

# If soft-fail triggered, read the placeholder
cat OUTPUT_pipeline/1-output/1_ai-visualization-placeholder.txt
```

## Common Execution Issues

### "No tree files found"

STEP_2 hasn't produced trees for this gene group. Run STEP_2 first.

### "toytree import failed"

The conda env is broken. RUN-workflow.sh should self-heal this, but if it persists:

```bash
conda env remove -n aiG-trees_gene_groups-visualization -y
bash RUN-workflow.sh   # will recreate from scratch
```

### "Failed to parse newick"

The tree file is malformed (unusual). Inspect:

```bash
head -c 500 ../../../../output_to_input/gene_groups-hugo_hgnc/STEP_2-phylogenetic_analysis/gene_group-<gene_family>/*.fasttree
```

### Tip labels unreadable in rendered PDF

Tree has too many tips for the current canvas. Either:
- Lower `show_tip_labels_max_tips` in config (hide labels sooner)
- Increase `canvas_height_per_tip_px` (taller canvas, each tip gets more space)

### Wrong species colors

Species parsing from tip labels didn't match expected patterns. Check `extract_species_from_label()` in `001_ai-python-render_trees.py`. Two patterns are supported:
- RGS headers (`rgs_FAMILY-SPECIES-...`)
- Genome protein headers (`...-n_Kingdom_..._Genus_species`)

## After Successful Run

1. Verify `1_ai-visualization_summary.md` lists all expected tree methods
2. Open a PDF to confirm rendering quality
3. Check symlinks: `ls -l ../../../../output_to_input/gene_groups-hugo_hgnc/STEP_3-tree_visualization/gene_group-<gene_family>/`
4. Share PDFs with collaborators or use SVGs for publication figure prep
