<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 09
Human:   Eric Edsinger
Purpose: BLOCK-level AI guide for BLOCK_annotations_X_orthogroups — the join
         design, output tables, and per-script pipeline.
Scope:   BLOCK_annotations_X_orthogroups.
============================================================================ -->

# AI Guide: BLOCK_annotations_X_orthogroups

## Where this fits

- Parent (subproject AI guide): [`../AI_GUIDE.md`](../AI_GUIDE.md) — integrator overview
- Parent (subproject README): [`../README.md`](../README.md)
- Workflow template: [`workflow-COPYME-annotations_X_orthogroups/`](workflow-COPYME-annotations_X_orthogroups/)
- This BLOCK's workflow guide: [`workflow-COPYME-annotations_X_orthogroups/ai/AI_GUIDE.md`](workflow-COPYME-annotations_X_orthogroups/ai/AI_GUIDE.md)
- Reads FROM:
  - `../../annogroups/output_to_input/BLOCK_build_annogroups/<species_set>/<source>/` — `2_ai-<source>-annogroup_map.tsv` (annogroup type, accessions, definitions) + `2_ai-<source>-annogroup_membership.tsv` (member `Sequence_IDs` per annogroup). **Imported DIRECTLY from the annogroups subproject — no OCL dependency.** Types included: feature + combination + architecture + **absent** (the pfam-dark state row; see `annogroup_types` in the config).
  - `../../orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC/orthogroups_gigantic_ids.tsv` — orthogroup membership
  - `../../trees_species/output_to_input/BLOCK_permutations_and_features/Species_Clade_Species_Mappings/9_ai-clade_species_mappings-all_structures.tsv` — Bilateria (`C103`) + Metazoa (`C082`) species sets
- Outputs TO: `../output_to_input/BLOCK_annotations_X_orthogroups/<run_label>/`
- Conda env: `aiG-integrator-annotations_X_orthogroups`

## Quick Reference

| User needs... | Go to... |
|---|---|
| GIGANTIC overview | `../../../AI_GUIDE.md` |
| Conventions | `../../../ai/ai_FYIs/gigantic_conventions.md` |
| integrator concepts + join model | `../AI_GUIDE.md` |
| BLOCK concepts (this file) | This file |
| Running the workflow | `workflow-COPYME-annotations_X_orthogroups/ai/AI_GUIDE.md` |

## What this BLOCK does

Joins pfam **annogroups** to **orthogroups** through shared member proteins, and
filters by the orthogroups' bilaterian / non-bilaterian species composition.

### Definitions

- **Annogroup**: a set of proteins sharing an annotation pattern from one database
  (here pfam). Subtype `single` = exactly one pfam; `combo` = identical multi-pfam
  architecture. `zero` (no pfam) is **excluded** by default. Produced by
  `ocl_phylogenetic_structures/BLOCK_annotations_X_ocl` (`run_label=species70_pfam`).
- **Orthogroup**: a set of orthologous genes across species (from
  `orthogroups/BLOCK_orthohmm_GIGANTIC`).
- **Species 3-way category** (from two `trees_species` clades, Bilateria
  `C103_Bilateria` ⊂ Metazoa `C082_Metazoa`):
  - **bilaterian** — in Bilateria
  - **non-bilaterian metazoan** — in Metazoa but not Bilateria (sponges,
    cnidarians, ctenophores, placozoans)
  - **non-metazoan** — not in Metazoa (unicellular outgroups)
- **Orthogroup composition** (4 classes by member-species categories):
  - `bilaterian_only` — only bilaterians
  - `mixed_with_bilaterian` — bilaterians + any non-bilaterians
  - `non_bilaterian_metazoan` — **zero bilaterians AND ≥1 non-bilaterian
    metazoan** (non-metazoans allowed) → the **QUALIFYING** class
  - `non_metazoan_only` — zero bilaterians, no metazoans (unicell-only) → does
    NOT qualify

### Join model

The annogroup↔orthogroup link is **shared member proteins** (full GIGANTIC IDs).
Each protein belongs to exactly one annogroup (a clean `single`+`combo` partition,
verified against real data) and at most one orthogroup. An annogroup's orthogroups
= the orthogroups its member proteins fall into. An annogroup is **kept** iff at
least one of those orthogroups is `non_bilaterian_metazoan` (qualifying).

### Structure-invariance (efficiency)

Annogroup membership, orthogroup membership, and the Bilateria species set are all
**invariant across the 105 species-tree structures** (Bilateria is a named clade
outside the unresolved zone — Rule 6). So this is a **single-pass, two-table
integration with no per-structure fan-out** — distinct from the sibling
`BLOCK_orthogroups_ocl_X_features`, which IS per-structure.

## Output tables

### Table 1 — annogroups X orthogroups (`3-output/`)
One row per **kept** annogroup. **Keep rule (user-approved)**: keep iff the
annogroup has ≥1 `non_bilaterian_metazoan` (qualifying) orthogroup; drop every
other annogroup (including those whose only non-bilaterian orthogroups are
non-metazoan-unicell-only). Columns: Annogroup_ID, Subtype,
Annotation_Accessions, Annotation_Definitions, Annogroup_Species_Count,
Annogroup_Member_Protein_Count, Members_With/Without_Orthogroup_Count,
Orthogroup_Count, the four per-class counts (NonBilaterian_Metazoan /
NonMetazoan_Only / Bilaterian_Only / Mixed_With_Bilaterian), the four per-class
Orthogroup_IDs lists, and All_Orthogroup_IDs. **All** of a kept annogroup's
orthogroups are reported regardless of their composition.

### Table 2 — non-bilaterian-metazoan orthogroups (`2-output/`)
File `2_ai-nonbilaterian_metazoan_orthogroups.tsv`. One row per orthogroup
classified `non_bilaterian_metazoan` (qualifying): Orthogroup_ID,
Member_Protein_Count, Species_Count, NonBilaterian_Metazoan_Species_Count,
NonMetazoan_Species_Count, Species_List.

### Supporting — orthogroup composition (`1-output/`)
Every orthogroup with its `Composition_Class` (one of the four), bilaterian /
non-bilaterian-metazoan / non-metazoan species counts, and a `Qualifies` flag —
the shared basis for both tables (Table 2 is its `non_bilaterian_metazoan` slice;
Table 1 uses it as the per-orthogroup class lookup).

## Upstream dependency: annogroup membership exposure

Table 1's join needs the per-protein annogroup `Sequence_IDs`, which the OCL
all-types summary does **not** carry. As of 2026-06-09 the
`BLOCK_annotations_X_ocl` workflow exposes the structure-invariant `single` +
`combo` membership files in its `output_to_input/` (its `RUN-workflow.sh` symlink
step was extended; existing `species70_pfam` symlinks were generated against the
canonical RUN_02). If a future annotations-OCL run does not expose membership,
Script 003 fails fast with a clear message. See
`../../ocl_phylogenetic_structures/BLOCK_annotations_X_ocl/AI_GUIDE.md`.

## Pipeline (5 scripts + utils)

| # | Script | Process | Function |
|---|--------|---------|----------|
| 001 | `classify_orthogroups.py` | `classify_orthogroups` | Classify every orthogroup into one of 4 composition classes via the Bilateria (`C103`) + Metazoa (`C082`) species sets; fail-fast if a clade row or inputs are missing |
| 002 | `build_nonbilaterian_orthogroups.py` | `build_nonbilaterian_orthogroups` | Table 2 — `non_bilaterian_metazoan` (qualifying) slice |
| 003 | `build_annogroup_X_orthogroups.py` | `build_annogroup_X_orthogroups` | Table 1 — join annogroup membership onto protein→orthogroup map; apply keep rule |
| 004 | `validate_results.py` | `validate_results` | Cross-check class validity, Table 2 count, Table 1 arithmetic + referential integrity + keep-rule; fail-fast (§36) |
| 005 | `write_run_log.py` | `write_run_log` | Timestamped run log (§45) |
| — | `utils_integrator.py` | — | Shared helpers (config, GIGANTIC-ID parsing, header indexing, `DELIM`) |

## Delimiter

In-column ID lists use **bare commas** (`,`) per §34.

## See also

- [`../AI_GUIDE.md`](../AI_GUIDE.md) — integrator subproject overview
- [`workflow-COPYME-annotations_X_orthogroups/ai/AI_GUIDE.md`](workflow-COPYME-annotations_X_orthogroups/ai/AI_GUIDE.md) — workflow execution + validated first-run reference
