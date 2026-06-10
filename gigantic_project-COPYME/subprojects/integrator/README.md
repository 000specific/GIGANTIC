<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 04
Human:   Eric Edsinger
Purpose: User-facing landing page for the integrator subproject — what it is,
         what it integrates, and how its BLOCKs are organized.
Scope:   The integrator subproject and its BLOCKs.
============================================================================ -->

# integrator

**Cross-subproject integration.** `integrator` joins outputs from multiple
GIGANTIC subprojects into combined, analysis-ready tables. It is organized as
independent **BLOCKs** (per `ai/ai_FYIs/gigantic_conventions.md` §41) — each
BLOCK integrates a specific combination of upstream subprojects and can be run
on its own.

## Where this fits

`integrator` is a downstream subproject: it **consumes** other subprojects'
`output_to_input/` and produces integrated tables. It produces no new primary
biology — it combines existing results.

- Parent project landing page: [`../../README.md`](../../README.md)
- Parent project AI guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md)
- This subproject's AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)
- BLOCKs: [`BLOCK_orthogroups_ocl_X_features/`](BLOCK_orthogroups_ocl_X_features/), [`BLOCK_annotations_X_orthogroups/`](BLOCK_annotations_X_orthogroups/)

## BLOCKs

| BLOCK | Integrates | Status |
|-------|-----------|--------|
| [`BLOCK_orthogroups_ocl_X_features`](BLOCK_orthogroups_ocl_X_features/) | OCL orthogroup analysis (per species-tree structure) × dark proteome × hotspots × secretome | Built 2026-06-04 (scaffold + scripts; not yet run end-to-end) |
| [`BLOCK_annotations_X_orthogroups`](BLOCK_annotations_X_orthogroups/) | pfam annogroups × orthogroups, focused on non-bilaterian-only orthogroups (structure-independent) | Built 2026-06-09 (scaffold + scripts; join validated end-to-end against real data) |

Future BLOCKs will integrate other combinations (each its own independent
BLOCK).

## The first BLOCK in one sentence

For each of the 105 phylogenetic species-tree structures, take the
orthogroup-level Origin/Conservation/Loss (OCL) result and, using each
orthogroup's member sequence IDs, attach per-gene **dark proteome**,
**hotspot**, and **secretome** features — so you can ask, e.g., *"orthogroups
that originated at clade X with high loss are enriched in secreted / dark /
hotspot genes."*

## Conventions

This subproject follows the standard GIGANTIC interface conventions:
`output_to_input/` for downstream sharing (§2), `upload_to_server/` for the
project data server (§38), the unified `RUN-workflow.sh` driver (§29), and
fail-fast pipelines (§36). See the BLOCK and workflow guides for specifics.

## Collaborators

Developed for the Moroz lab (UF). Outputs are intended for browsing by Eric
Edsinger and Leonid Moroz via the project data server and direct file access on
HiPerGator.
