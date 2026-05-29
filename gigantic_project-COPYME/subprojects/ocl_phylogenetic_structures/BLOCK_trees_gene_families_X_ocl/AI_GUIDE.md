# AI Guide — BLOCK_trees_gene_families_X_ocl

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 29 (OCL fix Commit 10)
Human:   Eric Edsinger
Purpose: AI-facing operational guide for the gene-families OCL BLOCK
         placeholder. Created per §51 (missing-doc-create-on-deep-eval)
         + §3 (one AI_GUIDE.md per directory).
Scope:   This BLOCK only. Phase 2 of the OCL reorg fleshes out content.
============================================================================ -->

## Where this fits

- Parent subproject: [`../README.md`](../README.md) + [`../AI_GUIDE.md`](../AI_GUIDE.md)
- BLOCK README (purpose, AGS rationale): [`README.md`](README.md)
- Project AI guide: [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- Sibling functional BLOCK (canonical workflow template to copy): [`../BLOCK_orthogroups_X_ocl/`](../BLOCK_orthogroups_X_ocl/)
- IN (planned): `../../trees_gene_families/.../STEP_1-homolog_discovery/...` AGS FASTAs + `../../trees_species/output_to_input/BLOCK_permutations_and_features/` species tree structures
- OUT (planned): `../output_to_input/BLOCK_trees_gene_families_X_ocl/<run_label>/structure_NNN/...` per §2

## Quick Reference

| User needs... | Go to... |
|---|---|
| Project AI guide | `../../../AI_GUIDE.md` |
| Conventions | `../../../ai/ai_FYIs/gigantic_conventions.md` |
| BLOCK purpose + AGS rationale | [`README.md`](README.md) |
| Parent subproject | [`../README.md`](../README.md), [`../AI_GUIDE.md`](../AI_GUIDE.md) |
| Canonical workflow to copy when promoting this BLOCK | [`../BLOCK_orthogroups_X_ocl/workflow-COPYME-ocl_analysis/`](../BLOCK_orthogroups_X_ocl/workflow-COPYME-ocl_analysis/) |
| OCL reorg handoff (Phase 2 context) | `../../../research_notebook/research_ai/HANDOFF-ocl_reorganization-2026may28.md` |

## Status

**Placeholder.** No workflow yet. Phase 2 of the OCL reorg fleshes this
out. See `README.md` for the planned AGS-based feature signal and why
this BLOCK side-steps the gene-tree-vs-species-tree reconciliation
problem.

## Promotion checklist (Phase 2)

When this BLOCK is being promoted to functional, follow `../AI_GUIDE.md`
"Adding a new BLOCK" section. Specifically:

1. AGS input contract finalized: which `output_to_input/<gene_family>/STEP_1-homolog_discovery/16_ai-ags-*.aa` files feed in, and how `INPUT_user/<input_manifest>.tsv` enumerates them.
2. Workflow template copied from `../BLOCK_orthogroups_X_ocl/workflow-COPYME-ocl_analysis/` and adapted: scripts 001-007 swapped for AGS membership input handling instead of orthogroup tables.
3. Conda env named `aiG-ocl_phylogenetic_structures-trees_gene_families_X_ocl` per §28.
4. BLOCK roster row in `../README.md` flipped from `placeholder` to `functional`.
5. Producer-side downstream-consumer note added to `../../trees_gene_families/AI_GUIDE.md` per §40.
