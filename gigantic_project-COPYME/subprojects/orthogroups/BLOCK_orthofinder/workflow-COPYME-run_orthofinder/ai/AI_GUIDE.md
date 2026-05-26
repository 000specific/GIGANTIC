# AI_GUIDE — orthogroups workflow runbook (BLOCK_orthofinder)

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
- Outputs to: `../../../output_to_input/BLOCK_orthofinder/`

---

**For AI Assistants**: Read `../../AI_GUIDE.md` first for OrthoFinder concepts. This guide focuses on running the workflow.

## Quick Start

```bash
# 1. Edit configuration
vi START_HERE-user_config.yaml

# 2. Run pipeline (auto-creates aiG-orthogroups-orthofinder env on first run)
bash RUN-workflow.sh

# Or submit to SLURM: set execution_mode: "slurm" in START_HERE-user_config.yaml,
# then run the same bash command — RUN-workflow.sh self-submits.
```

## Pipeline Steps

1. **validate_proteomes** - Checks proteome directory, creates `1_ai-proteome_list.tsv`
2. **prepare_proteomes** - Copies proteomes to OrthoFinder input directory
3. **run_orthofinder** - Executes OrthoFinder with Diamond and -X flag
4. **standardize_output** - Converts OrthoFinder matrix to GIGANTIC tab-separated format
5. **generate_summary_statistics** - Computes orthogroup size stats, coverage
6. **qc_analysis_per_species** - Per-species assignment rates and coverage

## Verification Commands

```bash
# Check pipeline output
ls OUTPUT_pipeline/*/

# Verify orthogroups were created
wc -l OUTPUT_pipeline/4-output/4_ai-orthogroups_gigantic_ids.tsv

# Check output_to_input/BLOCK_orthofinder/ was populated
ls ../../output_to_input/BLOCK_orthofinder/
```

## Common Errors

| Error | Solution |
|-------|----------|
| OrthoFinder not found | env auto-creates via `RUN-workflow.sh`; or `conda activate aiG-orthogroups-orthofinder` |
| No .aa files | Check proteomes_dir path in config |
| Results_* dir not found | OrthoFinder failed; check 3-output log |
| Stale Nextflow cache | `rm -rf work .nextflow .nextflow.log*` |
