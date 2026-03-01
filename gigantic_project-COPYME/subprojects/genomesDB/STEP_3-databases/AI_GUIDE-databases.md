# AI Guide: STEP_3-databases (genomesDB)

**For AI Assistants**: This guide covers STEP_3 of the genomesDB subproject. For genomesDB overview and four-step architecture, see `../AI_GUIDE-genomesDB.md`. For GIGANTIC overview, see `../../../AI_GUIDE-project.md`.

**Location**: `gigantic_project-COPYME/subprojects/genomesDB/STEP_3-databases/`

---

## ⚠️ CRITICAL: Surface Discrepancies - No Silent Changes

**The user is managing this project - you must surface discrepancies so the user can make decisions. Silent changes undermine project management.**

- ❌ **NEVER** silently do something different than requested
- ❌ **NEVER** assume you know better and proceed without asking
- ✅ **ALWAYS** stop and explain the discrepancy
- ✅ **ALWAYS** ask for clarification before proceeding

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../../AI_GUIDE-project.md` |
| genomesDB concepts, four-step structure | `../AI_GUIDE-genomesDB.md` |
| STEP_3 databases concepts (this step) | This file |
| Running the workflow | `workflow-COPYME-*/ai/AI_GUIDE-*_workflow.md` |

---

## What This Step Does

**Purpose**: Build BLAST databases and search indices.

**Inputs**: Standardized proteomes from STEP_2-standardize_and_evaluate

**Outputs**:
- BLAST databases (blastp)
- Species manifests
- Proteome indices

**Shared with**: Other GIGANTIC subprojects via `../output_to_input/`

---

## Path Depth

From this step directory, project root is at `../../../`:

| Location | Relative path to project root |
|----------|-------------------------------|
| `STEP_3-databases/` | `../../../` |
| `STEP_3-databases/workflow-COPYME-*/` | `../../../../` |

---

## Research Notebook Location

All STEP_3 logs save to the genomesDB subproject location:
```
research_notebook/research_ai/subproject-genomesDB/
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `workflow-*/INPUT_user/` | Input from STEP_2 | No |
| `workflow-*/RUN-*.sbatch` | SLURM account/qos | **YES** (SLURM) |
| `output_to_input/` | BLAST databases | No |
| `../output_to_input/` | Shared with other subprojects | No |

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| No input files | STEP_2 not run | Run STEP_2-standardize_and_evaluate first |
| makeblastdb failed | BLAST+ not installed | Install BLAST+ tools |
| Empty database | No proteomes passed QC | Check STEP_2 evaluation reports |
| Disk full | Large database | Free disk space |

---

## Dependencies

- STEP_2-standardize_and_evaluate must complete first
- BLAST+ tools must be installed (available in `ai_gigantic_genomesdb` conda environment)

---

## Next Step

After STEP_3 completes, proceed to **STEP_4-create_final_species_set** to select and copy the final species set for downstream subprojects.
