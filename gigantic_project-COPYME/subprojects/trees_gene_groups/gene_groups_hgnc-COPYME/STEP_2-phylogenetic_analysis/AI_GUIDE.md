# AI Guide: STEP_2 — Phylogenetic Analysis (trees_gene_groups)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent STEP README: [`README.md`](README.md)
- Parent (template): [`../README.md`](../README.md)
- Parent (subproject AI guide): [`../../AI_GUIDE.md`](../../AI_GUIDE.md)
- Reads FROM: `../../../../output_to_input/<gene_group>/STEP_1-homolog_discovery/`
- Outputs TO: `../../../../output_to_input/<gene_group>/STEP_2-phylogenetic_analysis/`
- Conda env: `aiG-trees_gene_groups-phylogenetic_analysis`

---

**For AI Assistants**: Read `../../../AI_GUIDE.md` first for GIGANTIC overview. Then `../../AI_GUIDE.md` for subproject concepts. This guide covers STEP_2.

**Location**: `gigantic_project-COPYME/subprojects/trees_gene_groups/gene_groups-COPYME/STEP_2-phylogenetic_analysis/`

---

## CRITICAL: Surface Discrepancies — No Silent Changes

- NEVER silently do something different than requested
- ALWAYS stop and explain any discrepancy before proceeding

---

## What This Step Does

**Purpose**: Build phylogenetic trees per gene group from STEP_1's AGS (All Gene Set).

**Input**: Per-gene-group AGS FASTA files at `output_to_input/<source>/STEP_1-homolog_discovery/gene_group-<name>/`.
**Output**: Per-gene-group tree newick files at `output_to_input/<source>/STEP_2-phylogenetic_analysis/gene_group-<name>/`.

## Single-Script Orchestrator Pattern

The workflow has **one user-runnable script**: `workflow-COPYME-phylogenetic_analysis/RUN-workflow.sh`. The user invokes it from a `workflow-RUN_NN-phylogenetic_analysis/` copy.

What it does:

1. **Create conda env once** on the login node from `ai/conda_environment.yml` (env name: `aiG-trees_gene_groups-phylogenetic_analysis`)
2. **Iterate the STEP_0 summary TSV** to enumerate gene groups
3. For each gene group with a STEP_1 AGS file: create `gene_group-X/workflow-RUN_01-phylogenetic_analysis/` as a sibling at this STEP_2 level (skip if no AGS yet)
4. Categorize as small (≤ `large_threshold` RGS seqs) or large
5. Dispatch per `execution_mode`:
   - `local` — sequential nextflow runs
   - `slurm-standard` — one sbatch per gene group, standard QOS
   - `slurm-burst` — chunk into blocks, one sbatch per block, burst QOS

## Pipeline Process (per gene group, inside nextflow)

| Process | Tool | What |
|---------|------|------|
| 1 | (bash) | Stage AGS from STEP_1 output_to_input |
| 2 | (bash) | Strip leading/trailing dashes |
| 3 | MAFFT | Multiple sequence alignment |
| 4 | ClipKit | Smart-gap alignment trimming |
| 5_a | FastTree | Fast approximate ML tree (default ON) |
| 5_b | IQ-TREE | Full ML with bootstrap (publication-quality; very slow) |
| 5_c | VeryFastTree | Parallelized FastTree alternative |
| 5_d | PhyloBayes | Bayesian MCMC (very slow) |
| 6 | python | Pipeline run log |

Tree methods are independently toggled in the `tree_methods:` YAML block. At least one must be enabled.

## Resource Tiers

Same RGS-count tiering as STEP_1. STEP_2 tends to need more CPU/memory than STEP_1 for the heavier tree methods (IQ-TREE especially).

## Conda Environment

`aiG-trees_gene_groups-phylogenetic_analysis` — auto-created from
`workflow-COPYME-phylogenetic_analysis/ai/conda_environment.yml` on first run.

Includes: python, pyyaml, nextflow, mafft, clipkit, fasttree, iqtree, veryfasttree.
(PhyloBayes-MPI not included by default; add to yml + rebuild env if needed.)

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "STEP_1 output_to_input dir not found" | STEP_1 hasn't run | Run STEP_1 first |
| Many gene groups skipped (no STEP_1 AGS) | STEP_1 still in progress | Wait for STEP_1 to finish; rerun STEP_2 |
| MAFFT out of memory | Large alignment | Use the `large` resource tier; bump `large_memory_gb` |
| IQ-TREE timeout | Model selection slow | Increase `large_time_hours` or use FastTree only |
| All trees fail with ClipKit error | All columns trimmed | Switch ClipKit mode to less aggressive (e.g., `kpic-smart-gap`) |

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `workflow-COPYME-*/START_HERE-user_config.yaml` | Tree methods, resources, paths | **YES** (in the RUN_NN copy) |
| `workflow-COPYME-*/ai/conda_environment.yml` | Conda env spec | No (auto-applied) |
| `workflow-COPYME-*/ai/main.nf`, `nextflow.config`, `scripts/*` | Pipeline | No |
