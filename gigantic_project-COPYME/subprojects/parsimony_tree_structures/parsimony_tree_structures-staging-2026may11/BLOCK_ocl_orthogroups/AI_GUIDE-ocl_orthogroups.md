# AI Guide: BLOCK_ocl_orthogroups

**AI**: Claude Code | Opus 4.7 | 2026 May 11
**Human**: Eric Edsinger

**For AI Assistants**: Read the project guide
(`../../../AI_GUIDE-project.md`) and subproject guide
(`../AI_GUIDE-parsimony_tree_structures.md`) first. This guide covers the
`BLOCK_ocl_orthogroups` BLOCK specifically.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../AI_GUIDE-project.md` |
| Subproject concepts (multiple BLOCKs, score variants) | `../AI_GUIDE-parsimony_tree_structures.md` |
| BLOCK_ocl_orthogroups concepts | This file |
| Running the workflow | `workflow-COPYME-score_structures_by_ocl_orthogroups/ai/AI_GUIDE-score_structures_by_ocl_orthogroups_workflow.md` |

---

## What This BLOCK Does

Ranks candidate species tree `structure_NNN` by **parsimony scores derived
from orthogroup OCL data**.

Inputs are the per-structure complete OCL summaries produced by
`orthogroups_X_ocl/`:

```
orthogroups_X_ocl/output_to_input/BLOCK_ocl_analysis/<run_label>/
    structure_001/4_ai-orthogroups-complete_ocl_summary.tsv
    structure_002/4_ai-orthogroups-complete_ocl_summary.tsv
    ...
```

Each summary lists every orthogroup with its `Conservation_Events`,
`Loss_Events`, `Continued_Absence_Events` counts under that structure. This
BLOCK aggregates those counts per structure, derives the multiple parsimony
scores (see subproject guide), bootstraps for confidence, and writes a single
ranking table.

## Why "ocl_orthogroups" and Not Just "orthogroups"?

The BLOCK name is `BLOCK_ocl_orthogroups` (not `BLOCK_orthogroups`) because
the **feature signal** being consumed is the OCL processing of orthogroups,
not raw orthogroup membership. The same orthogroup set scored against two
different species trees will yield two different OCL outputs and two
different parsimony scores. The BLOCK consumes the OCL output, not the
upstream orthogroup table.

Sister BLOCKs follow the same convention:

| Sister BLOCK (planned) | Feature signal | Upstream OCL subproject |
|---|---|---|
| `BLOCK_ocl_annotations` | OCL over HMM annotations | `annotations_X_ocl/` |
| `BLOCK_ocl_gene_groups` | OCL over gene groups | `gene_groups_X_ocl/` |

---

## Workflow Outline

The BLOCK contains a single workflow template,
`workflow-COPYME-score_structures_by_ocl_orthogroups/`, which the user
copies to `workflow-RUN_N-score_structures_by_ocl_orthogroups/` to run.

The workflow runs 7 sequential Python scripts. None of them require fan-out
across structures — each structure produces a single small aggregate row, so
all 105 are scanned in a single Python pass per script. This is intentionally
simpler than the upstream `orthogroups_X_ocl/` workflow (which fans out
per-structure because each structure requires heavy MRCA computation).

| Script | Purpose | Output |
|---|---|---|
| 001 | Validate inputs: structure_manifest, OCL paths per structure exist, required columns present | `OUTPUT_pipeline/1-output/1_ai-input_validation_report.tsv` |
| 002 | Aggregate OCL per structure: read each structure's summary TSV, sum the relevant columns, emit one row per structure | `OUTPUT_pipeline/2-output/2_ai-aggregate_ocl-per_structure.tsv` |
| 003 | Compute parsimony scores: side-by-side variants (Total_Losses, State_Transitions, Continued_Absence, Conservation_to_Loss_Ratio, Mean_Losses_Per_Orthogroup) | `OUTPUT_pipeline/3-output/3_ai-parsimony_scores-per_structure.tsv` |
| 004 | Bootstrap orthogroups: resample (default 1000 iterations), recompute `Score_Total_Losses` per structure, emit per-structure mean rank + 95% CI + pct_times_best | `OUTPUT_pipeline/4-output/4_ai-bootstrap_confidence-per_structure.tsv` |
| 005 | Dual rank by loss-min AND shallow-gain, identify best per criterion, flag agreement | `OUTPUT_pipeline/5-output/5_ai-parsimony_ranking-structures.tsv` + `5_ai-parsimony_best_structure.txt` |
| 006 | Visualize: colorblind-safe bar charts (loss-min and shallow-gain), 5-state stacked bar, all-scores heatmap, rank-agreement scatter | `OUTPUT_pipeline/6-output/figures/*.png` |
| 008 | Diagnose criteria divergence: Spearman + Pearson correlation, per-orthogroup origin-block shifts (3 pairwise TSVs), per-structure unresolved-zone topology summary | `OUTPUT_pipeline/8-output/*.tsv` + `8_ai-criteria_divergence_summary.txt` |
| 007 | Write run log: timestamped record of configuration, inputs, scripts, durations | `ai/logs/<timestamp>-run_log.json` |

The workflow's RUN-workflow.sh creates symlinks under
`../../output_to_input/BLOCK_ocl_orthogroups/<run_label>/` pointing to the
ranking table and best-structure text file, so downstream subprojects can
read these from a stable path.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| 001: "OCL summary file not found: structure_NNN" | Upstream `orthogroups_X_ocl` was not run for this structure | Check `orthogroups_X_ocl/output_to_input/BLOCK_ocl_analysis/<run_label>/structure_NNN/` |
| 001: "Required column 'Loss_Events' missing" | Upstream OCL schema drift | Re-run `orthogroups_X_ocl` with the current code |
| 002: "Orthogroup count differs between structures" | Some structures saw orthogroups others did not (should never happen — same orthogroup table per structure in OCL) | Investigate `orthogroups_X_ocl` — different structures should share the same orthogroup set |
| 004: "Cannot bootstrap: only 1 structure" | Single-structure manifest | Add more structures; bootstrap is meaningful only for ≥2 structures |
| 006: "matplotlib not available" | conda env missing matplotlib | Re-create env from `ai/conda_environment.yml` |

---

## Key Files

| File | User Edits? | Purpose |
|------|------------|---------|
| `workflow-COPYME-.../START_HERE-user_config.yaml` | Yes | `run_label` (output_to_input namespace), `ocl_orthogroups_dir`, `bootstrap_iterations`, execution mode |
| `workflow-COPYME-.../INPUT_user/structure_manifest.tsv` | Yes | Structure IDs to rank |
| `workflow-COPYME-.../ai/conda_environment.yml` | No | Per-BLOCK env: python, pyyaml, pandas, numpy, matplotlib |
