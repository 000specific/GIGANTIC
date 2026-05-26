# AI Guide: STEP_1 — Homolog Discovery (trees_gene_groups)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent STEP README: [`README.md`](README.md)
- Parent (template): [`../README.md`](../README.md) — gene_groups-COPYME (generic)
- Parent (subproject): [`../../README.md`](../../README.md) + [`../../AI_GUIDE.md`](../../AI_GUIDE.md)
- Parent (project): [`../../../../AI_GUIDE.md`](../../../../AI_GUIDE.md)
- Workflow template: [`workflow-COPYME-rbh_rbf_homologs/`](workflow-COPYME-rbh_rbf_homologs/)
- Reads FROM: per-gene-group RGS FASTAs from STEP_0 + `../../../../genomesDB/output_to_input/STEP_4-create_final_species_set/`
- Outputs TO: `../../../../output_to_input/<gene_group>/STEP_1-homolog_discovery/`
- Downstream STEP: `../STEP_2-phylogenetic_analysis/`
- Conda env: `aiG-trees_gene_groups-rbh_rbf_homologs`
- Sister: [`../../../../trees_gene_families/gene_family_COPYME/STEP_1-homolog_discovery/AI_GUIDE.md`](../../../../trees_gene_families/gene_family_COPYME/STEP_1-homolog_discovery/AI_GUIDE.md) — same shape, different RGS source

---

**For AI Assistants**: Read `../../../AI_GUIDE.md` first for GIGANTIC overview. Then `../../AI_GUIDE.md` for subproject concepts. This guide covers STEP_1.

**Location**: `gigantic_project-COPYME/subprojects/trees_gene_groups/gene_groups_COPYME/STEP_1-homolog_discovery/`

---

## CRITICAL: Surface Discrepancies — No Silent Changes

- NEVER silently do something different than requested
- ALWAYS stop and explain any discrepancy before proceeding

---

## What This Step Does

**Purpose**: Find homologs of each gene group's Reference Gene Set (RGS) across all project species using **Reciprocal Best Hit / Reciprocal Best Family (RBH/RBF) BLAST**.

**Input**: Per-gene-group RGS FASTA files from STEP_0 (one `.aa` per gene group).
**Output**: Per-gene-group AGS FASTA files (RGS + filtered CGS), one per gene group, symlinked into the subproject's `output_to_input/<source>/STEP_1-homolog_discovery/gene_group-<name>/`.

## Single-Script Orchestrator Pattern

The workflow has **one user-runnable script**: `workflow-COPYME-rbh_rbf_homologs/RUN-workflow.sh`. The user invokes it from a `workflow-RUN_NN-rbh_rbf_homologs/` copy of the COPYME.

What it does at orchestrator-level:

1. **Create conda env once** on the login node from `ai/conda_environment.yml` (env name: `aiG-trees_gene_groups-rbh_rbf_homologs`). Subsequent calls find the env and skip creation.
2. **Iterate the STEP_0 summary TSV** to enumerate gene groups
3. For each gene group: create `gene_group-X/workflow-RUN_01-rbh_rbf_homologs/` as a sibling at the STEP_1 level (copy of COPYME, with `INPUT_user/` populated and YAML sed-patched)
4. Categorize as small (≤ `large_threshold` RGS seqs) or large
5. Dispatch per `execution_mode` in YAML:
   - `local` — sequential nextflow runs on this machine
   - `slurm-standard` — one sbatch per gene group, standard QOS, per-tier resources
   - `slurm-burst` — chunk into blocks (`burst_block_size` per tier), one sbatch per block, burst QOS, blocks run gene groups sequentially

## Pipeline Process (per gene group, inside nextflow)

| Steps | Phase | What |
|-------|-------|------|
| 001 | Validate RGS | RGS FASTA format check (fail-fast) |
| 002–003 | Forward BLAST | RGS vs project species DBs |
| 004 | Extract BGS | Full-length + hit-region sequences |
| 005–006 | RGS-genome BLAST | RGS vs source-organism proteomes |
| 007–010 | Reciprocal setup | Map RGS→genome IDs (script 008), build modified genome DBs |
| 011–012 | Reciprocal BLAST | CGS vs combined RGS+genome DB |
| 013 | Extract CGS | RBH/RBF filter (with QUERY-side RGS-source protection) |
| 014 | Species filter | Keep only species in the keeper list |
| 016 | Create AGS | RGS + filtered CGS → final All Gene Set |
| 017 | Run log | Timestamped pipeline log |
| 018 | (Optional) Restore full-length RGS | When `rgs_sequence_is_full_length: false` |

**Note**: BLAST v5 databases preserve full GIGANTIC identifiers — no script 015 (identifier remapping).

## RGS Identification (Script 008)

Script 008 maps each RGS protein to its cognate in the source genome. The current implementation per [PLAN-rgs_identification_improvements.md](PLAN-rgs_identification_improvements.md) uses 5 mechanisms in order:

1. **NCBI accession match** — primary (deterministic, zero ambiguity for human/HGNC RGS)
2. **BLAST identity ≥95% AND symmetric coverage ≥95%** with T1 length-invariant check
3. **Bidirectional best hit (BBH)** to catch paralog confusion
4. **Hungarian (optimal) bipartite assignment** via scipy when greedy is ambiguous
5. **Strict fail-fast** — any unresolved RGS halts the pipeline with detailed diagnostics

Output adds a `mechanism` column and a sidecar audit `8_ai-rgs_identification_report.tsv`.

## Two RGS Modes

| Mode (`rgs_sequence_is_full_length`) | When | Behavior |
|------|------|----------|
| `true` (default) | Standard gene groups | `rgs_full_length_file` used for BLAST; script 018 skipped |
| `false` | Domain-only RGS (e.g., TRP pore regions) | `rgs_subsequence_file` used for BLAST; script 018 restores full-length in the AGS |

## Inputs Required (in each per-gene-group RUN_01 INPUT_user/)

| Input | Where it comes from |
|-------|---------------------|
| RGS FASTA | STEP_0 output_to_input |
| `species_keeper_list.tsv` | Generated by orchestrator from genomesDB BLAST DB dir |
| `rgs_species_map.tsv` | Source-specific (in the COPYME's INPUT_user/) |

## Outputs

| Output | Location |
|--------|----------|
| Final AGS | `gene_group-X/workflow-RUN_01-rbh_rbf_homologs/OUTPUT_pipeline/16-output/16_ai-ags-*.aa` |
| AGS symlinks | `../../../output_to_input/<source>/STEP_1-homolog_discovery/gene_group-X/*.aa` (consumed by STEP_2) |
| RGS-identification audit | `OUTPUT_pipeline/8-output/8_ai-rgs_identification_report.tsv` |

## Conda Environment

`aiG-trees_gene_groups-rbh_rbf_homologs` — auto-created from `workflow-COPYME-rbh_rbf_homologs/ai/conda_environment.yml` on first run.

Includes: python, pyyaml, nextflow, blast, numpy, scipy.

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "STEP_0 summary TSV not found" | STEP_0 not yet run for this source | Run STEP_0 first |
| "BLAST database not found" | genomesDB not complete | Run genomesDB subproject |
| "CRITICAL ERROR: RGS identification failed" | Orphan RGS not cleanly resolved by script 008 | Inspect the unresolved-RGS diagnostics; fix the RGS input |
| "No BLAST hits" | E-value too stringent or wrong RGS | Try 1e-2 or verify RGS sequences |
| `mamba env create` fails on race | Multiple jobs trying to create env simultaneously | The orchestrator creates env on the login node BEFORE any sbatch — should not race |

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `workflow-COPYME-*/START_HERE-user_config.yaml` | All per-STEP_1 configuration | **YES** (in the RUN_NN copy) |
| `workflow-COPYME-*/INPUT_user/rgs_species_map.tsv` | RGS short-name → Genus_species mapping | YES (per source) |
| `workflow-COPYME-*/ai/conda_environment.yml` | Conda env spec | No (auto-applied) |
| `workflow-COPYME-*/ai/main.nf`, `nextflow.config`, `scripts/*` | Pipeline implementation | No |
