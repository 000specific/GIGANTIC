<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 04
Human:   Eric Edsinger
Purpose: Workflow execution AI guide for orthogroups_ocl_X_features.
Scope:   workflow-COPYME-orthogroups_ocl_X_features (execution detail).
============================================================================ -->

# AI Guide: orthogroups_ocl_X_features Workflow

**For AI Assistants**: Read the BLOCK guide (`../../AI_GUIDE.md`) and the
subproject guide (`../../../AI_GUIDE.md`) first. This file focuses on running
the workflow.

## Where this fits

- Parent BLOCK guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md)
- Parent (subproject AI guide): [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- Parent (project): [`../../../../AI_GUIDE.md`](../../../../AI_GUIDE.md)
- Workflow README: [`../README.md`](../README.md)
- Outputs to: `../../../output_to_input/BLOCK_orthogroups_ocl_X_features/<run_label>/`

## Quick Reference

| User needs... | Go to... |
|---|---|
| GIGANTIC overview | `../../../../AI_GUIDE.md` |
| integrator concepts + join model | `../../../AI_GUIDE.md` |
| BLOCK concepts + output schema | `../../AI_GUIDE.md` |
| Running the workflow | This file |

## Pipeline (6 NextFlow processes)

| # | Script | Process | Function |
|---|--------|---------|----------|
| 001 | `build_feature_lookup.py` | `build_feature_lookup` | Singleton: build structure-invariant gene→feature lookup → `OUTPUT_pipeline/_shared/1-output/`; fail-fast if no source has data |
| 002 | `build_integrated_summary.py` | `build_integrated_summary` | Per structure: Table 1 (`2-output/`) |
| 003 | `build_block_state_expanded.py` | `build_block_state_expanded` | Per structure: Table 2 (`3-output/`) — needs OCL path_states |
| 004 | `build_gene_drilldown.py` | `build_gene_drilldown` | Per structure: Table 3 (`4-output/`) |
| 005 | `validate_results.py` | `validate_results` | Per structure: cross-checks (fail-fast, §36) → `5-output/` |
| 006 | `write_run_log.py` | `write_run_log` | Run log → `ai/logs/` (§45) |

Wiring (`main.nf`): `build_feature_lookup` runs once; its readiness is a value
channel (`.first()`) broadcast to every per-structure task. Per structure:
002 → 003 → 004, then a `collect().flatten()` barrier before 005, then 006.

## NextFlow Strict-DSL Posture

`main.nf` avoids top-level `def` / `import` / `workflow.onComplete`. Parameters
come from `-params-file START_HERE-user_config.yaml` (universal GIGANTIC
YAML→params pattern); SLURM account/qos + cpus/memory_gb flow through to
`nextflow.config` as `params.*`. Conda env pins `nextflow>=23.0,<26.0`.

## execution_mode and parallelism_mode

`START_HERE-user_config.yaml`:
- `execution_mode`: where the driver runs — `local` (here) or `slurm`
  (self-submits via `sbatch --wrap`).
- `parallelism_mode`: how per-structure tasks dispatch — `local` (parallel
  within the allocation; default, integration is seconds/task) or `slurm`
  (one SLURM job per task). They compose.

Recommended for a 105-structure species70 run: `execution_mode: slurm`,
`parallelism_mode: local` — one SLURM allocation, local parallelism inside.

## Common failure modes

| Error | Cause | Solution |
|-------|-------|----------|
| `no feature data found in ANY source` (001) | All input dirs missing/empty | Verify the four feature paths in the YAML resolve to populated `output_to_input/` dirs |
| `OCL summary not found for structure_NNN` (002) | run_label/structure not exposed | `ls ../../../ocl_phylogenetic_structures/output_to_input/BLOCK_orthogroups_X_ocl/<run_label>/structure_NNN/` |
| `OCL path_states not found` (003) | OCL didn't expose path_states | Re-run OCL `RUN-workflow.sh` (now exposes it) or recreate the symlink |
| `path/state length mismatch` or `inconsistent state` (003) | Malformed/inconsistent OCL path_states | Genuine upstream data problem — inspect the OCL path_states file; do not work around silently |
| validation FAIL (005) | Count/id-list/availability mismatch | Read `5-output/5_ai-structure_NNN-validation_report.txt`; investigate the offending table |
| Out-of-memory in per-structure task | Large gene lookup | Increase `memory_gb` in the YAML (drives SLURM + local-executor memory) |

## Diagnostic commands

```bash
# Lookup + availability
wc -l OUTPUT_pipeline/_shared/1-output/1_ai-gene_feature_lookup.tsv
column -t -s$'\t' OUTPUT_pipeline/_shared/1-output/1_ai-feature_availability_summary.tsv | head

# Per-structure table row counts
wc -l OUTPUT_pipeline/structure_001/2-output/*.tsv \
      OUTPUT_pipeline/structure_001/3-output/*.tsv \
      OUTPUT_pipeline/structure_001/4-output/*.tsv

# Validation verdict
grep -H Status OUTPUT_pipeline/structure_*/5-output/*validation_report.txt

# Downstream symlinks created
ls -la ../../../output_to_input/BLOCK_orthogroups_ocl_X_features/*/structure_001/
```

## NextFlow cache reset

```bash
rm -rf work .nextflow .nextflow.log* slurm_logs
bash RUN-workflow.sh   # fresh, no -resume
```

## See also

- [`../README.md`](../README.md) — runbook + I/O
- [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — output table schema + design decisions
- [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md) — join model + OCL path_states exposure note
