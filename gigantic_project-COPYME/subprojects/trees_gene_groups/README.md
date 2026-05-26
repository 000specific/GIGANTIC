# trees_gene_groups — Gene Group Phylogenetic Analysis

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent: [`../../README.md`](../../README.md) — gigantic_project-COPYME overview
- Subproject AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)
- Reads from:
  - `../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_{proteomes,blast_databases}/` — proteomes + BLAST databases
  - `../phylonames/` — species naming
  - External source data (HGNC, Pfam, etc.) — downloaded by per-source STEP_0
- Outputs to (`output_to_input/<gene_group>/`):
  - `STEP_1-homolog_discovery/` — AGS FASTAs per gene group
  - `STEP_2-phylogenetic_analysis/` — newick trees + alignments
  - `STEP_3-tree_visualization/` — PDFs + SVGs
- Downstream consumers:
  - `orthogroups_X_trees/` (when present) — cross-reference gene-group trees with orthogroup assignments
  - `upload_to_server/` (subproject root) — curated subset for the GIGANTIC server
- Sibling subproject: `../trees_gene_families/` — gene families via hand-curated RGS (same three-STEP pattern from STEP_1 onward; gene_groups adds source-specific STEP_0)

---

Build phylogenetic trees for gene groups across GIGANTIC project species. Gene
groups are defined by external classification systems (e.g., HUGO HGNC, Pfam,
custom lists), in contrast to `trees_gene_families` where reference sequences
are hand-curated per family.

## Subproject layout — two template variants + frozen instances

| Path | Type | Purpose |
|------|------|---------|
| `gene_groups-COPYME/` | **Template (generic)** | Master pattern for non-HGNC sources. Has empty `STEP_0-placeholder/` for user to fill in source-specific RGS prep. Per §47 + memory `feedback_instance_naming_follows_template_prefix`, instances of THIS template are named `gene_groups-<source>/`. |
| `gene_groups_hgnc-COPYME/` | **Template (HGNC-specialized)** | Master pattern for HGNC-derived sources, with concrete `STEP_0-hgnc_based_rgs/` containing two workflows: `workflow-COPYME-hgnc_database/` (full HGNC download) and `workflow-COPYME-hgnc_user_list/` (curated subset). Per §47 + the same naming memory, instances of THIS template are named `gene_groups_hgnc-<source>/`. |
| `gene_groups-hugo_hgnc/` | **FROZEN instance** | Older HGNC instance (~1,974 protein-coding groups) — predates `gene_groups_hgnc-COPYME`, uses its own pre-rework STEP_0 structure. Frozen per memory `feedback_research_instances_are_frozen_artifacts`. |
| `gene_groups-snap_family/` | **FROZEN instance** | SNAP family experiment using newer STEP_0-hgnc_based_rgs layout. Frozen per the same rule. |
| `output_to_input/` | Subproject output | Auto-populated by workflows |
| `upload_to_server/` | Server publishing | Auto-populated |
| `RUN-update_upload_to_server.sh` | Publisher | One publisher per subproject at the root, per §38 |

(No per-subproject `research_notebook/` — per §1 consolidation, project-root `../../research_notebook/research_user/` is the sandbox if needed.)

## Three-Step Sequential Pipeline (STEP_0 → STEP_1 → STEP_2 → STEP_3)

Both templates share STEPs 1-3; STEP_0 differs:
- **Generic template** (`gene_groups-COPYME`): `STEP_0-placeholder/` — user fills in source-specific RGS prep
- **HGNC template** (`gene_groups_hgnc-COPYME`): `STEP_0-hgnc_based_rgs/` with `workflow-COPYME-hgnc_database/` + `workflow-COPYME-hgnc_user_list/`

| Step | Name | What |
|------|------|------|
| STEP_0 | RGS Generation (source-specific) | Download source data, generate per-gene-group RGS FASTAs |
| STEP_1 | Homolog Discovery | RBH/RBF BLAST → AGS (All Gene Set) per gene group |
| STEP_2 | Phylogenetic Analysis | MAFFT → ClipKit → trees (FastTree/IQ-TREE/etc.) |
| STEP_3 | Tree Visualization | toytree → PDF + SVG |

Each STEP's `workflow-COPYME-*/RUN-workflow.sh` is the single user-runnable script for that STEP, running in orchestrator mode (processes all gene groups in one invocation). The orchestrator creates the per-workflow conda env once on the login node before any sbatch (no race condition for sub-jobs).

## How a user runs a STEP (per-source instance)

```bash
# 1. Make an instance from one of the templates
cp -r gene_groups_hgnc-COPYME gene_groups_hgnc-<your_source>
# (or: cp -r gene_groups-COPYME gene_groups-<your_source>)

# 2. Inside, for each STEP, copy the COPYME workflow to a RUN_N copy
cd gene_groups_hgnc-<your_source>/STEP_1-homolog_discovery/
cp -r workflow-COPYME-rbh_rbf_homologs workflow-RUN_1-rbh_rbf_homologs

# 3. Edit RUN's config (execution_mode, paths, SLURM resources)
cd workflow-RUN_1-rbh_rbf_homologs
nano START_HERE-user_config.yaml

# 4. Run
bash RUN-workflow.sh
```

`execution_mode` (in YAML) picks the dispatch strategy:
- `local` — sequential local runs
- `slurm-standard` — one sbatch per gene group to the standard QOS
- `slurm-burst` — chunked into blocks, one sbatch per block to the burst QOS

## Conda Environments (per-workflow, auto-created on first run)

Each STEP's workflow has its own conda env in `ai/conda_environment.yml`, named per §28 (`aiG-<subproject>-<step_or_workflow>`):

| STEP | Env name | Key dependencies |
|------|----------|------------------|
| STEP_0 (HGNC) | `aiG-trees_gene_groups-hgnc_*` (see workflow's conda_environment.yml) | python, pyyaml, requests |
| STEP_1 | `aiG-trees_gene_groups-rbh_rbf_homologs` | python, nextflow, blast, numpy, scipy |
| STEP_2 | `aiG-trees_gene_groups-phylogenetic_analysis` | python, nextflow, mafft, clipkit, fasttree, iqtree, veryfasttree |
| STEP_3 | `aiG-trees_gene_groups-visualization` | python, pip → toytree, toyplot, reportlab (no Qt) |

## Prerequisites

- **genomesDB** subproject must be complete (BLAST databases for STEP_1)
- **phylonames** subproject must be complete (species naming used throughout)

## For AI Assistants

See `AI_GUIDE.md`.
