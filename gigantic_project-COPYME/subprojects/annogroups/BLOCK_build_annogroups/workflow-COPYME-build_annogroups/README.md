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
| `sources` | `"all"` (every source with a parser plugin + data) or a subset like `[ pfam, gene3d ]` |
| `inputs.annotations_hmms_dir` | `annotations_hmms/output_to_input` root (each parser appends its own subpath) |
| `inputs.proteomes_dir` | `genomesDB/output_to_input/STEP_4-…/<set>_gigantic_T1_proteomes` |
| `execution_mode` | `local` (run here) or `slurm` (self-submit); set `slurm_account` + `slurm_qos` for slurm |
| `parallelism_mode` | `local` (per-source tasks within this allocation) or `slurm` (each source its own job) |
| `cpus`, `memory_gb`, `time_hours` | resources |
| `resume` | `true` to reuse NextFlow `work/` cache |

## Prerequisites (upstream `output_to_input/` must be populated)

- `annotations_hmms/output_to_input/BLOCK_interproscan_parsed/<db>/` (e.g. `pfam/`)
- `genomesDB/output_to_input/STEP_4-create_final_species_set/<set>_gigantic_T1_proteomes/*.aa`

## Outputs

```
OUTPUT_pipeline/
├── 1-output/   1_ai-sources_manifest.tsv, 1_ai-proteome_universe.tsv
├── 2-output/<source>/  2_ai-<source>-annogroup_map.tsv
│                       2_ai-<source>-annogroup_membership.tsv
│                       2_ai-<source>-dropped_orphan_sequences.tsv
├── 3-output/<source>/  3_ai-<source>-validation_report.txt
└── 4-output/   4_ai-annogroups_summary.tsv              (per source: per-type breakdown)
                4_ai-annogroups_summary-per_species.tsv  (species x sources)
                4_ai-annogroups_summary-per_phylum.tsv   (phylum x sources)
```

Downstream symlinks are created at
`../../output_to_input/BLOCK_build_annogroups/<species_set>/<source>/`.

## Reference run (pfam, species70, 2026-06-18)

End-to-end NextFlow run, local: universe = 1,375,926 sequences; pfam-annotated =
922,233; **137,762 annogroups** (10,635 feature + 46,846 combination + 80,280
architecture + 1 absent holding 453,693 sequences); validation **PASS**; 7
truncated orphan IDs dropped (audited). Build process ≈ 20 s + universe build.

See [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md) for execution detail and troubleshooting,
and [`../AI_GUIDE.md`](../AI_GUIDE.md) for the parser contract.
