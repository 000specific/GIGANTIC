<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 18
Human:   Eric Edsinger
Purpose: Document what annogroups shares with downstream subprojects.
Scope:   annogroups/output_to_input/.
============================================================================ -->

# annogroups / output_to_input

Downstream subprojects read annogroups from here (the canonical inter-subproject
sharing location, §2). Populated by `BLOCK_build_annogroups`'s `RUN-workflow.sh`
as **symlinks** into the canonical workflow run's `OUTPUT_pipeline/`.

## Layout

```
output_to_input/
└── BLOCK_build_annogroups/
    └── <species_set>/              # e.g. species70
        └── <source>/               # e.g. pfam, gene3d, tmbed, ...
            ├── 2_ai-<source>-annogroup_map.tsv          # one row per annogroup (all 4 types)
            ├── 2_ai-<source>-annogroup_membership.tsv   # one row per (sequence, annogroup)
            ├── 2_ai-<source>-dropped_orphan_sequences.tsv  # audit (orphan/truncated IDs)
            ├── 4_ai-<source>-annogroup_tree_counts-all_structures.tsv   # deconvolution union (all clades)
            ├── annogroup_tree_counts_per_structure/     # deconvolution, one file per structure
            │   └── 4_ai-<source>-annogroup_tree_counts-<structure>.tsv
            └── 5_ai-<source>-annogroup_sequences_per_species.tsv   # annogroup x species -> member sequence IDs
```

## Files

- **`…-annogroup_map.tsv`** — `Annogroup_ID`, `Source`, `Annogroup_Type`
  (feature / combination / architecture / absent), `Defining_Features`,
  `Sequence_Count`, `Species_Count`.
- **`…-annogroup_membership.tsv`** — `Sequence_Identifier` (full GIGANTIC ID),
  `Genus_Species`, `Annogroup_ID`, `Annogroup_Type`,
  `Member_Architecture_Coordinates` (coordinate-tagged ordered features for
  architecture rows; empty otherwise).
- **`…-annogroup_tree_counts-all_structures.tsv`** — species-tree deconvolution
  overlay on the annogroup map: per annogroup, the member-protein count at every
  non-redundant clade (node or tip) across all structures, one column per clade.
  A full-coverage (root) clade equals the annogroup's `Sequence_Count`.
- **`annogroup_tree_counts_per_structure/…-<structure>.tsv`** — the same
  per-clade member-protein counts laid out one file per species-tree structure
  (clades ordered root → tips within that structure). Downstream OCL reads the
  file for the structure it is analyzing.
- **`…-annogroup_sequences_per_species.tsv`** — the wide per-species companion to
  the deconvolution: per annogroup (feature / combination / architecture; the
  absent annogroup is excluded) with its annotation definitions, one column per
  species holding that annogroup's member sequence identifiers — the wide form of
  the long membership table.

## Consumers

`ocl_phylogenetic_structures` (annotations_X_ocl) and `integrator` consume
annogroup membership to relate features to orthogroups and species-tree
structures, and the per-structure **tree-counts** for species-tree
deconvolution. See the subproject [`../AI_GUIDE.md`](../AI_GUIDE.md).

Updated whenever `BLOCK_build_annogroups` is re-run.
