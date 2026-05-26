# BLOCK_orthofinder_array — Parallel-DIAMOND OrthoFinder Workflow

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK: [`../AI_GUIDE.md`](../AI_GUIDE.md) — BLOCK_orthofinder_array concepts (fan-out architecture)
- Parent subproject: [`../../README.md`](../../README.md) — orthogroups overview
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Reads from: `../../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs to: `../../output_to_input/BLOCK_orthofinder_array/` (bit-identical to BLOCK_orthofinder output)
- Standard variant (< 20 species, simpler): `../../BLOCK_orthofinder/workflow-COPYME-run_orthofinder/`

---

This workflow runs OrthoFinder orthogroup detection with the slow DIAMOND
all-vs-all step parallelized across SLURM burst-mode job arrays. Same
biological output as standard OrthoFinder, dramatically faster wall time.

**Use this workflow when** you have ≥ 30 species and standard OrthoFinder
(`../BLOCK_orthofinder/workflow-COPYME-run_orthofinder/`) would take days.

For smaller species sets, the standard workflow is simpler.

## Quick Start

1. **Edit `START_HERE-user_config.yaml`** — set `inputs.proteomes_dir` to
   point at your `genomesDB STEP_4 species{N}_gigantic_T1_proteomes/`
   directory and (optionally) set `slurm_mail_user` for email notifications.
2. **Run** `bash RUN-workflow.sh` — submits a long-running driver SLURM job
   that fans DIAMOND out as ~49 SLURM job arrays on burst QOS.
3. **Wait** — for 70 species, expect ~hours of wall time.
4. **Check outputs** in `OUTPUT_pipeline/` and `output_to_input/BLOCK_orthofinder_array/`
   for downstream consumption.

## What Happens

```
RUN-workflow.sh ──▶ SLURM driver job (10 d walltime, moroz QOS)
                     │
                     └─▶ NextFlow pipeline (ai/main.nf)
                          │
                          ├─ 001 validate proteomes
                          ├─ 002 prepare for OrthoFinder input format
                          ├─ 003 extract DIAMOND commands via OrthoFinder -op
                          ├─ 004 run_diamond_pair (× ~4,830, fan-out, inline)
                          │      └─▶ ~49 SLURM array submissions on moroz-b burst QOS
                          ├─ 005 pool & verify all DIAMOND outputs (silent-artifact gate)
                          ├─ 006 OrthoFinder -b (clustering + trees + reconciliation)
                          ├─ 007 standardize output to GIGANTIC format
                          ├─ 008 summary statistics
                          ├─ 009 per-species QC
                          └─ 010 timestamped run log
```

After the pipeline completes, `RUN-workflow.sh` creates symlinks in
`../../output_to_input/BLOCK_orthofinder_array/` for downstream subprojects.

## Files at a Glance

| File | What it does | User edits? |
|---|---|---|
| `START_HERE-user_config.yaml` | Resources, paths, OrthoFinder params, SLURM, email | **YES** |
| `RUN-workflow.sh` | Single entry point: env setup, SLURM self-submission, NextFlow run, output_to_input symlinks | No |
| `ai/main.nf` | NextFlow pipeline (10 processes) | No |
| `ai/nextflow.config` | Per-label process resources (yaml-driven), SLURM executor for diamond_pair, `array = 100` | No |
| `ai/scripts/*` | 9 numbered scripts (no `004` — DIAMOND pair runs inline in main.nf) | No |
| `INPUT_user/` | Reserved for any user-provided inputs | Optional |

## Configuration Cheat-Sheet

```yaml
project:                         # cosmetic name in logs
inputs:
  proteomes_dir: "..."           # PATH from this workflow root to your proteomes
orthofinder:
  search_method: "diamond"       # or "blast"
  mcl_inflation: "1.5"
resources:                       # per-process cpu/mem/time
  diamond_pair: {cpus, memory_gb, time_hours}        # fan-out task
  orthofinder_finalize: {cpus, memory_gb, time_hours}  # clustering + trees + reconciliation
  local_step: {cpus, memory_gb, time_hours}          # lightweight steps
execution_mode: "slurm"          # or "local"
slurm_account / slurm_qos        # driver job
slurm_burst_account / slurm_burst_qos     # fan-out tasks (burst)
slurm_mail_user                  # leave "" to disable email
conda:
  environment: "aiG-orthogroups-orthofinder"
resume: false
```

**HiPerGator memory rule:** `memory_gb ≤ 7.5 × cpus`.

## Outputs

Real files in `OUTPUT_pipeline/`:
- `1-output/` validated proteome list
- `2-output/` prepared OrthoFinder-input proteomes
- `3-output/` DIAMOND pair manifest + OrthoFinder workdir + raw `-op` stdout
- `4-output/` (none — fan-out outputs go to 5-output/)
- `5-output/` pooled DIAMOND outputs + verification report
- `6-output/` OrthoFinder finalize results (clustering + trees + reconciliation)
- `7-output/` orthogroups standardized to GIGANTIC long-form IDs
- `8-output/` summary statistics
- `9-output/` per-species QC

Symlinks in `output_to_input/BLOCK_orthofinder_array/`:
- `orthogroups_gigantic_ids.tsv`
- `gene_count_gigantic_ids.tsv`
- `summary_statistics.tsv`
- `per_species_summary.tsv`

Filenames match `BLOCK_orthofinder` and `BLOCK_orthohmm_GIGANTIC` so
downstream subprojects (e.g., `BLOCK_comparison`) can consume from any.

## When Things Go Wrong

| Symptom | Look at |
|---|---|
| Driver job failed quickly | `slurm_logs/orthofinder_array-*.log` |
| DIAMOND fan-out tasks failing | NextFlow `work/` dirs and `slurm_logs/` from burst array tasks |
| Pool verification: MISSING/EMPTY pairs | `OUTPUT_pipeline/5-output/5_ai-pool_verification_report.tsv` |
| Tree inference slow | Increase `resources.orthofinder_finalize.cpus` |
| Need to start fresh | `rm -rf work .nextflow .nextflow.log* OUTPUT_pipeline` then re-run |

For deeper debugging see `ai/AI_GUIDE.md`.

## See Also

- BLOCK-level guide: `../AI_GUIDE.md`
- Workflow execution guide (AI-oriented): `ai/AI_GUIDE.md`
- Standard (non-arrayed) variant: `../../BLOCK_orthofinder/workflow-COPYME-run_orthofinder/README.md`
