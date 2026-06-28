<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 27
Human:   Eric Edsinger
Purpose: Workflow-level (LEVEL 3) AI guide — running ambiguous_nodes_X_annogroups.
Scope:   This workflow's execution: scripts, verification, common errors.
============================================================================ -->

# AI_GUIDE — ambiguous_nodes_X_annogroups (workflow)

**For AI Assistants**: Read the subproject guide
(`../../AI_GUIDE.md`) first for the integrator overview, then the BLOCK guide
(`../AI_GUIDE.md`). This guide focuses on running the workflow.

| User needs... | Go to... |
|---|---|
| GIGANTIC overview, conventions | `../../../../AI_GUIDE.md`, `../../../../ai/ai_FYIs/gigantic_conventions.md` |
| integrator subproject concepts | `../../../AI_GUIDE.md` |
| this BLOCK's concepts | `../AI_GUIDE.md` |
| running this workflow (this file) | here |

## The pipeline

| Script | Process | Reads | Writes |
|--------|---------|-------|--------|
| `001_ai-python-resolve_ambiguous_nodes.py` | `resolve_ambiguous_nodes` | deconvolution headers (no data rows) + per-structure headers | `1-output/<source>/` registry + structure sets |
| `002_ai-python-project_annogroups_to_ambiguous_nodes.py` | `project_annogroups` | `4_ai-<source>-annogroup_tree_counts-all_structures.tsv` | `2-output/<source>/{all,one,some}/` projections |
| `003_ai-python-validate_results.py` | `validate_results` | 1-output + 2-output + source table | `3-output/3_ai-validation_report.txt` |
| `004_ai-python-write_run_log.py` | `write_run_log` | — | `ai/logs/run_*.log` |

Each script loops over the resolved annotation sources internally (the source
dial is `annotation_sources` in the config), so there is no per-source NextFlow
fan-out. The substrate is read straight from `output_to_input`; nothing is
recomputed (Rule 6 — counts are structure-invariant per `clade_id_name`).

## How an ambiguous node is identified

The deconvolution clade column header ends `... present in N of M structures`.
`utils_ambiguous_nodes.parse_clade_column_header` extracts `(clade_id_name, N, M)`;
a clade is ambiguous iff `N < M`. This is the single load-bearing signal — the
block needs no separate trees_species read to find the ambiguous set. The
per-structure files supply each structure's own clade set (header only) for the
`one`/`some` scopes.

## Run it

```bash
bash RUN-workflow.sh           # local or SLURM per execution_mode
```

## Verify a run

```bash
# Validation status
tail -3 OUTPUT_pipeline/3-output/3_ai-validation_report.txt   # expect: STATUS: PASS

# Ambiguous-node counts per source
for f in OUTPUT_pipeline/1-output/*/1_ai-*-structure_sets.tsv; do echo "== $f =="; column -t -s$'\t' "$f"; done

# A projected table's column count = identity cols + ambiguous-node cols
head -1 OUTPUT_pipeline/2-output/pfam/all/2_ai-pfam-ambiguous_nodes_X_annogroups-all_structures.tsv | tr '\t' '\n' | wc -l
```

## Common errors

| Error | Cause | Fix |
|-------|-------|-----|
| `annogroups species dir not found` | `inputs.annogroups_dir`/`species_set_name` wrong, or annogroups not exposed | `ls ../../../annogroups/output_to_input/BLOCK_build_annogroups/<species_set>/` |
| `source 'X' has no deconvolution all_structures table` | source name typo, or annogroups didn't expose `4-output` | check the source dir for `4_ai-<source>-annogroup_tree_counts-all_structures.tsv` |
| `per-structure tree-counts file not found` | a `one`/`some` structure id doesn't exist | use `structure_001 .. structure_NNN`; check Script 001 registry for valid ids |
| `scope 'X' resolved to ZERO ambiguous columns` | the chosen structure(s) carry no ambiguous nodes (unlikely) or wrong ids | inspect `1-output/<source>/1_ai-<source>-ambiguous_node_registry.tsv` |
| `SOME scope ... resolved to zero structures` | `some` enabled but no inline ids and empty/blank `selected_structures_file` | add ids or a file, or disable the `some` scope |
| stale `work/`/`.nextflow*` masking a fix | NF cache | `rm -rf work .nextflow .nextflow.log* slurm_logs` then re-run (no `-resume`) |

## Conda env

`aiG-integrator-ambiguous_nodes_X_annogroups` (§28/§53), auto-created on first
`RUN-workflow.sh`. Pure-Python (pyyaml only).
