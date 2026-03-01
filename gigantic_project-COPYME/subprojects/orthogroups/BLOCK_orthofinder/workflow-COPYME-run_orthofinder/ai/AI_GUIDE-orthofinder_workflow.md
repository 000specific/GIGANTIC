# AI_GUIDE-orthofinder_workflow.md (Level 3: Workflow Execution Guide)

**For AI Assistants**: Read `../../AI_GUIDE-orthofinder.md` first for OrthoFinder concepts. This guide focuses on running the workflow.

## Quick Start

```bash
# 1. Activate environment
module load conda
conda activate ai_gigantic_orthogroups
module load nextflow

# 2. Edit configuration
vi ../orthofinder_config.yaml

# 3. Run pipeline
bash ../RUN-workflow.sh

# Or submit to SLURM
sbatch ../RUN-workflow.sbatch
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

# Check output_to_input was populated
ls ../../output_to_input/
```

## Common Errors

| Error | Solution |
|-------|----------|
| OrthoFinder not found | `conda activate ai_gigantic_orthogroups` |
| No .aa files | Check proteomes_dir path in config |
| Results_* dir not found | OrthoFinder failed; check 3-output log |
| Stale Nextflow cache | `rm -rf work .nextflow .nextflow.log*` |
