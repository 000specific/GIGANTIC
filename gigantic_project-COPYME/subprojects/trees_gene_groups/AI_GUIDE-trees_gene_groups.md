# AI Guide: trees_gene_groups Subproject

**For AI Assistants**: Read `../../AI_GUIDE-project.md` first for the GIGANTIC project overview. This guide covers the trees_gene_groups subproject.

**Location**: `gigantic_project-COPYME/subprojects/trees_gene_groups/`

---

## CRITICAL: Surface Discrepancies — No Silent Changes

- NEVER silently do something different than requested
- NEVER assume you know better and proceed without asking
- ALWAYS stop and explain any discrepancy before proceeding

---

## Quick Reference

| User needs… | Go to… |
|-------------|--------|
| GIGANTIC project overview | `../../AI_GUIDE-project.md` |
| trees_gene_groups concepts (this file) | this file |
| Generic (source-agnostic) template | `gene_groups-COPYME/README.md` |
| HGNC-anchored template (newer, two STEP_0 modes) | `gene_groups_hgnc-COPYME/AI_GUIDE-gene_groups_hgnc.md` |
| HGNC source specifics (legacy instance) | `gene_groups-hugo_hgnc/AI_GUIDE-hugo_hgnc.md` |
| Canonical HGNC reference data | `output_to_input/hugo_hgnc_database/README.md` |
| STEP_1 concepts (RBH/RBF) | `gene_groups-COPYME/STEP_1-homolog_discovery/AI_GUIDE-homolog_discovery.md` |
| STEP_2 concepts | `gene_groups-COPYME/STEP_2-phylogenetic_analysis/AI_GUIDE-phylogenetic_analysis.md` |
| STEP_3 concepts | `gene_groups-COPYME/STEP_3-tree_visualization/AI_GUIDE-phylogenetic_visualization.md` |
| HGNC STEP_0 (batch all HGNC groups) | `gene_groups_hgnc-COPYME/STEP_0-hgnc_based_rgs/workflow-hgnc_database/ai/AI_GUIDE-hgnc_database_workflow.md` |
| HGNC STEP_0 (ad-hoc user gene set) | `gene_groups_hgnc-COPYME/STEP_0-hgnc_based_rgs/workflow-hgnc_user_list/ai/AI_GUIDE-hgnc_user_list_workflow.md` |
| Workflow execution details (STEP_1/2/3) | each `workflow-*/ai/AI_GUIDE-*.md` |
| Shared RBH/RBF methodology with sister subproject | `../trees_gene_families/AI_GUIDE-trees_gene_families.md` |

---

## What This Subproject Does

Build phylogenetic trees for gene groups across GIGANTIC species. Gene groups are sets of related genes defined by external classification systems (HGNC, Pfam, custom). The homolog discovery and tree-building pipelines are the same shape as `trees_gene_families`; the difference is RGS source:

| | trees_gene_families | trees_gene_groups |
|--|---------------------|-------------------|
| RGS source | Hand-curated per gene family | Generated from external classifications |
| Scale | Few families at a time | Hundreds–thousands of groups |
| STEP_0 | N/A | Source-specific RGS generation |
| Organization | One dir per family | Source-based; per-source instance contains all gene groups |

---

## Templates and Instances

trees_gene_groups has **two sibling COPYME templates** and a growing
collection of instances (one per analysis):

```
trees_gene_groups/
├── INPUT_user/                                            (none at present;
│                                                           subproject-level user inputs go here if needed)
├── output_to_input/
│   ├── hugo_hgnc_database/                                ← canonical shared HGNC reference (NEW)
│   │   └── hgnc_complete_set.txt                          (symlink → most recent STEP_0 OUTPUT_pipeline)
│   └── <instance>/STEP_N-*/...                            ← per-instance outputs
│
├── gene_groups-COPYME/                                    ← TEMPLATE 1: source-agnostic
│   ├── STEP_0-placeholder/                                (empty stub; replace per source)
│   └── STEP_1, STEP_2, STEP_3                             (shared)
│
├── gene_groups_hgnc-COPYME/                               ← TEMPLATE 2: HGNC-anchored (NEW)
│   ├── INPUT_user/user_gene_set_EXAMPLE.tsv               (for the user_list mode)
│   ├── STEP_0-hgnc_based_rgs/                             (HGNC-specific)
│   │   ├── workflow-hgnc_database/                        ← MODE 1: all HGNC groups
│   │   └── workflow-hgnc_user_list/                       ← MODE 2: ad-hoc user set
│   └── STEP_1, STEP_2, STEP_3                             (inherited from gene_groups-COPYME)
│
└── gene_groups-<instance>/                                ← INSTANCE: copy of one of the templates
                                                            + its own STEP_0 + per-instance state
```

The two templates **coexist forever**. Each one accumulates its own
instances:

- `gene_groups-COPYME` is for non-HGNC sources (Pfam, InterPro, custom
  classifications) — replace its `STEP_0-placeholder/` with a
  source-specific STEP_0.
- `gene_groups_hgnc-COPYME` is for HGNC-anchored analyses (batch or
  ad-hoc) — already has STEP_0 wired with two workflow modes.

### Why a research codebase keeps both

Old instances are **research notebooks + data archives** of the code
path that ran them. They are not migrated to new sibling templates,
even retroactively, because that would erase the historical record
(which scripts ran, which fixes were applied mid-flight, which
manifests were used).

Per-instance examples currently:
- `gene_groups-hugo_hgnc/` — HUGO HGNC gene groups (~1,974); instance of
  `gene_groups-COPYME` with a source-specific STEP_0 (`STEP_0-hgnc_gene_groups/`).
  Older code path; **kept as a research artifact**.
- `gene_groups-snap_family/` — Synaptosomal-Associated Proteins
  (SNAP23/25/29/47); instance of `gene_groups_hgnc-COPYME` using the
  `workflow-hgnc_user_list` mode.

---

## Three-Step Sequential Pipeline (per source)

STEPs are sequentially dependent: **STEP_0 → STEP_1 → STEP_2 → STEP_3**.

| Step | Name | What | Runs |
|------|------|------|------|
| STEP_0 | RGS Generation | Source-specific (download data, generate RGS FASTAs) | Once per source |
| STEP_1 | Homolog Discovery | RBH/RBF BLAST → AGS per gene group | Per source (across all groups) |
| STEP_2 | Phylogenetic Analysis | MAFFT/ClipKit/tree builders → newicks per gene group | Per source |
| STEP_3 | Tree Visualization | toytree → PDF + SVG per gene group | Per source |

Each STEP has a single user-runnable script: `workflow-COPYME-*/RUN-workflow.sh`. The user copies COPYME → `workflow-RUN_NN-*` at the same level, edits the YAML, and runs from the RUN_NN copy.

### Each STEP's RUN-workflow.sh is an orchestrator

The orchestrator handles all gene groups in one invocation:

1. Creates the per-workflow conda env once on the login node
2. Iterates the STEP_0 summary TSV (`gene_group_source_tsv` in YAML)
3. For each gene group: creates `gene_group-X/workflow-RUN_01-<stepname>/` as a sibling at the STEP_N level (copy of the per-STEP COPYME, customized)
4. Dispatches per `execution_mode`:
   - `local` — sequential nextflow/python runs
   - `slurm-standard` — 1 sbatch per gene group, standard QOS
   - `slurm-burst` — chunked into blocks (block size per tier), 1 sbatch per block, burst QOS

STEP_2 and STEP_3 orchestrators skip gene groups whose prior-STEP output isn't yet present (graceful handling of partial completion).

---

## Conda Environments (per-workflow, auto-created)

Each STEP has its own conda env defined in `workflow-COPYME-*/ai/conda_environment.yml`. Auto-created by `RUN-workflow.sh` on the login node, before any sbatch:

| STEP | Env name | Key dependencies |
|------|----------|------------------|
| STEP_0 (legacy hugo_hgnc instance) | `aiG-trees_gene_groups-hgnc_gene_groups` | python, pyyaml, nextflow (urllib stdlib for downloads) |
| STEP_0 (gene_groups_hgnc-COPYME, both workflows) | `aiG-trees_gene_groups-hgnc_based_rgs` | python, pyyaml, nextflow (urllib stdlib only — no `requests`) |
| STEP_1 | `aiG-trees_gene_groups-rbh_rbf_homologs` | python, pyyaml, nextflow, blast, numpy, scipy |
| STEP_2 | `aiG-trees_gene_groups-phylogenetic_analysis` | python, pyyaml, nextflow, mafft, clipkit, fasttree, iqtree, veryfasttree |
| STEP_3 | `aiG-trees_gene_groups-visualization` | python, pyyaml, pip → toytree, toyplot, reportlab |

---

## Gene Set Terminology

| Term | Abbreviation | Meaning |
|------|-------------|---------|
| Reference Gene Set | rgs | Curated sequences from a source (STEP_0 output) |
| Blast Gene Set | bgs | Hits from forward BLAST against project species |
| Candidate Gene Set | cgs | BGS sequences confirmed by reciprocal BLAST |
| All Gene Set | ags | Final combined set (rgs + filtered cgs); STEP_1 output |

Filenames use lowercase: `rgs-`, `bgs-`, `cgs-`, `ags-`.

---

## Inter-Subproject Dependencies

### Inputs FROM

| Subproject | What | Path |
|------------|------|------|
| genomesDB | BLAST databases (per-species .aa) | `../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_blastp/` |
| phylonames | Species name mappings | `../phylonames/output_to_input/maps/` |

### Outputs TO

| Location | What | Consumers |
|----------|------|-----------|
| `output_to_input/<source>/STEP_0-*/rgs_fastas/` | RGS files | Internal (STEP_1) |
| `output_to_input/<source>/STEP_1-*/gene_group-*/` | AGS files | Internal (STEP_2) |
| `output_to_input/<source>/STEP_2-*/gene_group-*/` | Tree newicks | Internal (STEP_3); publication |
| `output_to_input/<source>/STEP_3-*/gene_group-*/` | PDF/SVG renders | Publication; server upload |

---

## Adding a New Analysis

Pick the right template first:

### Case A: HGNC-anchored (human gene symbols → UniProt)

Use `gene_groups_hgnc-COPYME`. The STEP_0 already supports two modes
(batch HGNC + ad-hoc user list); no STEP_0 customization is needed in
the common case.

```bash
# 1. Instantiate
cp -r gene_groups_hgnc-COPYME gene_groups-<my_analysis>

# 2a. Ad-hoc mode: edit INPUT_user/user_gene_set.tsv with your symbols
#     Then: cd <instance>/STEP_0-hgnc_based_rgs/workflow-hgnc_user_list && bash RUN-workflow.sh

# 2b. Batch mode: edit STEP_0-hgnc_based_rgs/workflow-hgnc_database/START_HERE-user_config.yaml
#     to point at your human proteome.
#     Then: cd <instance>/STEP_0-hgnc_based_rgs/workflow-hgnc_database && bash RUN-workflow.sh

# 3. Run STEP_1 → STEP_2 → STEP_3 from the same instance
```

### Case B: Non-HGNC source (Pfam, InterPro, custom)

Use `gene_groups-COPYME` (source-agnostic). You must write the STEP_0
yourself.

```bash
# 1. Copy the source-agnostic template
cp -r gene_groups-COPYME gene_groups-pfam

# 2. Replace STEP_0-placeholder with source-specific RGS generation
rm -r gene_groups-pfam/STEP_0-placeholder
mkdir -p gene_groups-pfam/STEP_0-pfam_clans/workflow-pfam_clans/
# ... populate with the source's downloader + RGS generator ...
#     STEP_0 must emit a per-group summary TSV (5-column) that STEP_1's
#     orchestrator reads (see gene_groups_hgnc-COPYME's STEP_0 for the format).

# 3. Create AI_GUIDE-pfam.md describing source specifics

# 4. Run STEP_0 → STEP_1 → STEP_2 → STEP_3
```

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "BLAST database not found" | genomesDB not run | Run the genomesDB subproject first |
| "STEP_0 summary TSV not found" | STEP_0 hasn't been run for this source | Run STEP_0 first |
| "Many gene groups skipped (no STEP_1 AGS)" in STEP_2 | STEP_1 still in progress | Wait for STEP_1 to finish, then rerun STEP_2 |
| "CRITICAL ERROR: RGS identification failed" in STEP_1 | Script 008 fail-fast on orphans | Inspect diagnostics; fix RGS input or species set |
| Conda env race condition between SLURM jobs | Env wasn't created on login node | Always invoke `bash RUN-workflow.sh` from a login node; the orchestrator creates env BEFORE any sbatch |

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `gene_groups-COPYME/` | Source-agnostic master template | No (copy it to make non-HGNC instances) |
| `gene_groups_hgnc-COPYME/` | HGNC-anchored template (two STEP_0 modes) | No (copy it to make HGNC-anchored instances) |
| `output_to_input/hugo_hgnc_database/hgnc_complete_set.txt` | Canonical HGNC reference (auto-fetched by STEP_0 000) | No (managed by STEP_0) |
| `gene_groups_hgnc-COPYME/INPUT_user/user_gene_set_EXAMPLE.tsv` | Template example for the user_list workflow | No (replace in the instance) |
| `gene_groups-<instance>/INPUT_user/user_gene_set.tsv` | User-supplied gene set for the user_list workflow | **YES** |
| `gene_groups-<instance>/AI_GUIDE-<instance>.md` (optional) | Instance-specific AI guidance | Read only |
| `gene_groups-<instance>/STEP_0-*/workflow-*/START_HERE-user_config.yaml` | STEP_0 config | **YES** |
| `gene_groups-<instance>/STEP_1-*/workflow-*/START_HERE-user_config.yaml` | STEP_1 config | **YES** |
| `gene_groups-<instance>/STEP_2-*/workflow-*/START_HERE-user_config.yaml` | STEP_2 config | **YES** |
| `gene_groups-<instance>/STEP_3-*/workflow-*/START_HERE-user_config.yaml` | STEP_3 config | **YES** |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| Starting from scratch | "Have you run the genomesDB subproject? We need BLAST databases." |
| Which source | "HGNC, or another classification system?" |
| Before STEP_0 | "Do you need to regenerate RGS files, or use existing ones from a previous STEP_0 run?" |
| Before STEP_1 | "Local, slurm-standard, or slurm-burst? Which QOS / resources?" |
| Before STEP_2 | "Which tree methods? FastTree (fast), IQ-TREE (publication), VeryFastTree (large), PhyloBayes (Bayesian)?" |
| Before STEP_3 | "Has STEP_2 completed? Which tree methods produced output?" |
