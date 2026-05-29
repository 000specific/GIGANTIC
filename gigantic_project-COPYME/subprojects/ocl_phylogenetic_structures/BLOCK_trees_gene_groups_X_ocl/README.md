# BLOCK_trees_gene_groups_X_ocl

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 29
Human:   Eric Edsinger
============================================================================ -->

## Status

**Phase 1 placeholder.** Created during the OCL reorganization (Phase 1,
Commit 4/6, 2026-05-29). Content will be drafted in Phase 2 once AGS-based
OCL design is locked in with the user.

## Purpose (one-liner)

Origin / Conservation / Loss inference for gene groups (e.g., HUGO HGNC,
Pfam-derived sets, SNAP families, user-defined custom lists) across species
tree structures, using **AGS** (All Gene Set) as the feature signal.

## Why AGS, not gene trees?

See sibling `../BLOCK_trees_gene_families_X_ocl/README.md` for the full
rationale. Same routing: AGS lives at script 016 of each gene group's
`../../trees_gene_groups/.../STEP_1-homolog_discovery/` workflow and gives
per-species presence/absence of homologs without entangling OCL with gene-
tree-vs-species-tree reconciliation.

## Difference vs BLOCK_trees_gene_families_X_ocl

- `../../trees_gene_families/` operates on hand-curated RGS per family
  (one workflow per family) — sibling BLOCK consumes its AGSs.
- `../../trees_gene_groups/` operates on a SOURCE that produces many gene
  groups via STEP_0 (HGNC database download, Pfam-derived families, user
  list, etc.). The orchestrator dispatches per-group workflows, each
  producing its own AGS. This BLOCK consumes those AGSs, keyed by
  (source, gene_group).

## Reads FROM (planned)

- `../../trees_gene_groups/output_to_input/<source>/STEP_1-homolog_discovery/gene_group-<name>/`
  — per-gene-group AGS FASTAs
- `../../trees_species/output_to_input/BLOCK_permutations_and_features/` —
  species tree structures (the substrate)

## Provides TO (planned)

- Parent `output_to_input/` per the OCL-BLOCK output pattern

## For AI Assistants

Empty placeholder. Read
`../../../research_notebook/research_ai/HANDOFF-ocl_reorganization-2026may28.md`
for OCL reorg context, then `../README.md` and `../AI_GUIDE.md` for parent
scope. The gene_groups template/instance pattern (two-template setup with
gene_groups-COPYME generic and gene_groups_hgnc-COPYME HGNC-specialized) is
documented at `../../trees_gene_groups/README.md`.
