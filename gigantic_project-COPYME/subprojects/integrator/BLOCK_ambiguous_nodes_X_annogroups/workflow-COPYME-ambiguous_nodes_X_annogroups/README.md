<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 27
Human:   Eric Edsinger
Purpose: User-facing quick start for the ambiguous_nodes_X_annogroups workflow.
============================================================================ -->

# workflow — ambiguous_nodes_X_annogroups

Collapse the annogroups **species-tree deconvolution** down to only the
**ambiguous nodes** — the clades that exist in some but not all species-tree
structures (the unresolved basal-metazoan groupings) — in three structure
scopes (**one / some / all**), for each annotation source (pfam, go, panther).

## Quick start

```bash
# 1. Edit the config (run label, source dial, structure scopes, SLURM acct/qos)
nano START_HERE-user_config.yaml

# 2. (optional) Edit the SOME structure set
nano INPUT_user/some_structures_manifest.tsv

# 3. Run (local or SLURM, per execution_mode in the config)
bash RUN-workflow.sh
```

## What it does

This is a **pure column projection** of annogroups' own output. The annogroups
deconvolution (`4_ai-<source>-annogroup_tree_counts-*.tsv`) gives, per annogroup,
a member-protein count for every clade across all structures. Each clade column
self-documents `... present in N of M structures`; a clade is an **ambiguous
node** iff `N < M`. This workflow keeps only those columns (dropping the fixed
backbone) and writes three scoped views. No counts are recomputed — a clade has
the same species set, hence the same count, in every structure it appears in
(Rule 6).

| Scope | Keeps the ambiguous nodes that… | Defined by |
|-------|--------------------------------|-----------|
| `all`  | exist in any structure | always (the global ambiguous set) |
| `one`  | exist in one chosen structure | `structure_scopes.one.structure_id` |
| `some` | exist in any of a chosen subset | inline `structure_ids` and/or `selected_structures_file` |

## Inputs (via `output_to_input`)

- annogroups: `../../../annogroups/output_to_input/BLOCK_build_annogroups/<species_set>/<source>/`
  - `4_ai-<source>-annogroup_tree_counts-all_structures.tsv` (value table + ALL scope)
  - `annogroup_tree_counts_per_structure/4_ai-<source>-annogroup_tree_counts-structure_NNN.tsv` (one/some membership)

## Outputs

```
OUTPUT_pipeline/
├── 1-output/<source>/
│   ├── 1_ai-<source>-ambiguous_node_registry.tsv   # one row per ambiguous node + scope flags
│   └── 1_ai-<source>-structure_sets.tsv            # one row per scope (all/one/some)
├── 2-output/<source>/
│   ├── all/  2_ai-<source>-ambiguous_nodes_X_annogroups-all_structures.tsv
│   ├── one/  2_ai-<source>-ambiguous_nodes_X_annogroups-<structure_id>.tsv
│   └── some/ 2_ai-<source>-ambiguous_nodes_X_annogroups-some_structures.tsv
└── 3-output/3_ai-validation_report.txt
```

Downstream consumers read the run-label-namespaced symlinks under
`../../output_to_input/BLOCK_ambiguous_nodes_X_annogroups/<run_label>/<source>/`.

## Scope note

`composite_clades` (a different annogroups lens — the exact basal-phylum
signature of each annogroup) is intentionally **out of scope** for this BLOCK.
This BLOCK operates only on the per-clade deconvolution counts.

See `ai/AI_GUIDE.md` for execution details and troubleshooting.
