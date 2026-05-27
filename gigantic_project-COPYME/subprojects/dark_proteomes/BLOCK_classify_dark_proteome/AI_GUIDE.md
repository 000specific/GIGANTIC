# AI Guide: BLOCK_classify_dark_proteome

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 04 (workflow scripts)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (initial docs)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (subproject): [`../AI_GUIDE.md`](../AI_GUIDE.md) — dark_proteomes overview + 3-axis methodology
- Parent (subproject README): [`../README.md`](../README.md)
- Workflow template: [`workflow-COPYME-classify_dark_proteome/`](workflow-COPYME-classify_dark_proteome/)
- This BLOCK's workflow guide: [`workflow-COPYME-classify_dark_proteome/ai/AI_GUIDE.md`](workflow-COPYME-classify_dark_proteome/ai/AI_GUIDE.md)
- Reads FROM (per axis):
  - axis_a: `../../one_direction_homologs/output_to_input/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits/`
  - axis_b: `../../orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC/orthogroups_gigantic_ids.tsv`
  - axis_c: `../../annotations_hmms/output_to_input/BLOCK_interproscan_parsed/`
  - species set: `../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs TO: `../output_to_input/BLOCK_classify_dark_proteome/`
- 5 scripts (validate → build_reference_OG_set → classify_per_species → summarize → write_run_log per §45)
- Conda env: `aiG-dark_proteomes`

---

## Purpose

The single BLOCK in the dark_proteomes subproject. Runs the three-axis
DARK/ANNOTATED classification per gene per species and emits both
per-species results and a cross-species summary.

## Pipeline (5 NextFlow processes)

| # | Script | Function |
|---|--------|----------|
| 001 | `validate_inputs.py` | Pair each species with its 4 inputs; fail-fast on missing data |
| 002 | `build_reference_orthogroup_set.py` | One-time pre-process: set of OGs containing reference species |
| 003 | `classify_per_species.py` | Per-species fan-out: 3-axis check per gene → DARK/ANNOTATED |
| 004 | `summarize_dark_proteome.py` | Cross-species aggregate table |
| 005 | `write_run_log.py` | Timestamped run log (§45) |

## Why "BLOCK" (not "STEP")

Per §41: dark_proteomes is a single independently-runnable unit — it has
its own external upstream dependencies (3 other subprojects) but no
internal sequencing constraint. BLOCK is the right pattern.

## Conda Env Convention Note

Current env name is `aiG-dark_proteomes`. Strict §28 form would be
`aiG-dark_proteomes-classify_dark_proteome`. Functional impact is zero
(single-BLOCK subproject); flagged as minor naming drift for future
review.

## See Also

- [`../AI_GUIDE.md`](../AI_GUIDE.md) — subproject AI guide
- [`workflow-COPYME-classify_dark_proteome/ai/AI_GUIDE.md`](workflow-COPYME-classify_dark_proteome/ai/AI_GUIDE.md) — workflow execution guide
