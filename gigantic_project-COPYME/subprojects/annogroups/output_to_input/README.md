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
            └── 2_ai-<source>-dropped_orphan_sequences.tsv  # audit (orphan/truncated IDs)
```

## Files

- **`…-annogroup_map.tsv`** — `Annogroup_ID`, `Source`, `Annogroup_Type`
  (feature / combination / architecture / absent), `Defining_Features`,
  `Sequence_Count`, `Species_Count`.
- **`…-annogroup_membership.tsv`** — `Sequence_Identifier` (full GIGANTIC ID),
  `Genus_Species`, `Annogroup_ID`, `Annogroup_Type`,
  `Member_Architecture_Coordinates` (coordinate-tagged ordered features for
  architecture rows; empty otherwise).

## Consumers

`ocl_phylogenetic_structures` (annotations_X_ocl) and `integrator` consume
annogroup membership to relate features to orthogroups and species-tree
structures. See the subproject [`../AI_GUIDE.md`](../AI_GUIDE.md).

Updated whenever `BLOCK_build_annogroups` is re-run.
