# AI Guide — BLOCK_dark_proteomes_X_ocl

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 29 (OCL fix Commit 10)
Human:   Eric Edsinger
Purpose: AI-facing operational guide for the dark-proteomes OCL BLOCK
         placeholder. Created per §51 + §3.
Scope:   This BLOCK only. Feature definition deferred to Phase 4 per
         user direction.
============================================================================ -->

## Where this fits

- Parent subproject: [`../README.md`](../README.md) + [`../AI_GUIDE.md`](../AI_GUIDE.md)
- BLOCK README (provisional purpose): [`README.md`](README.md)
- Project AI guide: [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- Sibling functional BLOCK (canonical workflow): [`../BLOCK_orthogroups_X_ocl/`](../BLOCK_orthogroups_X_ocl/)
- Upstream: [`../../dark_proteomes/`](../../dark_proteomes/)
- Related ongoing work: [`../../z_dark_sono/`](../../z_dark_sono/) (Salk/Shrek collab; ion-channel candidates lacking human orthologs)
- IN (planned): `../../dark_proteomes/output_to_input/...` dark feature signal + `../../trees_species/output_to_input/BLOCK_permutations_and_features/`
- OUT (planned): `../output_to_input/BLOCK_dark_proteomes_X_ocl/<run_label>/structure_NNN/...` per §2

## Quick Reference

| User needs... | Go to... |
|---|---|
| Project AI guide | `../../../AI_GUIDE.md` |
| BLOCK provisional purpose | [`README.md`](README.md) |
| Parent subproject | [`../README.md`](../README.md), [`../AI_GUIDE.md`](../AI_GUIDE.md) |
| Upstream dark_proteomes subproject | [`../../dark_proteomes/`](../../dark_proteomes/) |
| Related ongoing dark_sono work | [`../../z_dark_sono/`](../../z_dark_sono/) |
| Canonical workflow template | [`../BLOCK_orthogroups_X_ocl/workflow-COPYME-ocl_analysis/`](../BLOCK_orthogroups_X_ocl/workflow-COPYME-ocl_analysis/) |
| OCL reorg handoff | `../../../research_notebook/research_ai/HANDOFF-ocl_reorganization-2026may28.md` |

## Status

**Placeholder.** Feature definition deferred to **Phase 4** of the OCL
reorganization per user direction. The provisional purpose (OCL on
proteins or protein subsets lacking annotation by standard reference
databases — Pfam / Gene3D / SUPERFAMILY / SMART / CDD / PROSITE
Profiles) is documented in `README.md` but is not load-bearing yet.

The active `../../z_dark_sono/` work informs the eventual feature
definition (ion-channel dark candidates lacking human orthologs) but
is its own subproject scope, not this BLOCK's.

## Promotion checklist

When the user is ready to flesh this out:

1. Dark-proteome feature definition decided WITH user (orthogroup-level
   dark sets? per-species dark proteins? lineage-specific dark families?
   — this is the open design question).
2. Workflow template copied from `../BLOCK_orthogroups_X_ocl/workflow-COPYME-ocl_analysis/`.
3. Conda env `aiG-ocl_phylogenetic_structures-dark_proteomes_X_ocl` per §28.
4. BLOCK roster row in `../README.md` updated.
5. Producer-side note added to `../../dark_proteomes/AI_GUIDE.md` per §40.
