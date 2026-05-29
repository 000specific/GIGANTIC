# BLOCK_trees_gene_families_X_ocl

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 29
Human:   Eric Edsinger
============================================================================ -->

## Status

**Phase 1 placeholder.** Created during the OCL reorganization (Phase 1,
Commit 4/6, 2026-05-29). Content will be drafted in Phase 2 once AGS-based
OCL design is locked in with the user.

## Purpose (one-liner)

Origin / Conservation / Loss inference for gene families across species tree
structures, using **AGS** (All Gene Set) as the feature signal.

## Why AGS, not gene trees?

The trees-derived BLOCKs deliberately use AGS — the FASTA produced by
script 016 of each `../../trees_gene_families/.../STEP_1-homolog_discovery/`
workflow, which concatenates the curated Reference Gene Set (RGS) with the
BLAST-discovered Candidate Gene Set (CGS). AGS encodes per-species
presence/absence of homologs for each gene family, which is exactly the
feature signal OCL needs.

Using AGS instead of the gene trees themselves side-steps the gene-tree-vs-
species-tree reconciliation problem (incomplete lineage sorting, duplication
+ loss, horizontal gene transfer, long-branch attraction). Reconciliation is
real and interesting, but it is its own problem — claimed by the placeholder
subproject `../z_species_trees_vs_gene_trees/`, not OCL.

## Reads FROM (planned)

- `../../trees_gene_families/output_to_input/<gene_family>/STEP_1-homolog_discovery/`
  — per-gene-family AGS FASTAs
- `../../trees_species/output_to_input/BLOCK_permutations_and_features/` —
  species tree structures (the substrate)

## Provides TO (planned)

- Parent `output_to_input/` per the OCL-BLOCK output pattern

## For AI Assistants

Empty placeholder. Read
`../../../research_notebook/research_ai/HANDOFF-ocl_reorganization-2026may28.md`
for OCL reorg context, then `../README.md` and `../AI_GUIDE.md` for parent
subproject scope. AGS specification lives in the workflow READMEs under
`../../trees_gene_families/gene_family_COPYME/STEP_1-homolog_discovery/`.
