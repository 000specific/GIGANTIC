# AI Guide: STEP_1 — Homolog Discovery (trees_gene_groups)

**For AI Assistants**: Read `../../../AI_GUIDE-project.md` first for GIGANTIC overview. Then `../../AI_GUIDE-trees_gene_groups.md` for subproject concepts. This guide covers STEP_1.

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
| 007 | List FASTAs | Per-species proteome FASTA paths for the genome indexer |
| 008 | Map RGS→genome IDs | Strict gene-symbol search OR NCBI accession match (no BLAST fallback) |
| 009–010 | Build modified genome DB | Modified genomes with RGS-renamed proteins; combined BLAST DB |
| 011–012 | Reciprocal BLAST | CGS vs combined RGS+genome DB |
| 013 | Extract CGS | RBH/RBF filter (with QUERY-side RGS-source protection) |
| 014 | Species filter | Keep only species in the keeper list |
| 016 | Create AGS | RGS + filtered CGS → final All Gene Set |
| 017 | Run log | Timestamped pipeline log |
| 018 | (Optional) Restore full-length RGS | When `rgs_sequence_is_full_length: false` |

**Notes**:
- BLAST v5 databases preserve full GIGANTIC identifiers — no script 015 (identifier remapping).
- 2026-05-26: Steps 005 + 006 (RGS-vs-source-genome BLAST) were **removed** along with the BLAST fallback chain in script 008. Script 005 was deleted; the `blast_rgs_versus_rgs_genomes` NextFlow process is gone. See the workflow AI_GUIDE for the full rationale.

## RGS Identification (Script 008) — BLAST-free as of 2026-05-26

Script 008 dispatches on RGS header format and uses exactly one deterministic
mechanism per RGS:

| RGS header format | Producer | Mechanism |
|---|---|---|
| 4-field uniprot-sourced (`rgs_<group>-<species>-<symbol>-uniprot<id>`) | `workflow-hgnc_user_list` | **Improvement 0** — strict gene-symbol search against the proteome's `>g_<SYMBOL>-` headers (exactly one match required, else fail-fast) |
| 5-field hgnc/ncbi-sourced (`rgs_<group>-<species>-<symbol>-<source>-<NP_id>`) | `workflow-hgnc_database` | **Improvement 1** — exact NCBI accession match against the proteome's `p_<accession>` |

Both mechanisms are strict and **fail-fast**. There is no BLAST rescue path
for RGS that doesn't cleanly resolve via its header's primary key. This is
intentional: gene_groups_hgnc RGS are always either NCBI-accession-tagged
(database mode) or HGNC-symbol-tagged (user-list mode), and Improvements
0 + 1 cover both cases exactly. The historical Improvements 2–4 (BLAST
fallback + Hungarian assignment) were inherited from trees_gene_families
and were dead code here — they were removed in 2026-05-26.

Output adds a `mechanism` column (`gene_symbol` or `ncbi_accession`) and
a sidecar audit `8_ai-rgs_identification_report.tsv`.

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
