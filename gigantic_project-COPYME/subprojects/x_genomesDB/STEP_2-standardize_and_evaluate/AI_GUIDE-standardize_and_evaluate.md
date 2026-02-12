# AI Guide: STEP_2-standardize_and_evaluate (genomesDB)

**For AI Assistants**: This guide covers STEP_2 of the genomesDB subproject. For genomesDB overview and three-step architecture, see `../AI_GUIDE-genomesDB.md`. For GIGANTIC overview, see `../../../AI_GUIDE-project.md`.

**Location**: `gigantic_project-*/subprojects/genomesDB/STEP_2-standardize_and_evaluate/`

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../../AI_GUIDE-project.md` |
| genomesDB concepts, three-step structure | `../AI_GUIDE-genomesDB.md` |
| STEP_2 standardize_and_evaluate concepts (this step) | This file |
| Running the workflow | `workflow-COPYME-*/ai/AI_GUIDE-*_workflow.md` |

---

## What This Step Does

**Purpose**: Standardize proteome formats, apply phylonames, evaluate quality.

**Inputs**: Raw proteome files from STEP_1-sources

**Outputs**:
- Standardized proteomes with phyloname-based naming
- Quality evaluation reports
- Statistics and metadata

---

## Path Depth

From this step directory, project root is at `../../../`:

| Location | Relative path to project root |
|----------|-------------------------------|
| `STEP_2-standardize_and_evaluate/` | `../../../` |
| `STEP_2-standardize_and_evaluate/workflow-COPYME-*/` | `../../../../` |

---

## Research Notebook Location

All STEP_2 logs save to the genomesDB subproject location:
```
research_notebook/research_ai/subproject-genomesDB/
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `workflow-*/INPUT_user/` | Input from STEP_1 | No |
| `workflow-*/RUN-*.sbatch` | SLURM account/qos | **YES** (SLURM) |
| `output_to_input/` | Standardized proteomes for STEP_3 | No |

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| No input files | STEP_1 not run | Run STEP_1-sources workflow first |
| Phyloname lookup fails | phylonames not run | Run phylonames subproject |
| Invalid FASTA | Corrupted download | Re-run STEP_1 |
| Quality check failure | Low quality genome | Review evaluation report |

---

## Notes

This is a placeholder AI guide. Content will be expanded when copying the working workflow from ai_ctenophores.
