# BLOCK_synteny_X_ocl

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 29
Human:   Eric Edsinger
============================================================================ -->

## Status

**Phase 1 placeholder.** Created during the OCL reorganization (Phase 1,
Commit 4/6, 2026-05-29). No content yet. Promotion out of placeholder
state happens when the upstream `../z_synteny/` subproject defines a
concrete synteny feature signal — which Eric flagged as "placeholder but
an important one" during the reorg design.

## Purpose (one-liner)

Origin / Conservation / Loss inference for **synteny blocks** (conserved
gene-order regions) across species tree structures.

## Reads FROM (planned)

- `../../z_synteny/output_to_input/...` (whatever the synteny subproject
  ultimately produces) — synteny block / micro-synteny feature signal
- `../../trees_species/output_to_input/BLOCK_permutations_and_features/` —
  species tree structures (the substrate)

## Provides TO (planned)

- Parent `output_to_input/` per the OCL-BLOCK output pattern

## For AI Assistants

Empty placeholder. Read
`../../../research_notebook/research_ai/HANDOFF-ocl_reorganization-2026may28.md`
for OCL reorg context. The upstream `../z_synteny/` is itself a placeholder
— concrete design awaits user direction.
