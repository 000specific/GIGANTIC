<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 18
Human:   Eric Edsinger
Purpose: Workflow-execution AI guide for build_annogroups (LEVEL 3) — step-by-
         step run, the NextFlow DAG, and common execution errors.
Scope:   Running the build_annogroups workflow.
============================================================================ -->

# AI_GUIDE — build_annogroups workflow (execution)

**For AI assistants**: Read the BLOCK guide ([`../../AI_GUIDE.md`](../../AI_GUIDE.md))
first for the build pipeline and the parser contract, and the subproject guide
([`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)) for the annogroup concept. This
guide focuses on **running** the workflow.

## How a run flows

`RUN-workflow.sh` (§29 unified driver) does, in order:

1. Reads `START_HERE-user_config.yaml` (flat keys via `read_config`).
2. If `execution_mode: slurm` and not already in a job → self-submits via
   `sbatch --wrap` and exits. Otherwise runs here.
3. Creates/activates the per-BLOCK conda env `aiG-annogroups-build_annogroups`
   (from `ai/conda_environment.yml`; mamba, conda fallback). This env provides
   `nextflow>=23,<26` — see the pin below.
4. Runs `nextflow run ai/main.nf -params-file START_HERE-user_config.yaml`
   with `-profile local` or `-profile standard` (per `parallelism_mode`).
5. After success, creates `output_to_input/` symlinks for downstream consumers
   and writes `RUN_SUMMARY.md`.

## The NextFlow DAG (`ai/main.nf`)

```
resolve_sources_and_universe (once)
        │  writes 1_ai-sources_manifest.tsv
        ▼  .splitCsv(header:true).map{ row -> row.source }   ← per-source fan-out
build_annogroups (per source)  ──►  validate_results (per source)
        │
        ▼  .collect()  (barrier)
write_summary (once)   → 4-output (per source / per species / per phylum)
        │
        ▼
write_run_log (once)
```

Scripts own the data: they read/write directly under `OUTPUT_pipeline/` (paths
resolved from the config relative to the workflow dir). NextFlow only manages
execution and the per-source fan-out.

## Config → params

The YAML is passed via `-params-file`, so `params.X.Y.Z` mirror the YAML shape
(`params.output.base_dir`, `params.species_set_name`). `RUN-workflow.sh` injects
`slurm_account`/`slurm_qos`/`cpus`/`memory_gb` for the executor. This is the
universal GIGANTIC YAML→params pattern — do not flatten the YAML.

## Common execution errors

| Symptom | Cause | Fix |
|---------|-------|-----|
| NextFlow DSL/syntax errors on perfectly good `main.nf` | system `nextflow` is 26.x (strict DSL) | use the env's pinned `<26` nextflow; the env yml pins `nextflow>=23.0,<26.0` |
| conda env create fails on a compute node (`/tmp/claude-*` missing) | Claude sets `TMPDIR=/tmp/claude-<pid>`; sbatch exports it | `export TMPDIR=/tmp` before `bash RUN-workflow.sh` |
| `CRITICAL ERROR: no proteome (*.aa) files` | `inputs.proteomes_dir` wrong / genomesDB STEP_4 not populated | point at the species-set proteomes under genomesDB `output_to_input/STEP_4-…` |
| `CRITICAL ERROR: <source> annotation directory not found` | annotations_hmms hasn't exposed that source's `output_to_input/` | run/parse that source upstream, or drop it from `sources:` |
| `requested source 'X' has no parser` | `sources:` lists a source with no `parsers/X.py` | add the parser plugin or correct `sources:` |
| validation FAIL: `outside-universe` / membership rows not in universe | annotation IDs don't match proteome headers (truncated/orphan) | small count → accepted drop (see WARNING note); large count → systematic mismatch, investigate the parser |
| stale results after editing a script | NextFlow `work/` cache | `rm -rf work .nextflow .nextflow.log*` and re-run without `-resume` (or set `resume: false`) |

## Re-running cleanly

```bash
cd workflow-RUN_N-build_annogroups
rm -rf work .nextflow .nextflow.log* OUTPUT_pipeline slurm_logs
export TMPDIR=/tmp
bash RUN-workflow.sh
```

## Diagnostics

- Per-source counts are printed by Script 002:
  `[002 <source>] feature=… combination=… architecture=… absent=…`.
- Cross-source summary tables (per source / species / phylum): `OUTPUT_pipeline/4-output/`.
- Validation status: `OUTPUT_pipeline/3-output/<source>/3_ai-<source>-validation_report.txt`.
- Dropped orphans: `OUTPUT_pipeline/2-output/<source>/2_ai-<source>-dropped_orphan_sequences.tsv`.
- NextFlow trace/report/timeline: `OUTPUT_pipeline/pipeline_*.{txt,html}`.
