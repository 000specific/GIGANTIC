# ocl_phylogenetic_structures

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 29
Human:   Eric Edsinger
============================================================================ -->

## Status

**Phase 1 stub.** This subproject was created during the OCL reorganization
(Phase 1, 2026 May 29) as the parent for all `_X_ocl` BLOCKs that map
features onto **phylogenetic species tree structures**. Full README + AI_GUIDE
content (the four-layer framework anchoring OCL methodology, the five-state
vocabulary, and the BLOCK roster) will be written in Phase 5 of the reorg
plan.

For session context and rationale see
`../../research_notebook/research_ai/HANDOFF-ocl_reorganization-2026may28.md`.

## Purpose (one-liner)

Origin / Conservation / Loss (OCL) inferences for a feature × species tree
structure pair. Each BLOCK consumes a different upstream feature type
(orthogroups, annotations, AGS-based gene families/groups, etc.) and reports
where that feature originated, where it persists, and where it was lost across
the resolved species tree structures produced by `../trees_species/`.

The sibling subproject `../z_ocl_taxonomic_hierarchies/` performs the same
analysis but against NCBI taxonomic hierarchies rather than species tree
structures — see Rule 5 (tree-vs-hierarchy distinction) in the project
`AI_GUIDE.md`.

## BLOCK roster (Phase 1)

| BLOCK | Status | Notes |
|-------|--------|-------|
| `BLOCK_orthogroups_X_ocl/` | functional | migrated from `orthogroups_X_ocl/` |
| `BLOCK_annotations_X_ocl/` | functional | migrated from `annotations_X_ocl/` |
| `BLOCK_trees_gene_families_X_ocl/` | placeholder | Phase 2 — uses AGS pre-treebuilding |
| `BLOCK_trees_gene_groups_X_ocl/` | placeholder | Phase 2 — uses AGS pre-treebuilding |
| `BLOCK_synteny_X_ocl/` | placeholder | future feature axis |
| `BLOCK_hotspots_X_ocl/` | placeholder | Phase 4 — design WITH user |
| `BLOCK_dark_proteomes_X_ocl/` | placeholder | Phase 4 — design WITH user |

Each BLOCK is independently runnable per §27.

## Reads FROM

- `../trees_species/output_to_input/` — species tree structures (the substrate)
- Feature subprojects upstream of each BLOCK (orthogroups, annotations, etc.)

## Provides TO

- `output_to_input/` — per-BLOCK OCL summary tables, consumed by downstream
  ranking / interpretation work
- `../z_parsimony_tree_structures/` (set aside, Layer 3) — future consumer
  for occams-tree-style structure ranking

## For AI Assistants

This is a minimal stub. Read `../../research_notebook/research_ai/HANDOFF-ocl_reorganization-2026may28.md`
for full reorg context.
