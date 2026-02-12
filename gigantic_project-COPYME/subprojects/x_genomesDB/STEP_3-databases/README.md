# STEP_3-databases - Build GIGANTIC GenomesDB

**AI**: Claude Code | Opus 4.5 | 2026 February 12
**Human**: Eric Edsinger

---

## Purpose

STEP_3 of the genomesDB pipeline. Builds BLAST databases and search indices from standardized proteomes.

**Part of**: genomesDB subproject (see `../README.md`)

---

## Workflow

```bash
cd workflow-COPYME-build_gigantic_genomesDB/

# Local:
bash RUN-workflow.sh

# SLURM:
sbatch RUN-workflow.sbatch
```

---

## Inputs

Standardized proteomes from STEP_2-standardize_and_evaluate.

**Location**: `workflow-COPYME-build_gigantic_genomesDB/INPUT_user/`
**From**: `../STEP_2-standardize_and_evaluate/output_to_input/`

---

## Outputs

- BLAST databases (blastp)
- Species manifests
- Proteome indices

**Shared with other subprojects via**: `../output_to_input/` (genomesDB root)

---

## Research Notebook

All logs and sessions saved to:
```
research_notebook/research_ai/subproject-genomesDB/
```

---

## Dependencies

- STEP_2-standardize_and_evaluate must complete first
- BLAST+ tools

---

## Notes

This is a placeholder README. Content will be populated when copying the working workflow from ai_ctenophores.
