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
| HGNC source specifics | `gene_groups-hugo_hgnc/AI_GUIDE-hugo_hgnc.md` |
| STEP_1 concepts | `gene_groups_COPYME/STEP_1-homolog_discovery/AI_GUIDE-homolog_discovery.md` |
| STEP_2 concepts | `gene_groups_COPYME/STEP_2-phylogenetic_analysis/AI_GUIDE-phylogenetic_analysis.md` |
| STEP_3 concepts | `gene_groups_COPYME/STEP_3-tree_visualization/AI_GUIDE-phylogenetic_visualization.md` |
| Workflow execution details | each `workflow-COPYME-*/ai/AI_GUIDE-*.md` |
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

## The Two-Workflow Pattern at the Subproject Level

trees_gene_groups has exactly **two workflows** at the subproject level:

```
trees_gene_groups/
├── gene_groups_COPYME/         ← workflow 1: master template (never run from here)
└── gene_groups-<source>/       ← workflow 2: per-source instance (one per source)
```

The master `gene_groups_COPYME/` contains STEP_0-placeholder + STEP_1/STEP_2/STEP_3 with their canonical `workflow-COPYME-*/` templates. To add a new source: `cp -r gene_groups_COPYME gene_groups-<source>/`, replace `STEP_0-placeholder/` with the source's STEP_0 code.

Per-source instances currently:
- `gene_groups-hugo_hgnc/` — HUGO HGNC gene groups (~1,974)

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
| STEP_0 (HGNC) | (HGNC's STEP_0 yml) | python, pyyaml, requests |
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

## Adding a New Gene Group Source

```bash
# 1. Copy the master template
cp -r gene_groups_COPYME gene_groups-pfam

# 2. Replace STEP_0-placeholder with source-specific RGS generation
rm -r gene_groups-pfam/STEP_0-placeholder
mkdir -p gene_groups-pfam/STEP_0-pfam_clans/workflow-COPYME-pfam_clans/
# ... populate with the source's downloader + RGS generator ...

# 3. Create AI_GUIDE-pfam.md describing source specifics

# 4. Run STEP_0 → STEP_1 → STEP_2 → STEP_3 as for hugo_hgnc
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
| `gene_groups_COPYME/` | Master template | No (copy it to make new sources) |
| `gene_groups-<source>/AI_GUIDE-<source>.md` | Source-specific AI guidance | Read only |
| `gene_groups-<source>/STEP_0-*/workflow-RUN_NN/START_HERE-user_config.yaml` | STEP_0 config | **YES** (in the RUN_NN copy) |
| `gene_groups-<source>/STEP_1-*/workflow-RUN_NN/START_HERE-user_config.yaml` | STEP_1 config | **YES** |
| `gene_groups-<source>/STEP_2-*/workflow-RUN_NN/START_HERE-user_config.yaml` | STEP_2 config | **YES** |
| `gene_groups-<source>/STEP_3-*/workflow-RUN_NN/START_HERE-user_config.yaml` | STEP_3 config | **YES** |

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
