# AI_GUIDE — orthogroups workflow runbook (BLOCK_orthohmm)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 to 4.7 | 2026 Feb-May (multiple passes)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK AI guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md)
- Parent subproject AI guide: [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- User-facing workflow README: [`../README.md`](../README.md)
- Reads from: `../../../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs to: `../../../output_to_input/BLOCK_orthohmm/`

---

**For AI Assistants**: Read `../../AI_GUIDE.md` first for OrthoHMM concepts. This guide focuses on running the workflow.

## Quick Start

```bash
module load conda
conda activate aiG-orthogroups-orthohmm
module load nextflow

vi ../START_HERE-user_config.yaml

bash ../RUN-workflow.sh
# (Set execution_mode: "slurm" in START_HERE-user_config.yaml first to self-submit to SLURM.)
```

## Pipeline Steps

1. **validate_proteomes** - Checks proteome directory, creates `1_ai-proteome_list.tsv`
2. **convert_headers** - Converts GIGANTIC headers to `Genus_species-N` format
3. **run_orthohmm** - Executes OrthoHMM (HMMER + MCL)
4. **restore_identifiers** - Restores full GIGANTIC identifiers from mapping
5. **generate_summary_statistics** - Computes orthogroup size stats, coverage
6. **qc_analysis_per_species** - Per-species assignment rates and coverage

## Verification Commands

```bash
ls OUTPUT_pipeline/*/
wc -l OUTPUT_pipeline/4-output/4_ai-orthogroups_gigantic_ids.tsv
ls ../../output_to_input/BLOCK_orthohmm/
```

## Common Errors

| Error | Solution |
|-------|----------|
| orthohmm not found | `conda activate aiG-orthogroups-orthohmm` |
| Header mapping empty | Rerun script 002 |
| orthohmm_orthogroups.txt missing | Check 3-output log for OrthoHMM errors |
| Stale cache | `rm -rf work .nextflow .nextflow.log*` |
