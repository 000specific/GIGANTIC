# AI_GUIDE — orthogroups workflow runbook (BLOCK_comparison)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 to 4.7 | 2026 Feb-May (multiple passes)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK AI guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md)
- Parent subproject AI guide: [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- User-facing workflow README: [`../README.md`](../README.md)
- Reads from: `../../../output_to_input/BLOCK_*/` (any tool BLOCK that's run)
- Outputs to: `../../../output_to_input/BLOCK_comparison/`

---

**For AI Assistants**: Read `../../AI_GUIDE.md` first for comparison concepts. This guide focuses on running the workflow.

## Quick Start

```bash
# Verify at least 2 tools have results (all in subproject-root output_to_input/)
ls ../../output_to_input/BLOCK_orthofinder/
ls ../../output_to_input/BLOCK_orthohmm/
ls ../../output_to_input/BLOCK_broccoli/

bash RUN-workflow.sh
```

Modern conda convention: `RUN-workflow.sh` auto-creates env `aiG-orthogroups-comparison`
from `ai/conda_environment.yml` on first run, then activates it before invoking
NextFlow. No need to `conda activate` manually.

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
