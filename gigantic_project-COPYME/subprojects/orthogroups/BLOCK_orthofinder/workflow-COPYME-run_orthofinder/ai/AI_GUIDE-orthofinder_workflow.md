# AI_GUIDE-orthofinder_workflow.md (Level 3: Workflow Execution Guide)

**For AI Assistants**: Read `../../AI_GUIDE-orthofinder.md` first for OrthoFinder concepts. This guide focuses on running the workflow.

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
