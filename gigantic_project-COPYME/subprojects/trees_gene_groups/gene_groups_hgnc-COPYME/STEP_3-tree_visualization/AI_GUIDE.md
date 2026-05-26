# AI Guide: STEP_3 — Tree Visualization (trees_gene_groups)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent STEP README: [`README.md`](README.md)
- Parent (template): [`../README.md`](../README.md)
- Parent (subproject AI guide): [`../../AI_GUIDE.md`](../../AI_GUIDE.md)
- Reads FROM: `../../../../output_to_input/<gene_group>/STEP_2-phylogenetic_analysis/`
- Conda env: `aiG-trees_gene_groups-visualization`

---

**For AI Assistants**: Read `../../../AI_GUIDE.md` first for GIGANTIC overview. Then `../../AI_GUIDE.md` for subproject concepts. This guide covers STEP_3.

**Location**: `gigantic_project-COPYME/subprojects/trees_gene_groups/gene_groups-COPYME/STEP_3-tree_visualization/`

---

## CRITICAL: Surface Discrepancies — No Silent Changes

- NEVER silently do something different than requested
- ALWAYS stop and explain any discrepancy before proceeding

---

## What This Step Does

**Purpose**: Render gene group phylogenetic trees as PDF + SVG.

**Input**: Per-gene-group tree newicks at `output_to_input/<source>/STEP_2-phylogenetic_analysis/gene_group-<name>/`.
**Output**: Per-gene-group PDF + SVG visualizations at `output_to_input/<source>/STEP_3-tree_visualization/gene_group-<name>/`.

## Critical context

STEP_3 is **decoupled** from STEP_2. The scientific artifact is the newick file
(STEP_2 output). STEP_3 is presentation. **A rendering issue never invalidates
STEP_2 science.** Implementation is explicitly **soft-fail**: on rendering
errors, a placeholder is written and the script exits 0.

## Single-Script Orchestrator Pattern

The workflow has **one user-runnable script**: `workflow-COPYME-tree_visualization/RUN-workflow.sh`. The user invokes it from a `workflow-RUN_NN-tree_visualization/` copy.

What it does:

1. **Create/heal conda env once** on the login node from `ai/conda_environment.yml` (env name: `aiG-trees_gene_groups-visualization`). Includes broken-env self-heal (rebuilds if `bin/python` is missing).
2. **Iterate the STEP_0 summary TSV** to enumerate gene groups
3. For each gene group with STEP_2 newicks: create `gene_group-X/workflow-RUN_01-tree_visualization/` as a sibling at this STEP_3 level (skip if no STEP_2 output)
4. Dispatch per `execution_mode`:
   - `local` — sequential renders (default; rendering is fast — seconds to minutes per render)
   - `slurm-standard` — one sbatch per gene group, standard QOS
   - `slurm-burst` — chunk into blocks, one sbatch per block, burst QOS

## Rendering Engine

**toytree + toyplot + reportlab** — pure Python, no Qt.

Why not ete3? ete3 requires PyQt5 which is flaky on conda-forge. toytree
removes the Qt dependency entirely.

Installed via pip inside conda env `aiG-trees_gene_groups-visualization`.

## Tree Files Consumed

The script auto-discovers tree newick files at the source's STEP_2 output:

| Suffix | Tree method |
|--------|-------------|
| `*.fasttree` | FastTree |
| `*.treefile` | IQ-TREE (ML with UFBoot/aLRT) |
| `*.veryfasttree` | VeryFastTree |
| `*.phylobayes.nwk` | PhyloBayes consensus |

If a method was disabled in STEP_2, the file doesn't exist → STEP_3 silently skips it.

## Tip Color Coding by Species

Tip labels are colored by species parsed from the GIGANTIC identifier:
- RGS format: `rgs_FAMILY-SPECIES-GENE-SOURCE-ID` → species from `parts[1]`
- Genome format: `g_GENE-t_TRANSCRIPT-p_PROTEIN-n_...Genus_species` → Genus_species from taxonomy

Auto-hide tip labels for trees > `show_tip_labels_max_tips` (default 500) — tree shape stays visible.

## Conda Environment

`aiG-trees_gene_groups-visualization` — auto-created from
`workflow-COPYME-tree_visualization/ai/conda_environment.yml` on first run.

Includes: python, pyyaml, pip → toytree, toyplot, reportlab.

## Resource Requirements

| Tier | CPUs | Memory | Time |
|------|------|--------|------|
| Small (≤ 50 RGS seqs) | 2 | 8 GB | 2 hr (12 hr burst) |
| Large (> 50 RGS seqs) | 2 | 16 GB | 4 hr (24 hr burst) |

Rendering is lightweight — even very large trees usually render in minutes.

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "STEP_2 output_to_input dir not found" | STEP_2 hasn't run | Run STEP_2 first |
| "toytree import failed" | Broken env | RUN-workflow.sh self-heals; if persistent, `conda env remove -n aiG-trees_gene_groups-visualization -y` and rerun |
| Tip labels unreadable | Tree too large | Lower `show_tip_labels_max_tips` in config |
| Wrong species colors | Unusual identifier format | Check `extract_species_from_label()` in render_trees.py |
| PDF too tall | Large tree | Reduce `canvas_height_per_tip_px` in config |

## Why STEP_3 is Separate

Historical context: an earlier GIGANTIC pipeline embedded visualization inside
STEP_2. Three recurring problems:
1. **ete3/PyQt5 install failures** would fail the whole STEP_2 run
2. **Iteration cost**: tweaking a figure required rebuilding trees (potentially days)
3. **False "complete" status** when rendering silently failed but trees succeeded

Separating into STEP_3 solves all three:
- Rendering env is its own small conda env; failures are isolated
- Figure iteration is seconds, not days
- Rendering is explicitly soft-fail; STEP_2 status is never confused by rendering outcomes
