# AI Guide — ocl_phylogenetic_structures

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 29 (Phase 1 stub)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 29 (OCL fix Commit 10 — §42 + §48 + §51 flesh-out)
Human:   Eric Edsinger
Purpose: AI-facing operational guide for the ocl_phylogenetic_structures
         subproject — the parent that hosts every _X_ocl BLOCK whose
         substrate is a species tree STRUCTURE. Complements README.md
         (user-facing); covers conventions, BLOCK layout, doc hierarchy,
         and what to read next.
Scope:   ocl_phylogenetic_structures/ subproject. AI sessions working on
         OCL should root at the renamed project (gigantic_project-*/) and
         drill into this subproject from there per §61.
============================================================================ -->

## Where this fits

- Parent project AI guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md) (Rules 1-7)
- This subproject's README: [`README.md`](README.md) (user-facing landing)
- Per-BLOCK AI guides: `BLOCK_<feature>_X_ocl/AI_GUIDE.md`
- Per-workflow AI guides: `BLOCK_<feature>_X_ocl/workflow-COPYME-ocl_analysis/ai/AI_GUIDE.md`
- IN: substrate (species tree structures) at `../trees_species/output_to_input/BLOCK_permutations_and_features/`; features per BLOCK
- OUT: per-BLOCK summaries at `output_to_input/<BLOCK>/<run_label>/structure_NNN/`; server publish via `upload_to_server/` + `RUN-update_upload_to_server.sh`
- Sibling axis (taxonomic hierarchies): [`../z_ocl_taxonomic_hierarchies/`](../z_ocl_taxonomic_hierarchies/)

## Quick Reference

| User needs... | Go to... |
|---|---|
| GIGANTIC overview | [`../../AI_GUIDE.md`](../../AI_GUIDE.md) |
| Conventions (§1-§61) | [`../../ai/ai_FYIs/gigantic_conventions.md`](../../ai/ai_FYIs/gigantic_conventions.md) |
| Rule 7 whitepaper (blocks + block-states + A/O/P/L/X) | [`../../ai/ai_FYIs/ocl_phylogenetic_structures-rule_7_whitepaper.md`](../../ai/ai_FYIs/ocl_phylogenetic_structures-rule_7_whitepaper.md) |
| Subproject purpose, BLOCK roster, dir layout | [`README.md`](README.md) |
| Run an OCL analysis on orthogroups (canonical-tool BLOCK) | [`BLOCK_orthogroups_X_ocl/AI_GUIDE.md`](BLOCK_orthogroups_X_ocl/AI_GUIDE.md) |
| Run an OCL analysis on annotation domains | [`BLOCK_annotations_X_ocl/AI_GUIDE.md`](BLOCK_annotations_X_ocl/AI_GUIDE.md) |
| Sibling subproject (taxonomic hierarchies) | [`../z_ocl_taxonomic_hierarchies/README.md`](../z_ocl_taxonomic_hierarchies/README.md) |
| OCL reorganization context (handoff) | [`../../research_notebook/research_ai/HANDOFF-ocl_reorganization-2026may28.md`](../../research_notebook/research_ai/HANDOFF-ocl_reorganization-2026may28.md) |
| Server publishing | [`../../server/AI_GUIDE.md`](../../server/AI_GUIDE.md) |

## Subproject posture

The parent subproject enforces ONE shape: each
`BLOCK_<feature>_X_ocl/` independently runs OCL inference against the
species tree structures produced by `../trees_species/`. BLOCKs do not
depend on each other; per §41 BLOCKs are parallel / alternative analyses.

When in doubt about whether something belongs in a BLOCK or at the
parent level, ask: *does this depend on the SUBSTRATE (species tree
structure) or the FEATURE?*

- Substrate-shared things → parent level (one shared view of
  `trees_species/output_to_input/`, one publisher, one
  `output_to_input/`, one `upload_to_server/`)
- Feature-specific things → the BLOCK (its own
  `workflow-COPYME-ocl_analysis/`, scripts, conda env, manifest)

## §-rule conformance status (after OCL fix Commits 7-10)

| § | Rule | Status |
|---|---|---|
| §1 | No per-subproject research_notebook/ | ✅ Sandbox content at `../../research_notebook/research_ai/subproject-ocl_phylogenetic_structures/`; nothing inside this subproject |
| §2 | output_to_input/ mirrors producer paths | ✅ Per-BLOCK subdirs (`output_to_input/BLOCK_<feature>_X_ocl/<run_label>/...`) |
| §3 | AI_GUIDE.md naming — no suffixes | ✅ Each directory has exactly one `AI_GUIDE.md` |
| §22 | ai_FYIs subproject-prefix naming | ✅ Rule 7 whitepaper at `../../ai/ai_FYIs/ocl_phylogenetic_structures-rule_7_whitepaper.md` |
| §28 | Per-subproject conda env naming `aiG-<subproject>-<block>` | ✅ Renamed to `aiG-ocl_phylogenetic_structures-{orthogroups,annotations}_X_ocl` |
| §29 | Unified RUN-workflow.sh + execution_mode | ✅ Inherited from migrated BLOCKs |
| §35 | workflow-COPYME-* / workflow-RUN_NN-* | ✅ Inherited |
| §36 | Fail-fast (no optional:true, errorStrategy=terminate, sys.exit(1)) | ✅ Inherited |
| §38 | One upload_to_server/ + one publisher at subproject root | ✅ At this subproject root |
| §42 | "Where this fits" header | ✅ Top of this file + README.md |
| §45 | write_run_log canonical final script | ✅ Inherited (script 006 + script 007 aggregator) |
| §47 | Frozen RUN artifacts | ✅ `workflow-RUN_*/` and `x_workflow-RUN_*/` archives untouched |
| §48 | Quick Reference table at top of AI_GUIDE | ✅ Above |
| §49 | z_* gitignore (sibling parent) | ✅ Sibling `../z_ocl_taxonomic_hierarchies/` follows this |
| §51 | Missing-doc-create-on-deep-eval | ✅ Parent README + this AI_GUIDE built; placeholder BLOCKs have READMEs (Commit 10 adds basic AI_GUIDE.md to each) |
| §56 | Workflow-level README.md mandatory | ⚠️ Workflows inherited the AI_GUIDE.md but workflow-level READMEs not yet added — deferred |

## Adding a new BLOCK

When a placeholder BLOCK is being promoted to functional:

1. The BLOCK's upstream feature subproject must be functional (e.g., to
   add `BLOCK_hotspots_X_ocl/` as functional, `../hotspots/` must be
   producing the feature signal).
2. Copy the canonical workflow template from one of the functional
   BLOCKs (`BLOCK_orthogroups_X_ocl/workflow-COPYME-ocl_analysis/` is a
   reasonable starting point). Rename the workflow per §35 if the
   pipeline diverges enough to deserve its own name.
3. Update the new workflow's `ai/conda_environment.yml` name to follow
   §28: `aiG-ocl_phylogenetic_structures-<feature>_X_ocl`.
4. Add the BLOCK's row to the BLOCK roster in `README.md`.
5. Per §51, give the BLOCK both a `README.md` and an `AI_GUIDE.md`.
6. Per §40, add a downstream-consumer note in the upstream feature
   subproject's AI guide referencing this new BLOCK.

## See also

- `README.md` — user-facing landing for this subproject
- `../../ai/ai_FYIs/gigantic_conventions.md` — §1-§61
- `../../ai/ai_FYIs/ocl_phylogenetic_structures-rule_7_whitepaper.md` —
  Rule 7 vocabulary
- `../../research_notebook/research_ai/HANDOFF-ocl_reorganization-2026may28.md`
  — OCL reorganization design + decisions
- `../../research_notebook/research_ai/subproject-ocl_phylogenetic_structures/`
  — sandbox (planning-occams_tree/, planning-leonid/,
  planning-phylogenetic_blocks_and_locks/) — see §1 for why this is
  outside GIGANTIC's pipeline boundary
