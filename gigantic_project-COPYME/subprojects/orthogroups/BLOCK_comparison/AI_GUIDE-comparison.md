# AI_GUIDE-comparison.md (Level 2: Tool Project Guide)

**For AI Assistants**: Read `../AI_GUIDE-orthogroups.md` first for subproject overview and standardized output format. This guide covers the cross-method comparison project.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE-project.md` |
| Orthogroups overview, tool comparison | `../AI_GUIDE-orthogroups.md` |
| Comparison concepts | This file |
| Running the workflow | `workflow-COPYME-compare_methods/ai/AI_GUIDE-comparison_workflow.md` |

## Comparison Overview

The comparison project performs cross-method analysis of orthogroup detection results from OrthoFinder, OrthoHMM, and Broccoli. It reads standardized output from each tool's `output_to_input/` directory and produces comparative statistics.

**Prerequisite**: At least 2 of the 3 tool projects must have completed their pipelines and populated their `output_to_input/` directories.

## Pipeline Scripts (2 steps)

| # | Script | Purpose |
|---|--------|---------|
| 001 | `001_ai-python-load_tool_results.py` | Load standardized results from tool output_to_input/ |
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
