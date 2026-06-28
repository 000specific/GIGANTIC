<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 27
Human:   Eric Edsinger
Purpose: What the user provides in INPUT_user/ for ambiguous_nodes_X_annogroups.
============================================================================ -->

# INPUT_user — ambiguous_nodes_X_annogroups

This BLOCK reads its scientific inputs from upstream `output_to_input/` (the
annogroups deconvolution); it does **not** need user-provided data files. The
only thing you may edit here defines the **SOME** structure scope.

## `some_structures_manifest.tsv`

Defines the subset of species-tree structures the **some** scope covers. Edit it
to list the `Structure_ID`s you care about (a `Structure_ID` column, or a bare
one-id-per-line list). Blank and `#` lines are ignored.

- The resolved SOME set is the **union** of this file and the inline
  `structure_scopes.some.structure_ids` list in `START_HERE-user_config.yaml`.
  Use either or both.
- A natural source is a `trees_species/BLOCK_user_requests` run: it resolves a
  topological hypothesis (e.g. "Ctenophora sister to all other Metazoa") to the
  matching structure ids — point `selected_structures_file` at that output, or
  paste its ids here.
- If you only use the inline list, set
  `structure_scopes.some.selected_structures_file: ""` in the config.

## Everything else lives in the config

`run_label`, `species_set_name`, the source dial (`annotation_sources`), the
`one` structure, and which scopes are enabled are all set in
`../START_HERE-user_config.yaml`.
