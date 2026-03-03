# AI_GUIDE-comparison_workflow.md (Level 3: Workflow Execution Guide)

**For AI Assistants**: Read `../../AI_GUIDE-comparison.md` first for comparison concepts. This guide focuses on running the workflow.

## Quick Start

```bash
module load conda
conda activate ai_gigantic_orthogroups
module load nextflow

# Verify at least 2 tools have results (all in subproject-root output_to_input/)
ls ../../output_to_input/BLOCK_orthofinder/
ls ../../output_to_input/BLOCK_orthohmm/
ls ../../output_to_input/BLOCK_broccoli/

bash ../RUN-workflow.sh
# Or: sbatch ../RUN-workflow.sbatch
```

## Pipeline Steps

1. **load_tool_results** - Loads standardized output from subproject-root output_to_input/BLOCK_*/ directories
2. **compare_methods** - Generates comparison statistics, overlap analysis, size distributions

## Verification Commands

```bash
ls OUTPUT_pipeline/*/
cat OUTPUT_pipeline/2-output/2_ai-method_comparison_summary.tsv
cat OUTPUT_pipeline/2-output/2_ai-gene_overlap_between_methods.tsv
```

## Common Errors

| Error | Solution |
|-------|----------|
| Need 2+ tools | Run at least 2 tool pipelines first |
| output_to_input empty | Tool pipeline didn't complete; check its logs |
| Stale cache | `rm -rf work .nextflow .nextflow.log*` |
