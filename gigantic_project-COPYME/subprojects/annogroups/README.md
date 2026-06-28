<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 18
Human:   Eric Edsinger
Purpose: User-facing landing page for the annogroups subproject — what an
         annogroup is, the four canonical types, and how the BLOCKs are organized.
Scope:   The annogroups subproject and its BLOCKs.
============================================================================ -->

# annogroups

**Annogroups are sequences grouped by shared annotation features, per annotation
source.** A *feature* is any annotated trait of a sequence with an evolutionary
origin — a domain, a motif, a site, a topology segment, a family assignment —
identified by `(source, annotation_identifier)`. `annogroups` turns each
annotation source's per-sequence features into a reusable grouping product that
downstream subprojects (OCL, the integrator) consume.

## The four canonical annogroup types

Computed **per source database** (pfam, gene3d, tmbed, signalp, deeploc, …).
`annogroup_feature`, `annogroup_combination`, `annogroup_architecture`, and
`annogroup_absent` are **canonical GIGANTIC terms** (like `phylogenetic_block`):

| Type | Definition | Identifier |
|------|-----------|------------|
| `annogroup_feature` | sequences sharing one feature (multi-membership) | `annogroup_<source>_<accession>` (e.g. `annogroup_pfam_PF00001`) |
| `annogroup_combination` | sequences sharing the same **distinct set** of features (unordered, alphabetical key) | `annogroup_<source>_combination<NNNNN>` + map |
| `annogroup_architecture` | sequences sharing the same **ordered** arrangement of positional features (N→C by start, stop) | `annogroup_<source>_architecture<NNNNN>` + map |
| `annogroup_absent` | sequences (in the proteome universe) with **no** feature from the source | `annogroup_<source>_absent` |

**Whole-protein vs sub-protein.** `combination` is a **whole-protein** grouping —
the set of features a protein carries, independent of where they sit. `architecture`
is a **sub-protein** grouping — the N→C ordered arrangement of features along the
sequence, which requires residue coordinates. So how many types a source yields
(3 or 4) is **data-determined**: a source whose annotations have **no sub-protein
coordinates** cannot form an architecture and yields only feature + combination +
absent (3 types). Examples of such whole-protein sources are **GO** (Gene Ontology
function/process/location labels) and **DeepLoc** (subcellular localization).
Positional sources (pfam, panther, …) yield all four.

## Where this fits

`annogroups` is an **upstream feature product**. It consumes per-source
annotations from `annotations_hmms` and the species-set proteomes from
`genomesDB`, and exposes grouped membership for downstream subprojects.

- Parent project landing page: [`../../README.md`](../../README.md)
- Parent project AI guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md)
- This subproject's AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)
- BLOCKs: [`BLOCK_build_annogroups/`](BLOCK_build_annogroups/)

## BLOCKs

| BLOCK | Builds | Status |
|-------|--------|--------|
| [`BLOCK_build_annogroups`](BLOCK_build_annogroups/) | the four canonical annogroup types per annotation source (one parser plugin per source) | Built 2026-06-18 — pfam validated end-to-end (137,762 annogroups, validation PASS). 2026-06-28: **panther** (positional, 4 types) and **go** (whole-protein, 3 types) parsers added and validated (PASS). |

Parser plugins available: **pfam**, **panther** (both positional → 4 types) and
**go** (whole-protein → 3 types). Adding a source is one file (`parsers/<source>.py`);
`sources: "all"` auto-includes every parser.

## Conventions

This subproject follows the standard GIGANTIC interface conventions:
`output_to_input/` for downstream sharing (§2), `upload_to_server/` for the
project data server (§38/§39), the unified `RUN-workflow.sh` driver (§29),
per-BLOCK conda envs (§28/§53), and fail-fast pipelines (§36). See the BLOCK and
workflow guides for specifics.

## Collaborators

Developed for the Moroz lab (UF). Outputs are intended for browsing by Eric
Edsinger and Leonid Moroz via the project data server and direct file access on
HiPerGator.
