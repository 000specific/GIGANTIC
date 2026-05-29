# AI Guide — Phyloname Tree Generator (workflow layer)

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 29
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent template README: [`../README.md`](../README.md)
- Parent toolkit AI guide:  [`../../AI_GUIDE.md`](../../AI_GUIDE.md)
- Top-level toolkit README: [`../../README.md`](../../README.md)

---

## What this workflow does

Generates a binary species-tree Newick from phylonames + backbone + optional internal-clade constraints, then symlinks it into the trees_species canonical workflow.

## Inputs

| YAML key | Default | Description |
|---|---|---|
| `inputs.phylonames` | species42 phylonames map | Phylonames TSV (positional read: col 0 = genus_species, col 1 = phyloname) |
| `inputs.config_file` | `INPUT_user/tree_config.yaml` | Backbone topology + assignment rules + internal-clade constraints + seed |
| `inputs.trees_species_input_user_dir` | species42 BLOCK_gigantic_species_tree INPUT_user | Target for the bridge symlink |
| `prefix` | `species42` | Output filename prefix |
| `seed` | `42` | RNG seed for reproducible polytomy resolution |

## Outputs

```
OUTPUT_pipeline/
├── 1-output/                                          (generate)
│   ├── <prefix>-seed<SEED>-species_tree.newick
│   ├── <prefix>-seed<SEED>-decision_log.tsv
│   ├── <prefix>-seed<SEED>-internal_constraints_applied.tsv
│   ├── <prefix>-seed<SEED>-ambiguity_summary.md
│   └── 1_ai-log-generate_species_tree.log
├── 2-output/                                          (validate)
│   ├── 2_ai-validation_pass.txt
│   └── 2_ai-log-validate_outputs.log
└── 3-output/                                          (bridge)
    └── 3_ai-log-bridge_to_trees_species.log

ai/logs/run_<timestamp>-subproject-trees_species_success.log  (§45 run log)
```

After a successful run, `<trees_species_input_user_dir>/species_tree.newick` is an absolute symlink to the validated Newick in `OUTPUT_pipeline/1-output/`.

## Process chain

| Process | Script | Inputs | Outputs |
|---|---|---|---|
| `generate_species_tree`     | `001_*.py` | `params.phylonames`, `params.config_file`, `params.seed` | `1-output/*` |
| `validate_outputs`          | `002_*.py` | `1-output/*.newick` | `2-output/2_ai-validation_pass.txt` |
| `bridge_to_trees_species`   | `003_*.py` | `1-output/*.newick`, `params.trees_species_input_user_dir` | symlink + `3-output/` log |
| `write_run_log`             | `004_*.py` | gate from bridge | `ai/logs/run_<timestamp>-*.log` |

## Algorithm at a glance

1. Phylonames → species records (positional column read).
2. Backbone-leaf assignment (rules in `tree_config.yaml::backbone_leaves`).
3. Below-leaf taxonomic dict per backbone leaf.
4. Apply `internal_clade_constraints` at each polytomy node.
5. Randomly pair any remaining > 2 children (seeded RNG).
6. Substitute subtrees into the user's `backbone_topology`.
7. Strip outer unary wrapper; emit unlabeled binary Newick.

## Failure semantics

- Species unassigned to a backbone leaf → exit 1
- Internal-clade constraint with missing siblings → exit 1 (a constraint must apply cleanly or the user's intent is ambiguous)
- Newick not strictly binary, duplicate leaves, reserved labels → script 002 exits 1
- `errorStrategy = 'terminate'`, `maxErrors = 0` in nextflow.config

## See also

- `../README.md`            — template-level user-facing README
- `../INPUT_user/README.md` — tree_config.yaml schema
- `../../AI_GUIDE.md`       — toolkit-level AI guide
- `subprojects/trees_species/BLOCK_gigantic_species_tree/AI_GUIDE.md` — downstream consumer
