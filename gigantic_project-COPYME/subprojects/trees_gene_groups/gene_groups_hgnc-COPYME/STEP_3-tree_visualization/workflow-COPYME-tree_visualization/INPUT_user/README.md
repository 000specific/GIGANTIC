# INPUT_user

Reserved for optional user-provided inputs to the tree visualization workflow (e.g., custom color palettes, tip annotation files, species-grouping overrides).

Currently the orchestrator reads everything it needs from:
- `../START_HERE-user_config.yaml` (orchestration settings + styling)
- `<step2_output_to_input_dir>/gene_group-<gene_family>/` (tree newick files; path configured in YAML)

So this directory is empty by design. Leave it in place — future workflow revisions may add optional overrides here.
