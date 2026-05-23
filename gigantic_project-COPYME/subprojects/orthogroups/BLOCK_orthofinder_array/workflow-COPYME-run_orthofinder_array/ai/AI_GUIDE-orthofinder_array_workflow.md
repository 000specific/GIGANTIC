# AI_GUIDE-orthofinder_array_workflow.md (Level 3: Workflow Execution Guide)

**For AI Assistants**: Read `../../AI_GUIDE-orthofinder_array.md` first for the BLOCK-level architecture overview. This guide focuses on running, debugging, and modifying the workflow.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../AI_GUIDE-project.md` |
| Orthogroups subproject overview | `../../../AI_GUIDE-orthogroups.md` |
| BLOCK_orthofinder_array architecture | `../../AI_GUIDE-orthofinder_array.md` |
| **Running this workflow** | This file |

## Pipeline (10 NextFlow Processes)

| # | Process | Label | What it does | Inputs | Outputs |
|---|---|---|---|---|---|
| 1 | `validate_proteomes` | `local_step` | Validates proteomes; emits proteome_list.tsv | proteomes_dir | 1_ai-proteome_list.tsv |
| 2 | `prepare_proteomes` | `local_step` | Stages proteomes for OrthoFinder input format | proteome_list | orthofinder_input_proteomes/*, 2_ai-prepared_proteomes_summary.tsv |
| 3 | `extract_orthofinder_search_commands` | `local_step` | Runs `orthofinder -op` to extract DIAMOND command set + prepared workdir | prepared_proteomes | 3_ai-search_pair_manifest.tsv (simple headers!), orthofinder_workdir/ |
| 4 | `run_diamond_pair` | **`diamond_pair`** (SLURM array, burst QOS) | Runs one DIAMOND pair per task; ~4,830 tasks | (taxa_a, taxa_b, output_filename, search_command, workdir) | Blast{A}_{B}.txt |
| 5 | `pool_and_verify_diamond_outputs` | `local_step` | Silent-artifact gate; verifies every pair is PRESENT (non-empty) | all DIAMOND outputs + manifest + workdir | orthofinder_workdir_with_results/*, 5_ai-pool_verification_report.tsv |
| 6 | `run_orthofinder_from_blast` | `orthofinder_finalize` | Runs `orthofinder -b <pooled_workdir>` (clustering + trees + reconciliation) | pooled_workdir | orthofinder_output/Results_*/ |
| 7 | `standardize_output` | `local_step` | Converts OrthoFinder species×OG matrix → GIGANTIC long-form orthogroup TSV | OrthoFinder output + proteome_list | 7_ai-orthogroups_gigantic_ids.tsv, 7_ai-gene_count_gigantic_ids.tsv |
| 8 | `generate_summary_statistics` | `local_step` | Orthogroup-level metrics | proteome_list + orthogroups_gigantic | 8_ai-summary_statistics.tsv |
| 9 | `qc_analysis_per_species` | `local_step` | Per-species QC | proteome_list + orthogroups_gigantic | 9_ai-per_species_summary.tsv |
| 10 | `write_run_log` | `local_step` | Timestamped run log | per-species summary | ai/logs/run_log_*.tsv |

## Running the Workflow

```bash
cd workflow-RUN_N-run_orthofinder_array/
bash RUN-workflow.sh
```

`RUN-workflow.sh` reads `execution_mode` from the yaml. With `slurm`, it
self-submits via `sbatch --wrap` as a long-running driver job. The driver
runs NextFlow which, when it reaches process 4, fans out via the SLURM
executor with `process.array = 100` (~49 array submissions to burst QOS).

## NextFlow Configuration Highlights

`ai/nextflow.config`:
- Loads `START_HERE-user_config.yaml` at the top via SnakeYAML.
- Per-label resources (`diamond_pair`, `orthofinder_finalize`, `local_step`) come from yaml.
- `diamond_pair` label uses `executor = 'slurm'` + `clusterOptions = "--account=${slurmBurstAccount} --qos=${slurmBurstQos}"` + `array = 100`.
- `errorStrategy = 'retry'` with `maxRetries = 2` for `diamond_pair` (transient SLURM/network glitches across thousands of tasks).
- timeline / report / trace blocks all use `overwrite = true` (avoids the FileAlreadyExistsException seen in earlier orthohmm runs).

## How `-op` and `-b` Work Together

OrthoFinder publishes two flags designed for HPC fan-out workflows:

- **`orthofinder -op`** — prepares the WorkingDirectory (renames proteomes
  to `Species{N}.fa`, builds DIAMOND databases via `makeblastdb`/`diamond
  makedb`, etc.), then prints every pairwise search command to stdout and
  exits before running searches. Per OrthoFinder docs: *"useful if you
  want to manage the BLAST searches yourself, e.g., distribute across
  multiple machines."*

- **`orthofinder -b <dir>`** — resumes from pre-computed search results
  inside `<dir>`. Skips Step 1; runs orthogroup clustering + tree inference
  + reconciliation.

Script 003 captures the printed commands AND the WorkingDirectory. The
fan-out runs each captured command verbatim. Script 005 pools all `Blast{A}_{B}.txt` outputs back into the WorkingDirectory. Script 006 calls `-b`.

## Common Execution Errors

| Error | Cause | Fix |
|---|---|---|
| `input file name collision -- multiple input files for: null` | Manifest TSV header uses self-documenting style — NextFlow's splitCsv returns null keys | Already fixed in script 003 (simple bare headers). See feedback memory. |
| `OrthoFinder did not produce a Results_<date> directory` | OrthoFinder failed silently | Check 6_ai-log-run_orthofinder_from_blast.log; inspect input pooled_workdir for completeness |
| Pool verification: many MISSING | Burst tasks failed | Inspect slurm_logs/ from array tasks |
| Pool verification: many EMPTY | Distantly-related species pairs (no detectable similarity) | Biologically valid — review report and proceed if comfortable |
| OrthoFinder hangs in tree inference | Large orthogroup set, high `-t` overhead | Increase finalize cpus to allow more parallel trees |

## Resume vs Fresh

`resume: true` in yaml → NextFlow `-resume`.

**Default is `false`** (fail-fast for research integrity per CLAUDE.md). To
restart fresh: `rm -rf work .nextflow .nextflow.log* OUTPUT_pipeline` then
`bash RUN-workflow.sh`.

## Diagnostic Commands

```bash
# Driver job status
squeue -j <DRIVER_JOB_ID> -o "%.10i %.30j %.2t %.10M %R"

# Inspect a specific NextFlow task
ls -la work/<HASH>/
cat work/<HASH>/.command.sh
cat work/<HASH>/.command.log
cat work/<HASH>/.command.err

# Per-pair verification status
column -ts $'\t' OUTPUT_pipeline/5-output/5_ai-pool_verification_report.tsv | less

# How many DIAMOND pairs done (during run)
ls work/*/Blast*.txt 2>/dev/null | wc -l
```

## Modifying for a New Project

1. `cp -a workflow-COPYME-run_orthofinder_array workflow-RUN_N-run_orthofinder_array`
2. Edit `START_HERE-user_config.yaml`:
   - `project.name`
   - `inputs.proteomes_dir`
   - `slurm_account`, `slurm_qos`, `slurm_burst_*`
   - `slurm_mail_user` (or leave `""`)
3. `bash RUN-workflow.sh`

## Honesty Principle

Per `../../../../AI_GUIDE-project.md`: when something didn't work, say "I
was incorrect" or "I was wrong" — not "that was confusing." This workflow
is the result of architectural lessons learned in `BLOCK_orthohmm_GIGANTIC`
— the same fan-out pattern, the same NextFlow `splitCsv` trap (now
addressed), the same etiquette considerations for HiPerGator burst QOS.
Future sessions should refer to those lessons rather than rediscovering
them.
