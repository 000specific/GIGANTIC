# AI_GUIDE-orthohmm_GIGANTIC_workflow.md (Level 3: Workflow Execution Guide)

**For AI Assistants**: Read `../../AI_GUIDE-orthohmm_GIGANTIC.md` first for the BLOCK-level architecture overview. This guide focuses on running, debugging, and modifying the workflow.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../AI_GUIDE-project.md` |
| Orthogroups subproject overview | `../../../AI_GUIDE-orthogroups.md` |
| BLOCK_orthohmm_GIGANTIC architecture | `../../AI_GUIDE-orthohmm_GIGANTIC.md` |
| **Running this workflow** | This file |

## Pipeline (10 NextFlow Processes)

| # | Process | Label | What it does | Inputs | Outputs |
|---|---|---|---|---|---|
| 1 | `validate_proteomes` | `local_step` | Validates proteomes from genomesDB; emits canonical proteome_list.tsv | proteomes_dir | 1_ai-proteome_list.tsv |
| 2 | `convert_headers` | `local_step` | Converts GIGANTIC long-form headers → OrthoHMM-compatible short IDs | proteome_list | short_header_proteomes/*.pep, 2_ai-header_mapping.tsv |
| 3 | `extract_phmmer_commands` | `local_step` | Runs `orthohmm --stop prepare` to extract canonical phmmer command set | short_header_proteomes | 3_ai-phmmer_pair_manifest.tsv (simple headers!) |
| 4 | `run_phmmer_pair` | **`phmmer_pair`** (SLURM array, burst QOS) | Runs one phmmer pair per task, ~4,830 tasks total | (taxa_a, taxa_b, fasta_a, fasta_b) | A_2_B.phmmerout.txt |
| 5 | `pool_and_verify_phmmer` | `local_step` | Silent-artifact gate: verifies every pair is present and well-formed (last line `# [ok]`) | all phmmer outputs + manifest | orthohmm_working_res/ + 4_ai-pool_verification_report.tsv |
| 6 | `run_orthohmm_from_search_res` | `orthohmm_finalize` | Runs `orthohmm --start search_res` (Steps 2-5: edge thresholds, MCL, write) | pooled phmmer dir + proteomes | orthohmm_orthogroups.txt + others |
| 7 | `restore_identifiers` | `local_step` | Replaces short IDs with GIGANTIC long-form using header_mapping | OrthoHMM output + header_mapping | 6_ai-orthogroups_gigantic_ids.tsv, 6_ai-gene_count_gigantic_ids.tsv |
| 8 | `generate_summary_statistics` | `local_step` | Orthogroup-level metrics | proteome_list + orthogroups_gigantic | 7_ai-summary_statistics.tsv |
| 9 | `qc_analysis_per_species` | `local_step` | Per-species checks (gene counts, OG membership rate, single-copy count) | proteome_list + orthogroups_gigantic | 8_ai-per_species_summary.tsv |
| 10 | `write_run_log` | `local_step` | Timestamped run log | per-species summary | ai/logs/run_log_*.tsv |

## Running the Workflow

```bash
cd workflow-RUN_N-run_orthohmm_GIGANTIC/
bash RUN-workflow.sh
```

`RUN-workflow.sh` reads `execution_mode` from the yaml. With `slurm`, it
self-submits via `sbatch --wrap` as a long-running driver job. The driver
runs NextFlow which, when it reaches process 4, fans out via the SLURM
executor with `process.array = 100` (~49 array submissions to burst QOS).

## NextFlow Configuration Highlights

`ai/nextflow.config`:
- Loads `START_HERE-user_config.yaml` at the top via SnakeYAML.
- Per-label resources (`phmmer_pair`, `orthohmm_finalize`, `local_step`) come from yaml.
- `phmmer_pair` label uses `executor = 'slurm'` + `clusterOptions = "--account=${slurmBurstAccount} --qos=${slurmBurstQos}"` + `array = 100`.
- `errorStrategy = 'retry'` with `maxRetries = 2` for `phmmer_pair` (transient SLURM/network glitches across thousands of tasks).
- timeline / report / trace blocks all use `overwrite = true` (avoids the FileAlreadyExistsException seen in earlier orthohmm runs).

## Common Execution Errors

| Error | Cause | Fix |
|---|---|---|
| `input file name collision -- multiple input files for: null` | Manifest TSV header uses self-documenting `field (description)` style — NextFlow's splitCsv returns null keys | Use simple bare headers (`taxa_a\ttaxa_b\toutput_filename`). Already fixed in script 003; documented in feedback memory. |
| `Process exceeded running time limit` | Wired `time` in `nextflow.config` is too low | Confirm `withLabel: 'phmmer_pair'` uses `time = phmmerPairTime` (yaml-driven), not a hardcoded value. Set `resources.phmmer_pair.time_hours` in yaml. |
| `Timeline file already exists` (FileAlreadyExistsException) | timeline / report blocks lack `overwrite = true` | Add `overwrite = true` in nextflow.config timeline/report blocks. |
| Pool verification: many pairs MISSING | Burst tasks didn't all complete | Inspect slurm_logs/ from array tasks; rerun missing pairs. |
| Pool verification: pairs MALFORMED | Phmmer was killed mid-run (no `# [ok]` sentinel) | Often time-limit; bump `resources.phmmer_pair.time_hours`. |
| 5.7% CPU efficiency | Too many cpus per phmmer call | Phmmer scales poorly past ~8 cpus. Use 5 (default). |

## Resume vs Fresh

`resume: true` in the yaml tells NextFlow to use `-resume` (work/ cache reuse).

**Default is `false`** (fail-fast for research integrity per CLAUDE.md). If
you need to resume, set true explicitly. Note: if the upstream config
yaml or any script content changed since last run, NextFlow's content-hash
will invalidate the cache for that step + everything downstream — usually
what you want.

To restart fresh: `rm -rf work .nextflow .nextflow.log* OUTPUT_pipeline`
then `bash RUN-workflow.sh`.

## Diagnostic Commands

```bash
# Driver job status
squeue -j <DRIVER_JOB_ID> -o "%.10i %.30j %.2t %.10M %R"

# Inspect a specific NextFlow task
ls -la work/<HASH>/
cat work/<HASH>/.command.sh
cat work/<HASH>/.command.log
cat work/<HASH>/.command.err

# Check slurm logs from burst array tasks
ls slurm_logs/orthohmm_GIGANTIC-*.log

# Check per-pair verification status
column -ts $'\t' OUTPUT_pipeline/4-output/4_ai-pool_verification_report.tsv | less

# How many phmmer pairs done (during run)
ls work/*/orthohmm_working_res/*.phmmerout.txt 2>/dev/null | wc -l
```

## Modifying for a New Project

To use this workflow on a new species set:
1. `cp -a workflow-COPYME-run_orthohmm_GIGANTIC workflow-RUN_N-run_orthohmm_GIGANTIC`
2. Edit `START_HERE-user_config.yaml`:
   - `project.name` (cosmetic)
   - `inputs.proteomes_dir` (point at your genomesDB STEP_4 output)
   - `slurm_account`, `slurm_qos`, `slurm_burst_*`
   - `slurm_mail_user` (or leave `""`)
3. `bash RUN-workflow.sh`

## Honesty Principle

Per `../../../../AI_GUIDE-project.md`: when something didn't work, say "I
was incorrect" or "I was wrong" — not "that was confusing." This workflow
is the result of two failed earlier attempts (`BLOCK_orthohmm` RUN_4 hit a
hardcoded 48 h NextFlow process timeout at 5.7 % CPU efficiency; first
submit of this BLOCK failed because manifest headers used the GIGANTIC
self-documenting style which broke NextFlow's splitCsv). Both failures
informed the architecture and are documented in feedback memories. Future
sessions should refer to those rather than rediscovering the same traps.
