# INPUT_user

This directory is reserved for future user-provided inputs to the tree visualization workflow (e.g., custom color palettes, tip annotation files, species-grouping overrides).

Currently the workflow reads everything it needs from:
- `START_HERE-user_config.yaml` (styling options)
- `../../../output_to_input/<gene_family>/STEP_2-phylogenetic_analysis/` (tree newick files)

So this directory is empty by design. Leave it in place — future workflow revisions may add optional overrides here.
