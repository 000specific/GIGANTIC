# AI_GUIDE-orthohmm_workflow.md (Level 3: Workflow Execution Guide)

**For AI Assistants**: Read `../../AI_GUIDE-orthohmm.md` first for OrthoHMM concepts. This guide focuses on running the workflow.

## Quick Start

```bash
module load conda
conda activate ai_gigantic_orthogroups
module load nextflow

vi ../orthohmm_config.yaml

bash ../RUN-workflow.sh
# Or: sbatch ../RUN-workflow.sbatch
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
ls ../../output_to_input/
```

## Common Errors

| Error | Solution |
|-------|----------|
| orthohmm not found | `conda activate ai_gigantic_orthogroups` |
| Header mapping empty | Rerun script 002 |
| orthohmm_orthogroups.txt missing | Check 3-output log for OrthoHMM errors |
| Stale cache | `rm -rf work .nextflow .nextflow.log*` |
