# AI Guide: STEP_3 Tree Visualization

**For AI Assistants**: Read `../../AI_GUIDE-project.md` first for GIGANTIC overview. Then read `../AI_GUIDE-trees_gene_groups.md` for subproject concepts. This guide covers STEP_3-specific details.

**Location**: `gene_groups-COPYME/STEP_1-.../workflow-COPYME/STEP_3-tree_visualization/`

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE-project.md` |
| Subproject concepts, three-phase architecture | `../AI_GUIDE-trees_gene_groups.md` |
| STEP_3 concepts (this file) | This file |
| Running the workflow | `workflow-COPYME-tree_visualization/ai/AI_GUIDE-tree_visualization_workflow.md` |

---

## What This Step Does

**Purpose**: Render gene group phylogenetic trees as PDF + SVG.

**Process**:
1. Discover tree newick files produced by STEP_2
2. For each, render to PDF + SVG with species color-coding and branch support
3. Write visualization summary
4. Create symlinks to `output_to_input/gene_groups-hugo_hgnc/STEP_3-tree_visualization/gene_group-<gene_family>/`

**Critical context**: STEP_3 is **decoupled** from STEP_2. The scientific artifact is the newick file (STEP_2 output). STEP_3 presentation never invalidates STEP_2 science. Implement with soft-fail behavior: on rendering errors, write a placeholder and exit 0.

---

## Rendering Engine

**toytree + toyplot + reportlab** (pure Python, no Qt/PyQt5 dependency).

Why not ete3? ete3 requires PyQt5 which is flaky on conda-forge — on this project alone two conda envs have become broken husks from partial installs. toytree removes the Qt dependency entirely.

Installed via pip inside conda env `aiG-trees_gene_groups-visualization`.

---

## Broken-Env Self-Heal

`RUN-workflow.sh` includes a broken-env detection pattern:
1. Check if env directory exists
2. If directory exists but `bin/python` is missing, remove and rebuild
3. If env doesn't exist at all, create fresh from `ai/conda_environment.yml`

This pattern originated in `trees_species/BLOCK_user_requests` and has proven robust against partial-install failures.

---

## Tree Files Consumed

STEP_3 auto-discovers tree newick files in `output_to_input/gene_groups-hugo_hgnc/STEP_2-phylogenetic_analysis/gene_group-<gene_family>/` matching these suffixes:

| Suffix | Tree method |
|--------|-------------|
| `*.fasttree` | FastTree |
| `*.treefile` | IQ-TREE (ML with UFBoot/aLRT) |
| `*.veryfasttree` | VeryFastTree |
| `*.phylobayes.nwk` | PhyloBayes consensus |

If a method is disabled in STEP_2, no matching file exists → STEP_3 silently skips it.

---

## Gene Tree Styling

Unlike species trees (bounded, ~70 tips, species names familiar), gene trees can be:
- Hundreds to thousands of tips
- Labeled with gene identifiers (not species)
- Include numeric branch support values

STEP_3 handles these via:

1. **Species color-coding**: tip labels colored by species parsed from GIGANTIC identifier format
   - RGS format: `rgs_FAMILY-SPECIES-GENE-SOURCE-ID` → species from `parts[1]`
   - Genome format: `g_GENE-t_TRANSCRIPT-p_PROTEIN-n_...Genus_species` → Genus_species from taxonomy
2. **Auto-scaling canvas**: `max(900px, 20px × ntips + 200px)`
3. **Auto-hide tip labels** for trees > `show_tip_labels_max_tips` (default 500) — tree shape remains visible
4. **Branch support auto-detection**: if newick contains numeric internal node labels, render them

---

## Directory Structure

```
STEP_3-tree_visualization/
├── AI_GUIDE-phylogenetic_visualization.md    # THIS FILE
├── README.md
└── workflow-COPYME-tree_visualization/
    ├── README.md
    ├── RUN-workflow.sh                        # Broken-env detection + run script
    ├── START_HERE-user_config.yaml
    ├── INPUT_user/                            # (empty; reserved for future overrides)
    └── ai/
        ├── conda_environment.yml              # aiG-trees_gene_groups-visualization
        ├── AI_GUIDE-tree_visualization_workflow.md
        └── scripts/
            ├── 001_ai-python-render_trees.py  # Core rendering (soft-fail)
            └── 002_ai-python-write_run_log.py
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `workflow-*/START_HERE-user_config.yaml` | Gene family name, styling options | **YES** (gene_family.name at minimum) |
| `workflow-*/ai/conda_environment.yml` | Env definition | No (auto-applied on first run) |
| `workflow-*/ai/scripts/001_ai-python-render_trees.py` | Rendering logic | No (soft-fail by design) |
| `../../output_to_input/gene_groups-hugo_hgnc/STEP_3-tree_visualization/gene_group-<gene_family>/` | Rendered PDFs/SVGs | No (auto-created symlinks) |

---

## Resource Requirements

| Aspect | Value |
|--------|-------|
| CPUs | 2 (single-process Python) |
| Memory | 8 GB |
| Time | Seconds to minutes per gene group |

STEP_3 is lightweight and rarely needs SLURM. Default `execution_mode: local`.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "No tree files found" | STEP_2 not complete for this gene group | Run STEP_2 first |
| "toytree import failed" | Conda env broken or not activated | Delete env and re-run (RUN-workflow.sh auto-rebuilds) |
| Tip labels unreadable | Tree has many tips | Lower `show_tip_labels_max_tips` (e.g., to 200) to hide labels sooner |
| Wrong species colors | Unusual tip label format | Check `extract_species_from_label()` in render_trees.py; may need pattern addition |
| PDF/SVG too tall | Large tree | Reduce `canvas_height_per_tip_px` in config |

### Diagnostic Commands

```bash
# Verify STEP_2 outputs exist
find -L ../../../output_to_input/gene_groups-hugo_hgnc/STEP_2-phylogenetic_analysis/gene_group-<gene_family>/ -name "*.treefile" -o -name "*.fasttree"

# Verify conda env is healthy
conda activate aiG-trees_gene_groups-visualization
python3 -c "import toytree, toyplot; print(toytree.__version__, toyplot.__version__)"

# Check rendered outputs
ls OUTPUT_pipeline/1-output/
```

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| Starting STEP_3 | "Has STEP_2 completed for this gene group? Which tree methods ran?" |
| Very large tree | "Do you want tip labels visible (may be unreadable) or hidden (tree shape only)?" |
| Publication figure | "Do you want branch support shown? SVG format is editable in Illustrator/Inkscape." |
| Broken env | "Should I delete the conda env and let RUN-workflow.sh rebuild it?" |

---

## Why STEP_3 is Separate

Historical context: an earlier GIGANTIC pipeline embedded visualization inside STEP_2 (trees + rendering in one workflow). This caused three recurring problems:

1. **ete3/PyQt5 install failures** on conda-forge would fail the whole STEP_2 run
2. **Iteration cost**: tweaking a figure required rebuilding trees (potentially days)
3. **False "complete" status** when rendering silently failed but trees succeeded

Separating into STEP_3 solves all three:
- Rendering env is its own small conda env; its failures are isolated
- Figure iteration is seconds instead of days
- Rendering is explicitly soft-fail; STEP_2 status is never confused by rendering outcomes
