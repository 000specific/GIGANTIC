# z_species_trees_vs_gene_trees

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 29
Human:   Eric Edsinger
============================================================================ -->

## Status

**Phase 1 placeholder, z_ early-development per §49.** Created during OCL
reorg (2026 May 29) as the explicit home for **gene tree vs species tree
concordance** work — separate from OCL inference.

The OCL reorg specifically routed the trees-derived `_X_ocl` BLOCKs
(`BLOCK_trees_gene_families_X_ocl/`, `BLOCK_trees_gene_groups_X_ocl/`) to use
**AGS** (All Gene Set) pre-treebuilding, *not* the gene trees themselves. That
side-steps the gene-tree-vs-species-tree reconciliation problem inside OCL.
The reconciliation problem is real and interesting in its own right — that's
what this placeholder claims for future development.

## Scope (future, no code yet)

Work that would land here:

- Gene tree topology vs species tree topology comparisons
- Systematic discordance from ILS (incomplete lineage sorting),
  duplication+loss, horizontal gene transfer, introgression, long-branch
  attraction
- Reconciliation methods (DTL — duplication / transfer / loss models, etc.)
- Gene tree → species tree feedback for refining
  `../trees_species/` structures

Out of scope:

- OCL inference itself — that belongs in
  `../ocl_phylogenetic_structures/` (against species tree structures) or
  `../z_ocl_taxonomic_hierarchies/` (against taxonomic hierarchies)
- Gene tree building per se — that's `../trees_gene_families/` and
  `../trees_gene_groups/`
- Species tree building per se — that's `../trees_species/`

## For AI Assistants

Phase 1 placeholder. No code or design docs yet. Promotion out of `z_` happens
when concrete scope and a workflow are designed.
