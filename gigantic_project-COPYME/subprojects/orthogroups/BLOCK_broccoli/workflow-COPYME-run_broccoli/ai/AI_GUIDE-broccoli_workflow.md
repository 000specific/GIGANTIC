# AI_GUIDE-broccoli_workflow.md (Level 3: Workflow Execution Guide)

**For AI Assistants**: Read `../../AI_GUIDE-broccoli.md` first for Broccoli concepts (4-step internal pipeline, output filenames, why no `_array` variant). This guide focuses on running the workflow.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../AI_GUIDE-project.md` |
| Orthogroups subproject overview | `../../../AI_GUIDE-orthogroups.md` |
| Broccoli concepts, CLI, output formats | `../../AI_GUIDE-broccoli.md` |
| Running the workflow (this file) | This file |

## Quick Start

```bash
# 1. Edit the user-facing config (the only file you should ever edit here)
vi START_HERE-user_config.yaml

# 2. Run — RUN-workflow.sh handles conda env creation, sbatch self-submission,
#    and NextFlow invocation based on execution_mode in the yaml
bash RUN-workflow.sh
```

`RUN-workflow.sh` is the single entry point. It:
1. Creates the `ai_gigantic_orthogroups_broccoli` conda env on-demand if absent (from `../../../../conda_environments/ai_gigantic_orthogroups_broccoli.yml`)
2. Reads `execution_mode` from the yaml
3. If `slurm`: re-invokes itself as a SLURM driver job (with the resources from the yaml)
4. If `local`: runs NextFlow directly on the calling node
5. After NextFlow completes, creates symlinks in `../../output_to_input/BLOCK_broccoli/`

## Pipeline Steps

| # | Process | What it does | Output |
|---|---|---|---|
| 1 | validate_proteomes | List input proteomes, count sequences, extract Genus_species from phyloname | `1-output/1_ai-proteome_list.tsv` |
| 2 | convert_headers | Rewrite FASTA headers as `{genus_species}-N` short IDs; record mapping | `2-output/short_header_proteomes/*.aa`, `2-output/2_ai-header_mapping.tsv` |
| 3 | run_broccoli | Run broccoli's 4-step internal pipeline (k-mer → DIAMOND+FastTree → network → pairwise) | `3-output/3_ai-{broccoli's 9 output files}` |
| 4 | restore_identifiers | Translate broccoli short_ids back to full GIGANTIC headers (orthologous_groups only — counts/names matrices have no protein IDs) | `4-output/4_ai-orthologous_groups-gigantic_ids.tsv` |
| 5 | generate_summary_statistics | Total orthogroups, coverage %, size distribution | `5-output/5_ai-summary_statistics.tsv`, `5_ai-orthogroup_size_distribution.tsv` |
| 6 | qc_analysis_per_species | Per-species coverage and orthogroup membership | `6-output/6_ai-per_species_summary.tsv` |
| 7 | write_run_log | Timestamped run log | `ai/logs/run_*.log` |

## Output Layout

Files in `OUTPUT_pipeline/3-output/` are broccoli's actual outputs renamed with the GIGANTIC `3_ai-` prefix only — the broccoli stem is preserved so files trace cleanly back to `broccoli_step3.py` / `broccoli_step4.py` documentation:

```
3_ai-orthologous_groups.txt              ← broccoli's main output (uses short_ids)
3_ai-table_OGs_protein_counts.txt        ← OG × species count matrix
3_ai-table_OGs_protein_names.txt         ← OG × species name matrix
3_ai-chimeric_proteins.txt               ← gene-fusion candidates
3_ai-unclassified_proteins.txt           ← proteins not in any OG
3_ai-statistics_per_OG.txt               ← per-OG metrics
3_ai-statistics_per_species.txt          ← per-species summary
3_ai-statistics_nb_OGs_VS_nb_species.txt ← distribution
3_ai-orthologous_pairs.txt               ← pairwise ortholog relationships (from dir_step4)
3_ai-log-run_broccoli.log                ← run_broccoli log
```

The only file translated to GIGANTIC IDs is in `4-output/`:
```
4_ai-orthologous_groups-gigantic_ids.tsv  ← broccoli orthogroups with full GIGANTIC headers
```

The count and name matrices in 3-output/ already reference species names (not protein IDs), so no translation is needed for those.

## Verification

```bash
# Did broccoli produce its 9 expected files?
ls OUTPUT_pipeline/3-output/

# How many orthogroups?
wc -l OUTPUT_pipeline/3-output/3_ai-orthologous_groups.txt
wc -l OUTPUT_pipeline/4-output/4_ai-orthologous_groups-gigantic_ids.tsv  # should match

# Per-species coverage
head OUTPUT_pipeline/6-output/6_ai-per_species_summary.tsv

# Symlinks for downstream subprojects
ls -l ../../output_to_input/BLOCK_broccoli/
```

## Resource Configuration

Broccoli is **monolithic** — no SLURM array fan-out (see `../../AI_GUIDE-broccoli.md` for the architectural reasoning). The `run_broccoli` process gets one big SLURM allocation. COPYME defaults sized for species70:

| resource | value | notes |
|---|---|---|
| cpus | 110 | broccoli's `-threads N` parallelizes step 2 internally |
| memory_gb | 700 | well under HiPerGator's 110 × 7.5 = 825 GB max |
| time_hours | 504 | 3 weeks — broccoli step 2 (DIAMOND + per-protein FastTree) is slow on 70 species; revisit after first species70 run by checking MaxRSS / Elapsed |

Driver `slurm_time_hours` is 552 (23 days) — must outlast `run_broccoli` with buffer.

For smaller datasets (e.g., 5-species test subset), edit the yaml downward.

## Common Errors

| Error message | Cause | Solution |
|---|---|---|
| `Environment 'ai_gigantic_orthogroups_broccoli' not found` | First run, env not yet created | RUN-workflow.sh creates it on-demand from yml — re-run |
| `dir_step3/ not found — broccoli step 3 did not run` | Broccoli failed before step 3 completed | Check `3_ai-log-run_broccoli.log` for the actual broccoli error |
| `required broccoli output missing: dir_step3/<file>` | Broccoli step 3 ran but didn't produce one of its 9 outputs (per source, all are always produced — this means a real broccoli failure) | Check broccoli log; do not proceed |
| `short_ids in broccoli output not found in header mapping` | Mismatch between FASTAs broccoli read and FASTAs script 002 wrote | Investigate scripts 002 and 003 — by construction this should be impossible |
| `total_sequences is zero` | Script 001 produced empty proteome list | Check `proteomes_dir` path in yaml |
| `no orthogroups in input` | Broccoli (or script 004) produced nothing usable | Check `4_ai-orthologous_groups-gigantic_ids.tsv` and broccoli log |
| Stale NextFlow cache after script edits | `work/`, `.nextflow/` from previous run | `rm -rf work .nextflow .nextflow.log*` then re-run (no `-resume`) |

## Fail-Fast Principle

Per CLAUDE.md "Zero Tolerance for Silent Artifacts," all scripts in this workflow fail-fast:
- No `optional: true` on NextFlow process outputs
- No placeholder/empty file fallbacks for missing critical data
- No silent passthrough of unmatched short_ids in `restore_identifiers`
- Every error path is `sys.exit(1)` with a detailed message

This is intentional and non-negotiable: broccoli runs for hours-to-weeks, and silent failures here become silent artifacts in published research. If something fails fast and loud, you fix it. If something fails silent, you don't know to fix it.

## Honesty Principle (for AI Assistants)

If you make a mistake while assisting with this workflow, acknowledge it directly. "I was wrong" or "I was incorrect" — not "that was confusing." This builds trust with users who rely on accurate information about their pipeline state.
