# z_ocl_taxonomic_hierarchies

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 29
Human:   Eric Edsinger
============================================================================ -->

## Status

**Phase 1 stub, z_ early-development per §49.** This subproject was created
during the OCL reorganization (Phase 1, 2026 May 29) as the sibling of
`../ocl_phylogenetic_structures/` for OCL analyses that map features onto
**taxonomic hierarchies** (e.g., the NCBI taxonomy encoded in `phylonames/`)
rather than species tree structures.

`z_` prefix indicates this subproject is gitignored except for `README.md`
(per §49). Promotion out of `z_` happens when its first concrete BLOCK
(`BLOCK_simple_taxonomy_X_ocl/`, designed in Phase 3) is functional.

Pluralized because users may have other taxonomies beyond NCBI (per user
direction during reorg design).

## Why a separate parent

Per Rule 5 (project `AI_GUIDE.md`):

- **Trees** (species trees) have a **root**. Edges represent inferred
  biological relationships. Structures are inferred and replaceable.
- **Hierarchies** (NCBI taxonomy) have an **origin**. Edges represent
  set inclusion (definitional, not inferred). Origin is intrinsic.

These are different KINDS of objects. The OCL methodology is the same — count
origins / persistences / losses across edges — but the target object type
differs at the PARENT level, not the BLOCK level. Each parent has the same
BLOCK roster; the substrate differs.

For session context and rationale see
`../../research_notebook/research_ai/HANDOFF-ocl_reorganization-2026may28.md`.

## BLOCK roster (planned — not yet materialized on disk)

| BLOCK | Status | Notes |
|-------|--------|-------|
| `BLOCK_simple_taxonomy_X_ocl/` | planned | Phase 3 — design doc already drafted (see `DESIGN-ocl_using_simple_taxonomy.md` in this directory) |
| `BLOCK_orthogroups_X_ocl/` | planned | mirror of phylogenetic sibling |
| `BLOCK_annotations_X_ocl/` | planned | mirror of phylogenetic sibling |
| `BLOCK_trees_gene_families_X_ocl/` | planned | mirror of phylogenetic sibling |
| `BLOCK_trees_gene_groups_X_ocl/` | planned | mirror of phylogenetic sibling |
| `BLOCK_synteny_X_ocl/` | planned | mirror of phylogenetic sibling |
| `BLOCK_hotspots_X_ocl/` | planned | mirror of phylogenetic sibling |
| `BLOCK_dark_proteomes_X_ocl/` | planned | mirror of phylogenetic sibling |

**Why no on-disk BLOCK placeholder directories?** Per §49, the gitignore
rules that protect `z_*` subprojects allow only the subproject-root
`README.md` to be tracked — any `BLOCK_*/README.md` inside this subproject
would be untrackable. Concrete BLOCK directories will appear here only as
each BLOCK is promoted out of placeholder state and given real workflow
code. Until then, this README and the migrated `DESIGN-*.md` carry the
intent. Phase 3 promotes `BLOCK_simple_taxonomy_X_ocl/` first.

## Reads FROM (planned)

- `../phylonames/` — taxonomic hierarchy (NCBI or user-supplied)
- Feature subprojects upstream of each BLOCK

## For AI Assistants

Phase 1 stub. Full guidance comes in Phases 3 and 5.

While this subproject is `z_`-prefixed (per §49), only `README.md` is tracked
— no separate `AI_GUIDE.md` until promotion. Until then, AI guidance lives
inline in this README.

### Quick Reference (Phase 1)

| User needs... | Go to... |
|---------------|----------|
| Project overview | `../../README.md` and `../../AI_GUIDE.md` |
| OCL reorg context | `../../research_notebook/research_ai/HANDOFF-ocl_reorganization-2026may28.md` |
| Rule 5 (tree vs hierarchy) | `../../AI_GUIDE.md` (Terminology Discipline section) |
| Design for first concrete BLOCK | `DESIGN-ocl_using_simple_taxonomy.md` (in this dir; gitignored per §49 but present on disk) |

### Key terminology reminder

- This parent operates on **hierarchies** (origin), NOT trees (root). Never write "rooted hierarchy."
- Where the phylogenetic-axis sibling reads `trees_species/output_to_input/` for structures, this parent reads `phylonames/` for the taxonomic hierarchy.
