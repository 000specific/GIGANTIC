<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 18
Human:   Eric Edsinger
Purpose: Design spec for a new first-class `annogroups` subproject — sequences
         grouped by shared annotation features, per source database, across the
         four canonical annogroup types. Captures the agreed model; gated behind
         user sign-off before any build.
Scope:   The proposed annogroups subproject + the downstream restructuring it
         implies (annotations_X_ocl, integrator). Planning doc in the AI sandbox.
Status:  DRAFT — for sign-off.
============================================================================ -->

# Design spec — `annogroups` subproject

## 1. Purpose

A new `subprojects/annogroups/` subproject produces **annogroups** as a
first-class, reusable GIGANTIC product. Downstream subprojects
(`annotations_X_ocl`, `integrator`, future consumers) consume the **same**
annogroup IDs from it — one source of truth. This replaces the current
`single`/`combo`/`zero` scheme (pfam-only, created inside OCL Script 001).

## 2. Canonical definitions

These four are **canonical GIGANTIC terms** — like `phylogenetic_block` or
`phylogenetic_path`. An **annogroup** is a set of sequences sharing an annotation
feature pattern, **always in reference to one source** annotation database. Every
annogroup ID is prefixed `annogroup_<source>_…`. A **feature** is one
`( source, annotation_identifier )` from the annotations_hmms annotation database.

### `annogroup_feature`
- **Definition**: sequences that share a single specific feature from the source,
  regardless of what else they carry. A sequence with N features belongs to N
  feature-annogroups (multi-membership).
- **Identifier**: `annogroup_<source>_<annotation_identifier>`
  e.g. `annogroup_pfam_PF00001`, `annogroup_tmbed_TM`.

### `annogroup_combination`
- **Definition**: sequences that share the same **unordered, distinct set** of
  source features (copies ignored).
- **Identifier**: `annogroup_<source>_combination<NNNNN>` (zero-padded counter).
  Map: ID → the feature set, listed **alphabetically**.
  e.g. `annogroup_superfamilies_combination00010 → SSF00010,SSF00055`.

### `annogroup_architecture`
- **Definition**: sequences that share the same **ordered arrangement** of
  positional source features (N→C by start coordinate, copies kept).
- **Identifier**: `annogroup_<source>_architecture<NNNNN>` (zero-padded counter).
  Map: ID → the ordered feature list **with coordinates**.
  e.g. `annogroup_pfam_architecture00001 →
  PF00001_start10_stop50,PF00001_start100_stop150,PF00011_start200_stop250`.

### `annogroup_absent`
- **Definition**: sequences (across the species-set proteomes) that have **no**
  feature from the source.
- **Identifier**: `annogroup_<source>_absent`  e.g. `annogroup_pfam_absent`.

Counters (`combination`/`architecture`) are scoped per (source, type), zero-padded,
and assigned **deterministically** (sort canonical keys, then number) so the same
input always yields the same IDs. `feature` and `absent` need no map; their IDs
are self-describing.

## 3. Worked example

A protein with `PF00001@10-50, PF00001@100-150, PF00011@200-250`:

| Type | This protein belongs to |
|---|---|
| feature | `annogroup_pfam_PF00001` **and** `annogroup_pfam_PF00011` |
| combination | the group keyed by `{PF00001, PF00011}` (alphabetical, deduped) |
| architecture | the group keyed by `PF00001_start10_stop50,PF00001_start100_stop150,PF00011_start200_stop250` (N→C order) |
| absent | not absent for pfam (it has pfam features) |

## 4. How many types a source yields is **data-determined** (not a user option)

A source produces 3 or 4 of the canonical types depending on the kind of data its
tool emits — never a user knob:

- **Positional, multi-feature** sources (pfam, gene3d, smart, cdd, superfamily,
  tmbed segments, metapredict regions, …) → all **4** types.
- **Whole-protein / presence** sources (deeploc localization) → **3** (feature,
  combination, absent); architecture is undefined for position-less features
  and is simply not produced.

Each source's parser also decides its **feature granularity**, e.g.:
- `tmbed`: `has-TM` at the feature level, with combination/architecture built from
  the per-segment data in the annotation DB.
- `metapredict`: `has-IDR` at the feature level, with combination/architecture
  built from the per-region data in the annotation DB.

## 5. Membership universe & `absent`

Per-sequence absence is trivial (did the source annotate this sequence?). The
**proteome matters only for completeness of enumeration**: to list every member
of any annogroup (incl. `absent`), the source must have run over the **entire**
species-set proteome set.

- **Universe** = all sequences in the species-set proteomes.
- `annogroup_<S>_absent` = universe − (sequences with ≥1 S-feature).

The proteome sequence lists are read from upstream **`output_to_input/`** —
`genomesDB/output_to_input/STEP_4-create_final_species_set/` — per GIGANTIC
convention that all inter-subproject data flows through `output_to_input/`
(§2; no other path is allowed).

## 6. Modularity — one parser per source

- A **common framework/driver** reads the YAML, inspects the annotation DB for
  available sources, dispatches to per-source parsers, then builds the canonical
  types + maps + membership uniformly and writes outputs.
- **One Python parser per source database**. Each parser owns its source's feature
  semantics and returns a normalized per-sequence feature list
  `sequence_id → [ ( accession, start, stop, is_positional ), … ]`; the framework
  does everything else identically. **New source = new parser**, nothing else
  changes.

## 7. Configuration (`START_HERE-user_config.yaml`)

- `species_set` (e.g. species70) — drives the proteome universe.
- `sources:` — `all` (every source present in the annotation DB) **or** an explicit
  subset; the subproject inspects the DB and validates the request.
- (No annogroup-type knob — type count is data-determined per §4.)

## 8. Inputs / outputs (all via `output_to_input/`, §2)

**Inputs**
- `annotations_hmms/output_to_input/BLOCK_build_annotation_database/` —
  standardized feature rows per source (`Sequence_Identifier, Database_Name,
  Annotation_Identifier, Domain_Start, Domain_Stop`).
- `genomesDB/output_to_input/STEP_4-create_final_species_set/` — proteome
  sequence lists (the universe).

**Outputs** (`annogroups/output_to_input/`), per source —
- annogroup **membership** (sequence → annogroup, all produced types),
- annogroup **map** (combination/architecture ID → feature set/list + type + counts),
- a **manifest** of sources + types produced.

Available sources in the live DB (2026-06): cdd, deeploc, funfam, gene3d, go,
interproscan, metapredict, ncbifam, panther, pfam, prints, sfld, smart,
superfamily, tmbed (+ signalp where present).

## 9. Downstream restructuring (breaking — accepted, "worth the effort")

- **`annotations_X_ocl`**: Script 001 stops *creating* annogroups and instead
  *loads* them from `annogroups/output_to_input/`; OCL runs per annogroup as today.
  ⚠️ Four types × many sources ≫ today's pfam single+combo (~74k); OCL scale and
  the `path_states` matrices grow a lot — **estimate volume before a full re-run**.
- **`integrator/BLOCK_annotations_X_orthogroups`**: consumes annogroup membership
  from `annogroups/` instead of from `annotations_X_ocl`; its single+combo logic
  generalizes to the canonical types.

## 10. GIGANTIC conventions

New `subprojects/annogroups/` as a BLOCK-type subproject (§41:
`BLOCK_build_annogroups`, framework driver + per-source parser scripts under
`ai/scripts/`). NextFlow workflow (per-source fan-out), unified `RUN-workflow.sh`
(§29), `START_HERE-user_config.yaml`, fail-fast (§36), `write_run_log` (§45),
`output_to_input/` (§2) + `upload_to_server/` (§38), full doc set (§3, §42, §48,
§56), per-BLOCK conda env (§28), self-documenting TSV headers (§34).

## 11. Build phases (after sign-off)

1. Scaffold `subprojects/annogroups/` + framework driver + the **pfam** parser;
   validate the four canonical types end-to-end on one source.
2. Add remaining per-source parsers (positional + whole-protein cases).
3. Wire `output_to_input/`; estimate full-source volume.
4. Restructure `annotations_X_ocl` Script 001 to consume annogroups.
5. Restructure the integrator to consume annogroups.
6. Re-run + re-publish the chain; update docs across all three subprojects.
