# AI Guide: score_structures_by_ocl_orthogroups Workflow

**AI**: Claude Code | Opus 4.7 | 2026 May 11
**Human**: Eric Edsinger

**For AI Assistants**: Read the project guide (`../../../../AI_GUIDE-project.md`),
subproject guide (`../../AI_GUIDE-parsimony_tree_structures.md`), and BLOCK
guide (`../AI_GUIDE-ocl_orthogroups.md`) first. This guide focuses on running
this specific workflow.

---

## Quick Reference

| User needs... | Go to... |
|---|---|
| GIGANTIC overview | `../../../../AI_GUIDE-project.md` |
| Subproject concepts (BLOCKs, scores, bootstrap) | `../../AI_GUIDE-parsimony_tree_structures.md` |
| BLOCK concepts | `../AI_GUIDE-ocl_orthogroups.md` |
| Running this workflow | This file |

---

## Running the Workflow

1. Copy the COPYME template to a run instance:
   ```
   cp -r workflow-COPYME-score_structures_by_ocl_orthogroups \\
         workflow-RUN_1-score_structures_by_ocl_orthogroups
   cd workflow-RUN_1-score_structures_by_ocl_orthogroups
   ```

2. Edit `START_HERE-user_config.yaml`:
   - `run_label` — typically matches the upstream OCL run_label
     (e.g., `species70_X_OrthoHMM_GIGANTIC`).
   - `species_set_name` — e.g., `species70`.
   - `orthogroup_tool` — `OrthoFinder` / `OrthoHMM` / `Broccoli` (descriptive).
   - `inputs.ocl_orthogroups_dir` — relative path to upstream OCL run_label.
   - `inputs.trees_species_dir` — relative path to trees_species
     `output_to_input/BLOCK_permutations_and_features`.
   - `bootstrap.iterations` — default 1000; lower for quick smoke tests.
   - `execution_mode` — `local` (default) or `slurm`.

3. Edit `INPUT_user/structure_manifest.tsv` — typically list all 105 structures.

4. Run:
   ```
   bash RUN-workflow.sh
   ```

---

## Pipeline Steps

| Process | Script | Reads | Writes |
|---|---|---|---|
| `validate_inputs` | `scripts/001_ai-python-validate_inputs.py` | structure_manifest.tsv, OCL summary TSVs (header + row counts only) | `OUTPUT_pipeline/1-output/1_ai-input_validation_report.tsv` |
| `aggregate_ocl_per_structure` | `scripts/002_ai-python-aggregate_ocl_per_structure.py` | OCL summary TSVs | `OUTPUT_pipeline/2-output/2_ai-aggregate_ocl-per_structure.tsv` (one row per structure) |
| `compute_parsimony_scores` | `scripts/003_ai-python-compute_parsimony_scores.py` | 2-output aggregate | `OUTPUT_pipeline/3-output/3_ai-parsimony_scores-per_structure.tsv` |
| `bootstrap_ranking_confidence` | `scripts/004_ai-python-bootstrap_ranking_confidence.py` | per-orthogroup losses extracted live from OCL TSVs | `OUTPUT_pipeline/4-output/4_ai-bootstrap_confidence-per_structure.tsv` |
| `rank_structures_and_summarize` | `scripts/005_ai-python-rank_structures_and_summarize.py` | 3-output + 4-output | `OUTPUT_pipeline/5-output/5_ai-parsimony_ranking-structures.tsv` + `5_ai-parsimony_best_structure.txt` |
| `visualize_ranking` | `scripts/006_ai-python-visualize_ranking.py` | 5-output ranking | `OUTPUT_pipeline/6-output/figures/*.png` |
| `write_run_log` | `scripts/007_ai-python-write_run_log.py` | config, OUTPUT_pipeline tree | `ai/logs/<timestamp>-run_log.json` |

---

## Common Execution Errors

| Error | Cause | Solution |
|---|---|---|
| 001: `OCL summary file not found for structure_NNN` | Upstream `orthogroups_X_ocl` not run for this structure under the configured run_label | Check `inputs.ocl_orthogroups_dir/structure_NNN/4_ai-orthogroups-complete_ocl_summary.tsv`. If missing, re-run `orthogroups_X_ocl` first. |
| 001: `Required column 'Loss_Events' missing` | Upstream OCL schema change | Re-run `orthogroups_X_ocl` with current code |
| 002: `pandas.errors.ParserError` | A summary TSV is malformed | Inspect the offending file; re-run the upstream step that produced it |
| 004: `Cannot bootstrap on 1 structure` | Single-structure manifest | Add more structures to the manifest |
| 006: `ImportError: matplotlib` | conda env missing matplotlib | Remove `aiG-parsimony_tree_structures-ocl_orthogroups` env and re-run RUN-workflow.sh to recreate |

---

## Diagnostic Commands

```
# Confirm upstream OCL output exists
ls ../../../../orthogroups_X_ocl/output_to_input/BLOCK_ocl_analysis/

# Confirm trees_species output exists
ls ../../../../trees_species/output_to_input/BLOCK_permutations_and_features/

# Check NextFlow execution status
cat OUTPUT_pipeline/pipeline_trace.txt

# View final ranking
head OUTPUT_pipeline/5-output/5_ai-parsimony_ranking-structures.tsv
cat OUTPUT_pipeline/5-output/5_ai-parsimony_best_structure.txt
```

---

## Cleanup After a Run

NextFlow leaves `work/`, `.nextflow/`, and `.nextflow.log*` behind. To clean:

```
rm -rf work .nextflow .nextflow.log*
```

For routine cleanup across the whole subproject use
`../../../RUN-clean_and_record_subproject.sh --clean`.

---

## Questions to Ask

| Situation | Ask |
|---|---|
| User has not set `run_label` yet | "Which upstream `orthogroups_X_ocl` run_label should I read from?" |
| User wants partial-manifest run | "Should the parsimony ranking only cover that subset, or do you want the full 105-structure ranking with the subset just highlighted?" |
| `Score_Total_Losses` vs the other scores diverge | "The scores agree on ranking when the input set is large; divergence usually means a structure has unusual continued-absence patterns. Want me to investigate which structures disagree most across scores?" |
