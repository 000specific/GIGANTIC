# STEP_2-standardize_and_evaluate - Standardize and Evaluate Genomes

**AI**: Claude Code | Opus 4.5 | 2026 February 12
**Human**: Eric Edsinger

---

## Purpose

STEP_2 of the genomesDB pipeline. Standardizes proteome file formats, applies phyloname-based naming, and evaluates genome quality.

**Part of**: genomesDB subproject (see `../README.md`)

---

## Workflow

```bash
cd workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/

# Local:
bash RUN-workflow.sh

# SLURM:
sbatch RUN-workflow.sbatch
```

---

## Inputs

Raw proteome files from STEP_1-sources.

**Location**: `workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/INPUT_user/`
**From**: `../STEP_1-sources/output_to_input/`

---

## Outputs

- Standardized proteomes with phyloname-based naming
- Quality evaluation reports
- Statistics and metadata

**Passed to STEP_3 via**: `output_to_input/`

---

## Research Notebook

All logs and sessions saved to:
```
research_notebook/research_ai/subproject-genomesDB/
```

---

## Dependencies

- STEP_1-sources must complete first
- phylonames subproject (for species naming)

---

## Notes

This is a placeholder README. Content will be populated when copying the working workflow from ai_ctenophores.
