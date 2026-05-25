# trees_gene_groups — Gene Group Phylogenetic Analysis

Build phylogenetic trees for gene groups across GIGANTIC project species. Gene
groups are defined by external classification systems (e.g., HUGO HGNC, Pfam,
custom lists), in contrast to `trees_gene_families` where reference sequences
are hand-curated per family.

## The two-workflow pattern

This subproject has exactly **two workflows** at the subproject level:

| Workflow | Purpose |
|----------|---------|
| `gene_groups_COPYME/` | Master template (never run from here) |
| `gene_groups-<source>/` | Per-source instance (copy of master + source-specific STEP_0) |

To add a new gene-group source (Pfam, InterPro, custom): make another `gene_groups-<source>/` by `cp -r gene_groups_COPYME gene_groups-<source>/`, then replace its `STEP_0-placeholder/` with source-specific STEP_0 code.

## Current sources

| Source | Directory | Status |
|--------|-----------|--------|
| HUGO HGNC | `gene_groups-hugo_hgnc/` | ~1,974 protein-coding gene groups; ready to run |

## Three-Step Sequential Pipeline (per source)

STEPs are sequentially dependent: STEP_0 → STEP_1 → STEP_2 → STEP_3.

| Step | Name | What |
|------|------|------|
| STEP_0 | RGS Generation (source-specific) | Download source data, generate per-gene-group RGS FASTAs |
| STEP_1 | Homolog Discovery | RBH/RBF BLAST → AGS (All Gene Set) per gene group |
| STEP_2 | Phylogenetic Analysis | MAFFT → ClipKit → trees (FastTree/IQ-TREE/etc.) |
| STEP_3 | Tree Visualization | toytree → PDF + SVG |

Each STEP's `workflow-COPYME-*/RUN-workflow.sh` is the **single user-runnable script** for that STEP. It always runs in orchestrator mode — processes all gene groups in one invocation.

## How a user runs a STEP

Inside a per-source instance:

```bash
# 1. Copy the STEP's COPYME → RUN_NN at the same level
cd gene_groups-hugo_hgnc/STEP_1-homolog_discovery/
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_1-rbh_rbf_homologs

# 2. Edit the RUN's config
cd workflow-RUN_1-rbh_rbf_homologs
# edit START_HERE-user_config.yaml — set execution_mode, paths, SLURM resources

# 3. Run
bash RUN-workflow.sh
```

`execution_mode` (in YAML) picks the dispatch strategy:
- `local` — sequential local runs
- `slurm-standard` — one sbatch per gene group to the standard QOS
- `slurm-burst` — chunked into blocks, one sbatch per block to the burst QOS

The orchestrator creates the per-workflow conda env once on the login node before any sbatch (no race condition for sub-jobs).

## Quick Start (HUGO HGNC)

```bash
# 1. STEP_0 — generate ~1,974 RGS FASTAs (one time per source)
cd gene_groups-hugo_hgnc/STEP_0-hgnc_gene_groups/
cp -r workflow-COPYME-hgnc_gene_groups workflow-RUN_1-hgnc_gene_groups
cd workflow-RUN_1-hgnc_gene_groups
# Edit START_HERE-user_config.yaml (set human_proteome_path)
bash RUN-workflow.sh

# 2. STEP_1 — homolog discovery across all gene groups
cd ../../STEP_1-homolog_discovery/
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_1-rbh_rbf_homologs
cd workflow-RUN_1-rbh_rbf_homologs
# Edit START_HERE-user_config.yaml (execution_mode, SLURM resources)
bash RUN-workflow.sh

# 3. STEP_2 — phylogenetic trees per gene group
cd ../../STEP_2-phylogenetic_analysis/
cp -r workflow-COPYME-phylogenetic_analysis workflow-RUN_1-phylogenetic_analysis
cd workflow-RUN_1-phylogenetic_analysis
bash RUN-workflow.sh

# 4. STEP_3 — render trees as PDF + SVG
cd ../../STEP_3-tree_visualization/
cp -r workflow-COPYME-tree_visualization workflow-RUN_1-tree_visualization
cd workflow-RUN_1-tree_visualization
bash RUN-workflow.sh
```

## Conda Environments

Each STEP has its own conda env (auto-created from `ai/conda_environment.yml` on first run, on the login node, before any sbatch):

| STEP | Env name | Key deps |
|------|----------|----------|
| STEP_0 (HGNC) | (source-specific; see HGNC's STEP_0 conda_environment.yml) | python, pyyaml, requests |
| STEP_1 | `aiG-trees_gene_groups-rbh_rbf_homologs` | python, nextflow, blast, numpy, scipy |
| STEP_2 | `aiG-trees_gene_groups-phylogenetic_analysis` | python, nextflow, mafft, clipkit, fasttree, iqtree, veryfasttree |
| STEP_3 | `aiG-trees_gene_groups-visualization` | python, pip → toytree, toyplot, reportlab |

## Subproject layout

```
trees_gene_groups/
├── AI_GUIDE-trees_gene_groups.md
├── README.md                          (this file)
├── RUN-update_upload_to_server.sh
├── gene_groups_COPYME/                (master; see its README.md)
├── gene_groups-hugo_hgnc/             (HGNC source instance)
├── output_to_input/                   (autopopulated by workflows)
├── research_notebook/
└── upload_to_server/                  (autopopulated)
```

## Prerequisites

- **genomesDB** subproject must be complete (BLAST databases for STEP_1)
- **phylonames** subproject must be complete (species naming used throughout)

## For AI Assistants

See `AI_GUIDE-trees_gene_groups.md`.
