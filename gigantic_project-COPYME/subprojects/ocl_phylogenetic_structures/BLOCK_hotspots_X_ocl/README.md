# BLOCK_hotspots_X_ocl

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 29
Human:   Eric Edsinger
============================================================================ -->

## Status

**Phase 1 placeholder.** Created during the OCL reorganization (Phase 1,
Commit 4/6, 2026-05-29). Feature definition and concrete design will be
fleshed out **with the user** in Phase 4 of the reorg per their direction
("we will go through the blocks one by one — let's leave these for last
to flesh this out").

## Purpose (one-liner, provisional)

Origin / Conservation / Loss inference for **hotspots** — clade-restricted
gene clusters / lineage-specific gene-family expansions / regions of elevated
evolutionary signal — across species tree structures.

The precise hotspot definition is the open design question for Phase 4.

## Reads FROM (planned)

- `../../hotspots/output_to_input/...` (whatever the hotspots subproject
  ultimately produces)
- `../../trees_species/output_to_input/BLOCK_permutations_and_features/` —
  species tree structures (the substrate)

## Provides TO (planned)

- Parent `output_to_input/` per the OCL-BLOCK output pattern

## For AI Assistants

Empty placeholder. Read
`../../../research_notebook/research_ai/HANDOFF-ocl_reorganization-2026may28.md`
for OCL reorg context. Feature definition awaits Phase 4 discussion with Eric.
The upstream `../hotspots/` subproject is the source of the feature signal.
