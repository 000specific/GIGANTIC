# AI Guide — ocl_phylogenetic_structures

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 29
Human:   Eric Edsinger
============================================================================ -->

## Status

**Phase 1 stub.** Full subproject-level AI guidance (four-layer framework,
five-state vocabulary, BLOCK roster + cross-BLOCK coordination) will be
written in Phase 5.

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| Project overview, directory structure, conventions | `../../README.md` and `../../AI_GUIDE.md` |
| OCL reorg history and rationale | `../../research_notebook/research_ai/HANDOFF-ocl_reorganization-2026may28.md` |
| Running a specific BLOCK | `BLOCK_*/AI_GUIDE-*.md` (per-BLOCK guide) |
| Rule 5 (tree vs hierarchy) | `../../AI_GUIDE.md` (Terminology Discipline section) |

## Posture

The parent subproject `ocl_phylogenetic_structures/` enforces ONE shape:
each `BLOCK_<feature>_X_ocl/` independently runs OCL inference against the
species tree structures produced by `../trees_species/`. BLOCKs do not depend
on each other. Cross-BLOCK aggregation (occams-tree-style ranking) is out of
scope for the BLOCKs themselves — that work lives downstream in
`../z_parsimony_tree_structures/` (set aside) and any future STEP_2-occams_tree
at the parent level.

When in doubt about whether something belongs in a BLOCK or at the parent
level, ask: *does this depend on the substrate (species tree structure) or
the feature?* Substrate-shared things belong at the parent (a single shared
view of `trees_species/output_to_input/`); feature-specific things belong in
the BLOCK.
