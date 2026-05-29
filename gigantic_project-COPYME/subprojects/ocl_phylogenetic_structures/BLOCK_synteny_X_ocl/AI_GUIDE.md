# AI Guide — BLOCK_synteny_X_ocl

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 29 (OCL fix Commit 10)
Human:   Eric Edsinger
Purpose: AI-facing operational guide for the synteny OCL BLOCK placeholder.
         Created per §51 + §3.
Scope:   This BLOCK only. Awaits concrete upstream design from ../z_synteny/.
============================================================================ -->

## Where this fits

- Parent subproject: [`../README.md`](../README.md) + [`../AI_GUIDE.md`](../AI_GUIDE.md)
- BLOCK README: [`README.md`](README.md)
- Project AI guide: [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- Sibling functional BLOCK (canonical workflow): [`../BLOCK_orthogroups_X_ocl/`](../BLOCK_orthogroups_X_ocl/)
- Upstream (planned, still placeholder): [`../../z_synteny/`](../../z_synteny/)
- IN (planned): `../../z_synteny/output_to_input/...` synteny block / micro-synteny signal + `../../trees_species/output_to_input/BLOCK_permutations_and_features/`
- OUT (planned): `../output_to_input/BLOCK_synteny_X_ocl/<run_label>/structure_NNN/...` per §2

## Quick Reference

| User needs... | Go to... |
|---|---|
| Project AI guide | `../../../AI_GUIDE.md` |
| BLOCK purpose | [`README.md`](README.md) |
| Parent subproject | [`../README.md`](../README.md), [`../AI_GUIDE.md`](../AI_GUIDE.md) |
| Upstream synteny subproject (placeholder) | [`../../z_synteny/`](../../z_synteny/) |
| Canonical workflow template | [`../BLOCK_orthogroups_X_ocl/workflow-COPYME-ocl_analysis/`](../BLOCK_orthogroups_X_ocl/workflow-COPYME-ocl_analysis/) |
| OCL reorg handoff | `../../../research_notebook/research_ai/HANDOFF-ocl_reorganization-2026may28.md` |

## Status

**Placeholder.** Both this BLOCK and the upstream `../../z_synteny/` are
placeholders. Promotion happens after `z_synteny/` defines a concrete
synteny feature signal. The user flagged synteny as "placeholder but an
important one" during the reorg design.

## Promotion checklist

When upstream synteny is ready:

1. Synteny feature signal contract finalized in `../../z_synteny/`.
2. Workflow template copied from `../BLOCK_orthogroups_X_ocl/workflow-COPYME-ocl_analysis/`.
3. Conda env `aiG-ocl_phylogenetic_structures-synteny_X_ocl` per §28.
4. BLOCK roster row in `../README.md` updated.
5. Producer-side note added to upstream synteny subproject AI_GUIDE per §40.
