# STEP_1-sources - Collect Source Genomes

**AI**: Claude Code | Opus 4.5 | 2026 February 12
**Human**: Eric Edsinger

---

## Purpose

STEP_1 of the genomesDB pipeline. Collects proteome files from various sources (NCBI, UniProt, user-provided).

**Part of**: genomesDB subproject (see `../README.md`)

---

## Workflow

```bash
cd workflow-COPYME-collect_source_genomes/

# Local:
bash RUN-workflow.sh

# SLURM:
sbatch RUN-workflow.sbatch
```

---

## Inputs

- Species list or source manifest
- Download configuration

**Location**: `workflow-COPYME-collect_source_genomes/INPUT_user/`

---

## Outputs

Raw proteome files organized by source.

**Passed to STEP_2 via**: `output_to_input/`

---

## Research Notebook

All logs and sessions saved to:
```
research_notebook/research_ai/subproject-genomesDB/
```

---

## Dependencies

- phylonames subproject (for species naming)
- Network access (for downloads)

---

## Notes

This is a placeholder README. Content will be populated when copying the working sources workflow from ai_ctenophores.
