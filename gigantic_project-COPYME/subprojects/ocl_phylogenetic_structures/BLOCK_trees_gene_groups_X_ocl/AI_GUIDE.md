# AI Guide — BLOCK_trees_gene_groups_X_ocl

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 29 (OCL fix Commit 10)
Human:   Eric Edsinger
Purpose: AI-facing operational guide for the gene-groups OCL BLOCK
         placeholder. Created per §51 + §3.
Scope:   This BLOCK only. Phase 2 of the OCL reorg fleshes out content.
============================================================================ -->

## Where this fits

- Parent subproject: [`../README.md`](../README.md) + [`../AI_GUIDE.md`](../AI_GUIDE.md)
- BLOCK README (purpose, AGS rationale, source × gene_group key): [`README.md`](README.md)
- Project AI guide: [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- Sibling functional BLOCK (canonical workflow): [`../BLOCK_orthogroups_X_ocl/`](../BLOCK_orthogroups_X_ocl/)
- IN (planned): `../../trees_gene_groups/.../STEP_1-homolog_discovery/...` AGS FASTAs (per source × gene_group) + `../../trees_species/output_to_input/BLOCK_permutations_and_features/`
- OUT (planned): `../output_to_input/BLOCK_trees_gene_groups_X_ocl/<run_label>/structure_NNN/...` per §2

## Quick Reference

| User needs... | Go to... |
|---|---|
| Project AI guide | `../../../AI_GUIDE.md` |
| Conventions | `../../../ai/ai_FYIs/gigantic_conventions.md` |
| BLOCK purpose + AGS rationale + source × gene_group key | [`README.md`](README.md) |
| Parent subproject | [`../README.md`](../README.md), [`../AI_GUIDE.md`](../AI_GUIDE.md) |
| Canonical workflow template (for Phase 2 promotion) | [`../BLOCK_orthogroups_X_ocl/workflow-COPYME-ocl_analysis/`](../BLOCK_orthogroups_X_ocl/workflow-COPYME-ocl_analysis/) |
| Gene groups template pattern (HGNC + non-HGNC) | `../../trees_gene_groups/README.md` |
| OCL reorg handoff | `../../../research_notebook/research_ai/HANDOFF-ocl_reorganization-2026may28.md` |

## Status

**Placeholder.** No workflow yet. Phase 2 of the OCL reorg fleshes this
out. The gene-groups setup differs from gene-families by the upstream
SOURCE dimension (HGNC vs SNAP family vs user-defined): the run_label
will encode source × gene_group (e.g. `species70_hgnc-wnt_ligands`).

## Promotion checklist (Phase 2)

See `../AI_GUIDE.md` "Adding a new BLOCK". Specifically:

1. AGS input contract: per-gene-group AGS files at
   `output_to_input/<source>/STEP_1-homolog_discovery/gene_group-<name>/16_ai-ags-*.aa`,
   keyed by (source, gene_group).
2. Workflow template adapted with two-level run_label (source × gene_group)
   for input manifest.
3. Conda env `aiG-ocl_phylogenetic_structures-trees_gene_groups_X_ocl` per §28.
4. BLOCK roster row in `../README.md` updated.
5. Producer-side note added to `../../trees_gene_groups/AI_GUIDE.md` per §40.
