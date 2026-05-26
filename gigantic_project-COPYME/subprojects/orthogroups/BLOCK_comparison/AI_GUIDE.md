# AI_GUIDE — BLOCK_comparison (orthogroups)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 February 28 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

**For AI Assistants**: Read `../AI_GUIDE.md` first for subproject overview and standardized output format. This guide covers the cross-method comparison project.

## Where this fits

- Parent subproject: [`../AI_GUIDE.md`](../AI_GUIDE.md) — orthogroups overview + tool comparison
- Parent project: [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- Prerequisite BLOCKs: at least 2 of `BLOCK_orthofinder` / `BLOCK_orthofinder_array` / `BLOCK_orthohmm` / `BLOCK_orthohmm_GIGANTIC` / `BLOCK_broccoli` must have run first
- Workflow to run: [`workflow-COPYME-compare_methods/README.md`](workflow-COPYME-compare_methods/README.md)
- Reads from: `../output_to_input/BLOCK_*/` (standardized orthogroup tables from any tool BLOCK)
- Outputs to: `../output_to_input/BLOCK_comparison/` (cross-method comparison tables + visualizations)

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE.md` |
| Orthogroups overview, tool comparison | `../AI_GUIDE.md` |
| Comparison concepts | This file |
| Running the workflow | `workflow-COPYME-compare_methods/ai/AI_GUIDE.md` |

## Comparison Overview

The comparison project performs cross-method analysis of orthogroup detection results from OrthoFinder, OrthoHMM, and Broccoli. It reads standardized output from the subproject-root `output_to_input/BLOCK_*/` directories and produces comparative statistics.

**Prerequisite**: At least 2 of the 3 tool projects must have completed their pipelines and populated their `output_to_input/BLOCK_*/` directories.

## Pipeline Scripts (2 steps)

| # | Script | Purpose |
|---|--------|---------|
| 001 | `001_ai-python-load_tool_results.py` | Load standardized results from output_to_input/BLOCK_*/ |
| 002 | `002_ai-python-compare_orthogroup_methods.py` | Cross-method comparison and statistics |

## Comparison Output

| File | Contents |
|------|----------|
| `method_comparison_summary.tsv` | Side-by-side statistics (orthogroup count, coverage, sizes) |
| `gene_overlap_between_methods.tsv` | Gene-level overlap and Jaccard indices between tool pairs |
| `orthogroup_size_comparison.tsv` | Size distribution comparison across methods |

## Interpreting Results

- **High Jaccard index** (>0.8): Methods agree strongly on gene assignments
- **Low Jaccard index** (<0.5): Methods disagree; investigate divergent sequences
- **Size distribution differences**: Different MCL inflation or clustering parameters
- **Coverage differences**: Different sensitivity to orphan genes
