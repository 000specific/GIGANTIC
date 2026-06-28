<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 28
Human:   Eric Edsinger
Purpose: Workflow execution AI guide for species_X_all_annotations.
Scope:   workflow-COPYME-species_X_all_annotations (execution detail).
============================================================================ -->

# AI Guide: species_X_all_annotations Workflow

**For AI Assistants**: Read the BLOCK guide (`../../AI_GUIDE.md`) and the
subproject guide (`../../../AI_GUIDE.md`) first. This file focuses on running
the workflow.

## Where this fits

- Parent BLOCK guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md)
- Parent (subproject AI guide): [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- Parent (project): [`../../../../AI_GUIDE.md`](../../../../AI_GUIDE.md)
- Workflow README: [`../README.md`](../README.md)
- Outputs to: `../../../output_to_input/BLOCK_species_X_all_annotations/<run_label>/`

## Quick Reference

| User needs... | Go to... |
|---|---|
| GIGANTIC overview | `../../../../AI_GUIDE.md` |
| integrator concepts + join model | `../../../AI_GUIDE.md` |
| BLOCK concepts + join keys + output schema | `../../AI_GUIDE.md` |
| Running the workflow | This file |

## Pipeline (5 NextFlow processes)

| # | Script | Process | Function |
|---|--------|---------|----------|
| 000 | `resolve_structures.py` | `resolve_structures` | Resolve `structures` (`all` \| list) → `structures.txt`; fail-fast verify BOTH OCL summaries exist for each |
| 001 | `build_invariant_base.py` | `build_invariant_base` | Phase 1 (once) — join every structure-invariant per-gene feature onto the proteome spine → `1-output/_shared/<phyloname>-proteome_annotations-base.tsv` + availability summary |
| 002 | `build_per_structure_tables.py` | `build_per_structure_tables` | Phase 2 (one task per structure) — append the structure's orthogroup + pfam-annogroup OCL columns → `2-output/<structure>/<phyloname>-proteome_all_annotations.tsv` |
| 003 | `validate_results.py` | `validate_results` | Base + per-structure cross-checks; fail-fast (§36) → `3-output/` |
| 004 | `write_run_log.py` | `write_run_log` | Run log → `ai/logs/` (§45) |
| — | `utils_species_X_all_annotations.py` | — | Shared helpers (config, GIGANTIC-ID parsing, header indexing, nr-hit formatting, `DELIM`/`SUBDELIM`/`NA`) |

Wiring (`main.nf`): `resolve_structures` emits `structures.txt`, split into a
channel; `build_invariant_base` runs once; `build_per_structure_tables` fans out
over the structure channel (each task also gates on `build_invariant_base`
readiness). A `.collect()` barrier runs `validate_results` after every
per-structure table is written, then `write_run_log`.

## structures (all | list)

`START_HERE-user_config.yaml`:
```yaml
structures:
  - "structure_001"
  - "structure_003"
  - "structure_032"
  - "structure_033"
# or:  structures: "all"
```
`all` materializes every structure produced by the orthogroups OCL run
(currently 105 → 105 × 70 full wide tables — large; use `parallelism_mode: slurm`).
A list materializes only those structures. Script 000 fail-fasts if a requested
structure lacks either OCL summary.

## execution_mode and parallelism_mode

- `execution_mode`: where the driver runs — `local` or `slurm` (self-submits via
  `sbatch --wrap`).
- `parallelism_mode`: how processes dispatch — `local` (default; tasks share the
  allocation; good for a few structures) or `slurm` (one SLURM job per task; good
  for `all`).

Phase 1 is memory-bound (loads the orthogroups table + pfam/go/panther annogroup
membership + AGS membership globally). `memory_gb` in the config must be ≥ the
`build_invariant_base` process memory in `ai/nextflow.config` (48 GB); the default
`memory_gb: 64` satisfies this.

## NextFlow Strict-DSL Posture

`main.nf` avoids top-level `def` / `import` / `workflow.onComplete`. Parameters
come from `-params-file START_HERE-user_config.yaml`; SLURM account/qos + cpus /
memory_gb flow through to `ai/nextflow.config` as `params.*`. Conda env pins
`nextflow>=23.0,<26.0`.

## Common failure modes

| Error | Cause | Solution |
|-------|-------|----------|
| `orthogroups OCL run directory not found` (000) | `orthogroups_ocl_run_label` / `inputs.orthogroups_ocl_dir` wrong | `ls ../../../ocl_phylogenetic_structures/output_to_input/BLOCK_orthogroups_X_ocl/` |
| `required OCL input(s) missing` (000) | a requested structure has no OCL summary | drop it from `structures`, or run that structure's OCL |
| `no spine sequence tables found` (001) | `inputs.spine_dir` wrong | verify `genomesDB/output_to_input/STEP_4-create_final_species_set/species70_gigantic_T1_sequence_tables/*-T1-proteome-sequence_table.tsv` |
| `annogroup membership not found for source` (001) | a `annogroup_sources` entry not built | remove the source, or run the annogroups subproject for it |
| `orthogroup ... has no row in the orthogroup OCL summary` (002) | orthogroups membership and OCL run out of sync | confirm `orthogroups_file` and `orthogroups_ocl_run_label` are the same OrthoHMM run |
| validation FAIL (003) | header / uniqueness / species-containment / availability-leak / row-count / OCL-referential mismatch | read `3-output/3_ai-validation_report.txt` |

## Diagnostic commands

```bash
# How many proteins per species + availability coverage
column -t -s$'\t' OUTPUT_pipeline/1-output/_shared/feature_availability_summary.tsv | less -S

# Wide table row count for a structure (should equal base row count)
wc -l OUTPUT_pipeline/2-output/structure_001/*-proteome_all_annotations.tsv | tail -1

# Validation verdict
grep -A2 Status OUTPUT_pipeline/3-output/3_ai-validation_report.txt

# Downstream symlinks created (directory symlinks: _shared + one per structure)
ls -la ../../../output_to_input/BLOCK_species_X_all_annotations/*/
```

## NextFlow cache reset

```bash
rm -rf work .nextflow .nextflow.log* slurm_logs
bash RUN-workflow.sh   # fresh, no -resume
```

## See also

- [`../README.md`](../README.md) — runbook + I/O
- [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — join keys + output schema
- [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md) — integrator join model
