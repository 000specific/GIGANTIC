# BLOCK_orthohmm_GIGANTIC — Parallel-Phmmer OrthoHMM Workflow

This workflow runs OrthoHMM orthogroup detection with the slow phmmer
all-vs-all step parallelized across SLURM burst-mode job arrays. Same
biological output as standard OrthoHMM, dramatically faster wall time.

**Use this workflow when** you have ≥ 30 species and standard OrthoHMM
(`../BLOCK_orthohmm/workflow-COPYME-run_orthohmm/`) would take days.

For smaller species sets, the standard workflow is simpler.

## Quick Start

1. **Edit `START_HERE-user_config.yaml`** — set `inputs.proteomes_dir` to
   point at your `genomesDB STEP_4 species{N}_gigantic_T1_proteomes/`
   directory and (optionally) set `slurm_mail_user` for email notifications.
2. **Run** `bash RUN-workflow.sh` — submits a long-running driver SLURM job
   that itself fans phmmer out as ~49 SLURM job arrays on burst QOS.
3. **Wait** — for 70 species, expect a few hours of wall time.
4. **Check outputs** in `OUTPUT_pipeline/` and the `output_to_input/BLOCK_orthohmm_GIGANTIC/`
   symlinks for downstream consumption.

## What Happens

```
RUN-workflow.sh ──▶ SLURM driver job (10 d walltime, moroz QOS)
                     │
                     └─▶ NextFlow pipeline (ai/main.nf)
                          │
                          ├─ 001 validate proteomes
                          ├─ 002 convert headers to short IDs
                          ├─ 003 extract phmmer commands via OrthoHMM --stop prepare
                          ├─ 004 run_phmmer_pair (× ~4,830, fan-out)
                          │      └─▶ ~49 SLURM array submissions on moroz-b burst QOS
                          ├─ 005 pool & verify all phmmer outputs (silent-artifact gate)
                          ├─ 006 OrthoHMM --start search_res (Steps 2-5)
                          ├─ 007 restore GIGANTIC long-form identifiers
                          ├─ 008 summary statistics
                          ├─ 009 per-species QC
                          └─ 010 timestamped run log
```

After the pipeline completes, `RUN-workflow.sh` creates symlinks in
`../../output_to_input/BLOCK_orthohmm_GIGANTIC/` for downstream subprojects.

## Files at a Glance

| File | What it does | User edits? |
|---|---|---|
| `START_HERE-user_config.yaml` | Resources, paths, OrthoHMM params, SLURM account/QOS, email | **YES** |
| `RUN-workflow.sh` | Single entry point: env setup, SLURM self-submission, NextFlow run, output_to_input symlinks | No |
| `ai/main.nf` | NextFlow pipeline (10 processes) | No |
| `ai/nextflow.config` | Per-label process resources (yaml-driven), SLURM executor for phmmer_pair, `array = 100` | No |
| `ai/scripts/*` | Numbered scripts implementing each process | No |
| `INPUT_user/` | Reserved for any user-provided inputs (none required for default config) | Optional |

## Configuration Cheat-Sheet

The config yaml has six sections you might edit:

```yaml
project:                         # cosmetic name in logs
inputs:
  proteomes_dir: "..."           # PATH from this workflow root to your proteomes
orthohmm:
  evalue: "0.0001"
  single_copy_threshold: "0.5"
resources:                       # per-process cpu/mem/time
  phmmer_pair: {cpus, memory_gb, time_hours}        # fan-out task
  orthohmm_finalize: {cpus, memory_gb, time_hours}  # Steps 2-5
  local_step: {cpus, memory_gb, time_hours}         # lightweight steps
execution_mode: "slurm"          # or "local"
slurm_account / slurm_qos        # driver job (long-running)
slurm_burst_account / slurm_burst_qos     # fan-out tasks (burst)
slurm_mail_user                  # leave "" to disable email
conda:
  environment: "ai_gigantic_orthogroups_orthohmm"
resume: false                    # NextFlow -resume cache reuse
```

**HiPerGator memory rule:** `memory_gb ≤ 7.5 × cpus`. If memory is the bottleneck, increase cpus.

## Outputs

Real files in `OUTPUT_pipeline/`:
- `1-output/` validated proteome list
- `2-output/` short-header proteomes + header mapping
- `3-output/` phmmer pair manifest (extracted from `--stop prepare`)
- `4-output/` pooled phmmer outputs + verification report (one row per pair: PRESENT, MISSING, MALFORMED)
- `5-output/` OrthoHMM finalize results
- `6-output/` orthogroups with GIGANTIC long-form IDs
- `7-output/` summary statistics
- `8-output/` per-species QC

Symlinks in `output_to_input/BLOCK_orthohmm_GIGANTIC/`:
- `orthogroups_gigantic_ids.tsv`
- `gene_count_gigantic_ids.tsv`
- `summary_statistics.tsv`
- `per_species_summary.tsv`

Filenames match `BLOCK_orthohmm` so downstream subprojects can consume from either.

## When Things Go Wrong

| Symptom | Look at |
|---|---|
| Driver job failed quickly | `slurm_logs/orthohmm_GIGANTIC-*.log` |
| Phmmer fan-out tasks failing | NextFlow `work/` dirs and `slurm_logs/` from the burst array tasks |
| Pool verification report shows MISSING/MALFORMED | `OUTPUT_pipeline/4-output/4_ai-pool_verification_report.tsv` |
| Need to start fresh | `rm -rf work .nextflow .nextflow.log* OUTPUT_pipeline` then re-run |

For deeper debugging guidance see `ai/AI_GUIDE-orthohmm_GIGANTIC_workflow.md`.

## See Also

- BLOCK-level guide: `../AI_GUIDE-orthohmm_GIGANTIC.md`
- Workflow execution guide (AI-oriented): `ai/AI_GUIDE-orthohmm_GIGANTIC_workflow.md`
- Standard (non-arrayed) variant: `../../BLOCK_orthohmm/workflow-COPYME-run_orthohmm/README.md`
