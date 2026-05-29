# AI Guide — BLOCK_hotspots_X_ocl

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 29 (OCL fix Commit 10)
Human:   Eric Edsinger
Purpose: AI-facing operational guide for the hotspots OCL BLOCK placeholder.
         Created per §51 + §3.
Scope:   This BLOCK only. Feature definition deferred to Phase 4 of the
         OCL reorg per user direction ("design WITH user").
============================================================================ -->

## Where this fits

- Parent subproject: [`../README.md`](../README.md) + [`../AI_GUIDE.md`](../AI_GUIDE.md)
- BLOCK README (provisional purpose): [`README.md`](README.md)
- Project AI guide: [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- Sibling functional BLOCK (canonical workflow): [`../BLOCK_orthogroups_X_ocl/`](../BLOCK_orthogroups_X_ocl/)
- Upstream: [`../../hotspots/`](../../hotspots/)
- IN (planned): `../../hotspots/output_to_input/...` hotspot feature signal + `../../trees_species/output_to_input/BLOCK_permutations_and_features/`
- OUT (planned): `../output_to_input/BLOCK_hotspots_X_ocl/<run_label>/structure_NNN/...` per §2

## Quick Reference

| User needs... | Go to... |
|---|---|
| Project AI guide | `../../../AI_GUIDE.md` |
| BLOCK provisional purpose | [`README.md`](README.md) |
| Parent subproject | [`../README.md`](../README.md), [`../AI_GUIDE.md`](../AI_GUIDE.md) |
| Upstream hotspots subproject | [`../../hotspots/`](../../hotspots/) |
| Canonical workflow template | [`../BLOCK_orthogroups_X_ocl/workflow-COPYME-ocl_analysis/`](../BLOCK_orthogroups_X_ocl/workflow-COPYME-ocl_analysis/) |
| OCL reorg handoff | `../../../research_notebook/research_ai/HANDOFF-ocl_reorganization-2026may28.md` |

## Status

**Placeholder.** Feature definition is the open question and is deferred
to **Phase 4** of the OCL reorganization per user direction ("design
WITH user" — leave for last in the BLOCK roster sweep).

The provisional definition (clade-restricted gene clusters / lineage-
specific gene-family expansions / regions of elevated evolutionary
signal) is documented in `README.md` but is not load-bearing yet.

## Promotion checklist

When the user is ready to flesh this out:

1. Hotspot feature signal definition decided WITH user (this is the
   open design question).
2. Workflow template copied from `../BLOCK_orthogroups_X_ocl/workflow-COPYME-ocl_analysis/`.
3. Conda env `aiG-ocl_phylogenetic_structures-hotspots_X_ocl` per §28.
4. BLOCK roster row in `../README.md` updated.
5. Producer-side note added to `../../hotspots/AI_GUIDE.md` per §40.
