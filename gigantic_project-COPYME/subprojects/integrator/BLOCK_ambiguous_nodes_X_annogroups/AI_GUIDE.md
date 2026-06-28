<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 27
Human:   Eric Edsinger
Purpose: BLOCK-level (LEVEL 2-ish) AI guide for BLOCK_ambiguous_nodes_X_annogroups.
Scope:   This BLOCK — concepts, the ambiguous_nodes pattern, key files.
============================================================================ -->

# AI_GUIDE — BLOCK_ambiguous_nodes_X_annogroups

**For AI Assistants**: Read the integrator subproject guide
(`../AI_GUIDE.md`) first for the BLOCK-type model and conventions, and the
project guide (`../../../AI_GUIDE.md`) for GIGANTIC terminology (Rules 1–7). This
guide covers this BLOCK's concepts; the workflow guide
(`workflow-COPYME-ambiguous_nodes_X_annogroups/ai/AI_GUIDE.md`) covers running it.

| User needs... | Go to... |
|---|---|
| GIGANTIC terminology (structure vs topology, ambiguous zone, Rule 6) | `../../../AI_GUIDE.md` + `../../trees_species/README.md` |
| integrator subproject concepts | `../AI_GUIDE.md` |
| this BLOCK's concepts (this file) | here |
| running the workflow | `workflow-COPYME-*/ai/AI_GUIDE.md` |

## Core concept

An **ambiguous node** is a clade that exists in some but not all species-tree
structures. For species70 the input species tree is unresolved at five basal
metazoan clades (Ctenophora, Porifera, Placozoa, Cnidaria, Bilateria), yielding
105 structures; the ambiguous nodes are the internal groupings of those five
below Metazoa (e.g. `C096_Planulozoa` = Cnidaria+Bilateria, present in 15/105;
the synthetic `C087_Metazoa_Subclade_1`, `C091_Parahoxozoa`, `Clade_NNN`). The
fixed backbone clades (every species, every named clade outside the unresolved
zone, Metazoa itself, and the five phyla as groups) are present in all 105.

## What this BLOCK does

The annogroups subproject's **deconvolution** (`004_ai-python-species_tree_deconvolution.py`)
writes, per annogroup, one member-protein count column per clade across all
structures, in:

```
annogroups/output_to_input/BLOCK_build_annogroups/<species_set>/<source>/
  4_ai-<source>-annogroup_tree_counts-all_structures.tsv            (union of all clades)
  annogroup_tree_counts_per_structure/4_ai-<source>-annogroup_tree_counts-structure_NNN.tsv
```

Each clade column header ends `... present in N of M structures`. This BLOCK
**projects** that table to keep only the clade columns with `N < M` (the
ambiguous nodes), in three scopes:

- **all** — every ambiguous node (the union table, ambiguous columns only)
- **one** — ambiguous nodes of one chosen structure (its per-structure file)
- **some** — ambiguous nodes across a chosen subset (union over those structures)

It is a pure projection: no count is recomputed, because a `clade_id_name`'s
species set — and therefore an annogroup's count at it — is identical in every
structure it appears in (Rule 6). The per-structure files are read (header only)
to learn which ambiguous nodes a given structure carries.

## Why the `_X_` name (and what's excluded)

The `_X_` marks an integrator cross: `ambiguous_nodes` × `annogroups`. The
series generalizes — `ambiguous_nodes_X_<other upstream>` would collapse a
different upstream's per-structure output to the same ambiguous-node axis. The
annogroups `composite_clades` lens (exact basal-phylum signatures) is a separate
product and is **not** consumed here; ambiguous nodes and composite clades are
distinct sets that may overlap partially or not at all.

## Key files (what the user edits)

| File | User edits? | Purpose |
|------|-------------|---------|
| `workflow-*/START_HERE-user_config.yaml` | yes | source dial (`annotation_sources`), structure scopes (`one`, `some`, `all`), SLURM acct/qos |
| `workflow-*/INPUT_user/some_structures_manifest.tsv` | optional | the SOME structure subset |
| `workflow-*/ai/scripts/*.py` | rarely | projection logic |

## Questions to ask the user

| Situation | Ask |
|-----------|-----|
| First run | "Which sources — all (pfam, go, panther) or a subset? Which `one` structure? Which `some` subset?" |
| `some` scope | "Give the subset as inline structure ids, a file (e.g. a `BLOCK_user_requests` selection), or both?" |
| Output grain | "Member-protein counts per ambiguous node (current), or also a presence/absence view?" |
