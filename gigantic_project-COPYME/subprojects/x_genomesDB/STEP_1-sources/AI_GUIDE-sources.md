# AI Guide: STEP_1-sources (genomesDB)

**For AI Assistants**: This guide covers STEP_1 of the genomesDB subproject. For genomesDB overview and three-step architecture, see `../AI_GUIDE-genomesDB.md`. For GIGANTIC overview, see `../../../AI_GUIDE-project.md`.

**Location**: `gigantic_project-*/subprojects/genomesDB/STEP_1-sources/`

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../../AI_GUIDE-project.md` |
| genomesDB concepts, three-step structure | `../AI_GUIDE-genomesDB.md` |
| STEP_1 sources concepts (this step) | This file |
| Running the workflow | `workflow-COPYME-*/ai/AI_GUIDE-*_workflow.md` |

---

## What This Step Does

**Purpose**: Collect proteome files from various sources.

**Sources**:
- NCBI protein databases
- UniProt
- User-provided files

**Outputs**: Raw proteome files passed to STEP_2-standardize_and_evaluate

---

## Path Depth

From this step directory, project root is at `../../../`:

| Location | Relative path to project root |
|----------|-------------------------------|
| `STEP_1-sources/` | `../../../` |
| `STEP_1-sources/workflow-COPYME-*/` | `../../../../` |

---

## Research Notebook Location

All STEP_1 logs save to the genomesDB subproject location:
```
research_notebook/research_ai/subproject-genomesDB/
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `workflow-*/INPUT_user/source_manifest.tsv` | What to download | **YES** |
| `workflow-*/RUN-*.sbatch` | SLURM account/qos | **YES** (SLURM) |
| `output_to_input/` | Raw proteomes for STEP_2 | No |

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| Download failed | Network or server down | Check connectivity, retry |
| Species not found | Not in NCBI/UniProt | Check species name, try synonym |
| Permission denied | Scripts not executable | `chmod +x ai/scripts/*.sh` |

---

## Notes

This is a placeholder AI guide. Content will be expanded when copying the working sources workflow from ai_ctenophores.
