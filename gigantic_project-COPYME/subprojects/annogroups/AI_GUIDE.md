<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 18
Human:   Eric Edsinger
Purpose: AI guide for the annogroups subproject — the annogroup concept, the
         four canonical types, locked design decisions, and where to go next.
Scope:   The annogroups subproject (LEVEL 2 of the AI_GUIDE hierarchy).
============================================================================ -->

# AI_GUIDE — annogroups (subproject)

**For AI assistants**: Read [`../../AI_GUIDE.md`](../../AI_GUIDE.md) first for the
GIGANTIC overview, directory structure, and general patterns. This guide covers
annogroups-specific concepts. For running the build, read the workflow guide
([`BLOCK_build_annogroups/workflow-COPYME-build_annogroups/ai/AI_GUIDE.md`](BLOCK_build_annogroups/workflow-COPYME-build_annogroups/ai/AI_GUIDE.md)).

| User needs… | Go to… |
|-------------|--------|
| GIGANTIC overview, directory structure, conventions | [`../../AI_GUIDE.md`](../../AI_GUIDE.md) |
| Annogroup concept, types, design decisions | This file |
| Adding a source / the parser contract | [`BLOCK_build_annogroups/AI_GUIDE.md`](BLOCK_build_annogroups/AI_GUIDE.md) |
| Running the build | `BLOCK_build_annogroups/workflow-COPYME-build_annogroups/ai/AI_GUIDE.md` |

## What an annogroup is

An **annogroup** is a set of sequences grouped by a shared annotation feature,
computed **per source database**. A **feature** = `(source, annotation_identifier)`
from `annotations_hmms` — the general unit, not just a domain (it covers motifs,
sites, family assignments, topology segments, etc.).

An annogroup is **always in reference to a source database**. The source is part
of the identity and the identifier (`annogroup_pfam_…`, `annogroup_tmbed_…`), so
the same scheme extends across every annotation source without collision.

## The four canonical types (canonical terms — use exactly)

| Type | Definition | Identifier | Map? |
|------|-----------|------------|------|
| `annogroup_feature` | sequences sharing one feature (multi-membership: a sequence is in one feature annogroup per distinct feature it has) | `annogroup_<source>_<accession>` | no (natural ID) |
| `annogroup_combination` | sequences sharing the same **distinct set** of features (unordered; key = alphabetically-sorted distinct accessions; copies ignored) | `annogroup_<source>_combination<NNNNN>` | yes |
| `annogroup_architecture` | sequences sharing the same **ordered arrangement** of positional features (N→C by `(start, stop)`) | `annogroup_<source>_architecture<NNNNN>` | yes |
| `annogroup_absent` | sequences in the proteome universe with **no** feature from the source | `annogroup_<source>_absent` | no (one per source) |

### Whole-protein vs sub-protein (combination vs architecture)

- `combination` is a **whole-protein** annotation grouping: the *set* of features a
  protein carries, independent of position.
- `architecture` is a **sub-protein** annotation grouping: the N→C *ordered
  arrangement* of features along the sequence. It requires per-feature residue
  coordinates.

A source whose annotations carry **no sub-protein coordinates cannot form an
architecture**, so it yields only feature + combination + absent (3 types). This is
the `is_positional=False` case in the parser contract. **GO** (function/process/
location labels) and **DeepLoc** (subcellular localization) are such whole-protein
sources. Positional sources (pfam, panther) yield all four. How many types a source
yields (3 or 4) is therefore **data-determined, not a knob**.

## Locked design decisions (do NOT re-litigate — user-approved 2026-06-18)

1. **Architecture grouping key is coord-FREE** (the ordered accession pattern),
   so homologs with shifted coordinates group together. Each sequence's
   **coordinate-tagged** architecture (`PF00001_start10_stop50,…`) is stored on
   its **membership row**, not in the shared key.
2. **Combination = distinct set, alphabetical** canonical key.
3. **`absent` needs the full proteome universe** (genomesDB STEP_4). Each
   sequence is independently evaluated by the source, so "no annotation" is a
   per-sequence fact — but to enumerate *complete* `absent` membership the source
   must have been run over every proteome in the species set.
4. **One parser plugin per source** (`parsers/<source>.py`); the four-type
   construction is shared. New source = new parser, nothing else.
5. **How many types a source yields (3 or 4) is data-determined**, not a knob.
6. **Counter IDs are deterministic** (sort canonical keys, then number) — same
   input always yields the same IDs.
7. **All inter-subproject I/O via `output_to_input/`** (§2) — no other path.

## Where annogroups sit in the dependency chain

```
annotations_hmms (per-source features) ─┐
                                         ├─► annogroups ─► OCL, integrator
genomesDB STEP_4 (proteome universe) ────┘
```

`annogroups` replaces the old ad-hoc `single`/`combo`/`zero` scheme that used to
live inside `annotations_X_ocl` Script 001. Downstream restructuring to *consume*
annogroups (rather than recompute groupings) is a planned later phase — see the
BLOCK guide.

## Status

Built 2026-06-18. **pfam validated end-to-end** (137,762 annogroups across the
four types; validation PASS; full NextFlow DAG run).

2026-06-28: two more parsers added and validated (scripts 001–003, PASS):
- **panther** — positional PTHR families (4 types): feature 11,033 / combination
  11,033 / architecture 11,051 / absent 418,016.
- **go** — whole-protein Gene Ontology terms from the **raw** InterProScan results
  (3 types, no architecture by design): feature 8,994 / combination 27,974 / absent
  539,984. GO origin selection (InterPro / PANTHER union, default both) is a
  documented config knob (`go_term_origins`).

One known, user-accepted data caveat: a handful of truncated multi-locus annotation
IDs are dropped — see
`BLOCK_build_annogroups/workflow-COPYME-build_annogroups/ai/ai_FYIs/WARNING-truncated_orphan_annotations.md`.
Downstream restructuring to *consume* annogroups is a later phase.
