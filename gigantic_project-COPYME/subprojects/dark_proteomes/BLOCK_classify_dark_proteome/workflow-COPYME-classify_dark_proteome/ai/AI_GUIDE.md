# AI Guide: classify_dark_proteome Workflow

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 04 (workflow scripts)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (initial docs)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — BLOCK_classify_dark_proteome concepts
- Parent (subproject AI guide): [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md) — dark_proteomes overview
- Parent (project): [`../../../../AI_GUIDE.md`](../../../../AI_GUIDE.md)
- Workflow README: [`../README.md`](../README.md)
- Reads from (per axis):
  - axis_a: `../../../../one_direction_homologs/output_to_input/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits/`
  - axis_b: `../../../../orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC/orthogroups_gigantic_ids.tsv`
  - axis_c: `../../../../annotations_hmms/output_to_input/BLOCK_interproscan_parsed/`
  - species: `../../../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs to: `../../../output_to_input/BLOCK_classify_dark_proteome/`
- 5 scripts (validate / build_ref_OG / classify_per_species / summarize / write_run_log per §45)
- Conda env: `aiG-dark_proteomes`

---

## Pipeline (5 NextFlow processes)

| # | Script | Process | Function |
|---|--------|---------|----------|
| 001 | `validate_inputs.py` | `validate_inputs` | Pair each species with its 4 inputs; fail-fast on missing data |
| 002 | `build_reference_orthogroup_set.py` | `build_reference_orthogroup_set` | One-time pre-process: set of OGs containing reference species |
| 003 | `classify_per_species.py` | `classify_per_species` | Per-species fan-out: 3-axis check per gene → DARK/ANNOTATED |
| 004 | `summarize_dark_proteome.py` | `summarize_dark_proteome` | Cross-species aggregate table |
| 005 | `write_run_log.py` | `write_run_log` | Timestamped run log per §45 |

## NextFlow Strict-DSL Posture

`main.nf` is written for strict NextFlow 26 DSL: no top-level `def`,
`import`, or `workflow.onComplete`. Parameters come from
`-params-file <yaml>`; executor decisions (local vs slurm) come from
env vars set by `RUN-workflow.sh` (per the `execution_mode` YAML key).

## execution_mode

Set in `START_HERE-user_config.yaml`:
- `local` — sequential NextFlow runs on the head node
- `slurm` — `RUN-workflow.sh` self-submits the NextFlow driver as one sbatch
- `slurm_burst` — same, but the chunked process(es) fan out to burst QOS

`RUN-workflow.sh` reads `execution_mode` from the YAML and applies the
right dispatch — no `RUN-workflow.sbatch` needed (deprecated per §29).

## Common Failure Modes

| Error | Cause | Solution |
|-------|-------|----------|
| validate_inputs fails: "missing axis_a for species X" | one_direction_homologs run produced no hits dir for that species | Check `one_direction_homologs/output_to_input/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits/` for species X |
| validate_inputs fails: "missing axis_b" | orthogroups OG table has no rows for species X | Check the OG table includes the same species set as genomesDB STEP_4 |
| validate_inputs fails: "missing axis_c" | annotations_hmms not run, or parsed dir empty | Run `BLOCK_interproscan` + `BLOCK_build_annotation_database` first |
| classify produces 0 dark genes | Inputs paired but classification logic produced no DARK → check that reference species are actually in the OG table | Verify reference species appear in `orthogroups_file` |
| summarize tail: weird %s | Some species missing from one or more axes | Cross-check species set consistency upstream |

## Diagnostic Commands

```bash
# How many genes per species got classified?
wc -l OUTPUT_pipeline/3-output/3_ai-dark_classification-*.tsv

# Cross-species summary
cat OUTPUT_pipeline/4-output/4_ai-dark_proteome_summary.tsv

# Per-species dark count + percent
awk -F'\t' 'NR>1 {print $1, $5, $6}' OUTPUT_pipeline/4-output/4_ai-dark_proteome_summary.tsv
```

## See Also

- [`../README.md`](../README.md) — workflow usage
- [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — BLOCK concepts
- [`../../../README.md`](../../../README.md) — subproject methodology + Edsinger 2024 reference
