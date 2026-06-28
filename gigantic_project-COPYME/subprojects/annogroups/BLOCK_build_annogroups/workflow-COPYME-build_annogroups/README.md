<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 18
Human:   Eric Edsinger
Purpose: Runbook for the build_annogroups workflow (COPYME template).
Scope:   workflow-COPYME-build_annogroups.
============================================================================ -->

# workflow — build_annogroups (COPYME template)

Builds the four canonical annogroup types per annotation source. This is the
**COPYME template** — copy it to `workflow-RUN_N-build_annogroups/` for a real
run (the template stays clean; execution artifacts live in the RUN copy).

## Quick start

```bash
# from the BLOCK directory:
cp -r workflow-COPYME-build_annogroups workflow-RUN_1-build_annogroups
cd workflow-RUN_1-build_annogroups

# 1. Edit START_HERE-user_config.yaml (see below)
# 2. Run (creates the conda env on first run):
export TMPDIR=/tmp        # if submitting to SLURM (avoids the Claude TMPDIR footgun)
bash RUN-workflow.sh
```

## What to edit in `START_HERE-user_config.yaml`

| Key | What |
|-----|------|
| `species_set_name` | drives the proteome universe (e.g. `species70`) |
| `sources` | `"all"` (every parser plugin: pfam, panther, go) or a subset like `[ pfam, panther ]` |
| `go_term_origins` | (go parser only) GO origins to include: `[ "InterPro", "PANTHER" ]` (union, default) or `[ "InterPro" ]` (curated only) |
| `inputs.annotations_hmms_dir` | `annotations_hmms/output_to_input` root (each parser appends its own subpath) |
| `inputs.proteomes_dir` | `genomesDB/output_to_input/STEP_4-…/<set>_gigantic_T1_proteomes` |
| `execution_mode` | `local` (run here) or `slurm` (self-submit); set `slurm_account` + `slurm_qos` for slurm |
| `parallelism_mode` | `local` (per-source tasks within this allocation) or `slurm` (each source its own job) |
| `cpus`, `memory_gb`, `time_hours` | resources |
| `resume` | `true` to reuse NextFlow `work/` cache |

## Prerequisites (upstream `output_to_input/` must be populated)

- `annotations_hmms/output_to_input/BLOCK_interproscan_parsed/<db>/` (e.g. `pfam/`, `panther/`)
- `annotations_hmms/output_to_input/BLOCK_interproscan/*_interproscan_results.tsv` (raw, for the `go` parser)
- `genomesDB/output_to_input/STEP_4-create_final_species_set/<set>_gigantic_T1_proteomes/*.aa`

## Outputs

```
OUTPUT_pipeline/
├── 1-output/   1_ai-sources_manifest.tsv, 1_ai-proteome_universe.tsv
├── 2-output/<source>/  2_ai-<source>-annogroup_map.tsv
│                       2_ai-<source>-annogroup_membership.tsv
│                       2_ai-<source>-dropped_orphan_sequences.tsv
├── 3-output/<source>/  3_ai-<source>-validation_report.txt
├── 4-output/<source>/  4_ai-<source>-annogroup_tree_counts-all_structures.tsv
│                       annogroup_tree_counts_per_structure/   (one file per structure)
├── 5-output/<source>/  5_ai-<source>-annogroup_sequences_per_species.tsv
├── 6-output/<source>/  6_ai-<source>-composite_clades-per_annogroup.tsv
│                       6_ai-<source>-composite_clades-summary_counts.tsv
│                       composite_clades_detail_tables/        (one per composite clade)
└── 7-output/   7_ai-annogroups_summary.tsv              (per source: per-type breakdown)
                7_ai-annogroups_summary-per_species.tsv  (species x sources)
                7_ai-annogroups_summary-per_phylum.tsv   (phylum x sources)
```

Downstream symlinks are created at
`../../output_to_input/BLOCK_build_annogroups/<species_set>/<source>/`.

## Reference runs (species70)

**pfam** (2026-06-18, end-to-end NextFlow, local): universe = 1,375,926 sequences;
pfam-annotated = 922,233; **137,762 annogroups** (10,635 feature + 46,846
combination + 80,280 architecture + 1 absent holding 453,693 sequences); validation
**PASS**; 7 truncated orphan IDs dropped (audited).

**panther + go** (2026-06-28, build + validate, scripts 001–003): same universe.
- panther (positional, 4 types): 11,033 feature + 11,033 combination + 11,051
  architecture + 1 absent (418,016 seqs); validation **PASS**; 7 orphans dropped.
- go (whole-protein, 3 types — no architecture): 8,994 feature + 27,974 combination
  + 1 absent (539,984 seqs); validation **PASS**; 6 orphans dropped; GO origins =
  InterPro + PANTHER (default union, `go_term_origins`). GO build ≈ 45 s (reads the
  raw per-species InterProScan results).

See [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md) for execution detail and troubleshooting,
and [`../AI_GUIDE.md`](../AI_GUIDE.md) for the parser contract.
