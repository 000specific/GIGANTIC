# BLOCK_dark_proteomes_X_ocl

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

Origin / Conservation / Loss inference for **dark proteome features** —
proteins or protein subsets that lack annotation by standard reference
databases (Pfam / Gene3D / SUPERFAMILY / SMART / CDD / PROSITE Profiles) —
across species tree structures.

The precise dark-proteome feature definition (orthogroup-level dark sets,
per-species dark proteins, lineage-specific dark families, etc.) is the open
design question for Phase 4.

## Reads FROM (planned)

- `../../dark_proteomes/output_to_input/...` (whatever the dark_proteomes
  subproject ultimately produces)
- `../../trees_species/output_to_input/BLOCK_permutations_and_features/` —
  species tree structures (the substrate)

## Provides TO (planned)

- Parent `output_to_input/` per the OCL-BLOCK output pattern

## Related ongoing work

- `../z_dark_sono/` — current dark-proteome / sono dossier work for the
  Salk/Shrek collaboration; informs the eventual feature definition.

## For AI Assistants

Empty placeholder. Read
`../../../research_notebook/research_ai/HANDOFF-ocl_reorganization-2026may28.md`
for OCL reorg context. Feature definition awaits Phase 4 discussion with Eric.
The upstream `../dark_proteomes/` subproject is the source of the feature
signal.
