<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 27
Human:   Eric Edsinger
Purpose: Landing page for the BLOCK_ambiguous_nodes_X_annogroups integrator BLOCK.
Scope:   This BLOCK and its workflow.
============================================================================ -->

# BLOCK_ambiguous_nodes_X_annogroups

**The first BLOCK in the integrator `ambiguous_nodes_X_*` series.** It collapses
an upstream subproject's per-structure analysis down to **only the ambiguous
nodes** — the clades that define the alternative species-tree structures — and
reports them in three scopes (**one / some / all** structures). Here the upstream
is **annogroups**.

## In one sentence

For each annotation source (pfam, go, panther), take the annogroups species-tree
**deconvolution** (per annogroup, a member-protein count for every clade across
all structures) and keep only the **ambiguous-node** columns — the unresolved
basal-metazoan groupings — in three structure scopes, so you can ask *"how many
of each annogroup's proteins fall under each contested basal-metazoan grouping?"*
for one structure, a chosen subset, or all of them.

## The `ambiguous_nodes_X_*` pattern

An **ambiguous node** is a clade present in some but not all of the species-tree
structures (for species70: the internal groupings of Ctenophora / Porifera /
Placozoa / Cnidaria / Bilateria below Metazoa). Most of a per-structure analysis
is identical across structures; the ambiguous nodes are where structures
actually differ. The `ambiguous_nodes_X_<upstream>` series collapses an upstream
analysis to just those nodes, in three user-controllable structure scopes. This
BLOCK realizes the pattern for `annogroups`; future BLOCKs can realize it for
other upstreams.

## What it is (and is not)

- **Is**: a pure column projection of annogroups' own deconvolution output. No
  count is recomputed (Rule 6 — a `clade_id_name` has a fixed species set, hence
  a fixed count, in every structure it appears in). No new biology.
- **Is not**: an OCL/origin analysis, and **not** the annogroups `composite_clades`
  lens (the exact basal-phylum signature of each annogroup) — that stays in the
  annogroups subproject and is out of scope here.

## Status

Built 2026-06-27 (scaffold + scripts). Targets the annogroups deconvolution
exposed in `annogroups/output_to_input/BLOCK_build_annogroups/<species_set>/<source>/`.

## Layout

```
BLOCK_ambiguous_nodes_X_annogroups/
├── README.md          # this file
├── AI_GUIDE.md        # BLOCK-level AI guide
└── workflow-COPYME-ambiguous_nodes_X_annogroups/
    ├── README.md                     # user quick start
    ├── RUN-workflow.sh               # unified driver (§29; local or SLURM)
    ├── START_HERE-user_config.yaml   # source dial + structure scopes
    ├── upload_manifest.tsv
    ├── INPUT_user/                   # SOME-scope structure manifest (optional)
    └── ai/
        ├── AI_GUIDE.md
        ├── main.nf
        ├── nextflow.config
        ├── conda_environment.yml     # env: aiG-integrator-ambiguous_nodes_X_annogroups
        └── scripts/                  # 001 resolve, 002 project, 003 validate, 004 run-log, utils
```

See `workflow-COPYME-ambiguous_nodes_X_annogroups/README.md` to run it.
