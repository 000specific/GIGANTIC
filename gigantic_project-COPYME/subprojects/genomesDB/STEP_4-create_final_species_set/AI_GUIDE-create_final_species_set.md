# AI Guide: STEP_4-create_final_species_set (genomesDB)

**For AI Assistants**: This guide covers STEP_4 of the genomesDB subproject. For genomesDB overview and pipeline architecture, see `../AI_GUIDE-genomesDB.md`. For GIGANTIC overview, see `../../../AI_GUIDE-project.md`.

**Location**: `gigantic_project-COPYME/subprojects/genomesDB/STEP_4-create_final_species_set/`

---

## CRITICAL: Surface Discrepancies - No Silent Changes

**The user is managing this project - you must surface discrepancies so the user can make decisions. Silent changes undermine project management.**

- NEVER silently do something different than requested
- NEVER assume you know better and proceed without asking
- ALWAYS stop and explain the discrepancy
- ALWAYS ask for clarification before proceeding

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../../AI_GUIDE-project.md` |
| genomesDB concepts, pipeline architecture | `../AI_GUIDE-genomesDB.md` |
| STEP_4 concepts and troubleshooting (this step) | This file |
| Running the workflow | `workflow-COPYME-*/ai/AI_GUIDE-create_final_species_set_workflow.md` |

---

## Purpose of STEP_4

STEP_4 is the **final step** in the genomesDB pipeline. It creates the definitive species set that all downstream subprojects use.

**What it does**: Selects and copies proteomes (from STEP_2) and BLAST databases (from STEP_3) based on user configuration. This is a **copy/filter** step, not a processing step.

**Why a separate step?** After STEP_2 evaluates genome/proteome quality, the user may want to exclude certain species (poor assembly quality, contamination, etc.). STEP_4 gives the user explicit control over which species enter the downstream analyses.

---

## Prerequisites

| Prerequisite | Why | How to verify |
|-------------|-----|---------------|
| STEP_2 complete | Provides cleaned, standardized proteomes | Check `../STEP_2-*/workflow-RUN_*/OUTPUT_pipeline/` for proteome files |
| STEP_3 complete | Provides BLAST databases | Check `../STEP_3-databases/workflow-RUN_*/OUTPUT_pipeline/` for blastp files |
| User evaluation | User must decide which species to keep | User reviews STEP_2 quality metrics |

---

## Data Flow

```
STEP_2 (cleaned proteomes)  ──┐
                               ├──> STEP_4 (select + copy) ──> output_to_input/
STEP_3 (BLAST databases)   ──┘                                   ├── speciesN_gigantic_T1_proteomes/
                                                                  └── speciesN_gigantic_T1_blastp/
                                                                         │
                                                                         └──> downstream subprojects
                                                                              (orthogroups, gene_trees, etc.)
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `workflow-*/final_species_set_config.yaml` | Paths to STEP_2 and STEP_3 outputs | **YES** (required) |
| `workflow-*/INPUT_user/selected_species.txt` | Species selection list | **YES** (optional - defaults to all) |
| `workflow-*/RUN-workflow.sh` | Local execution script | No |
| `workflow-*/RUN-workflow.sbatch` | SLURM execution script | **YES** (account/qos) |
| `workflow-*/ai/scripts/001_ai-python-validate_species_selection.py` | Validates species selection | No (AI-generated) |
| `workflow-*/ai/scripts/002_ai-python-copy_selected_files.py` | Copies selected files | No (AI-generated) |
| `output_to_input/` | Final species set for downstream | No (auto-populated) |
| `RUN-clean_and_record_subproject.sh` | Cleanup and session recording | No |
| `RUN-update_upload_to_server.sh` | Manage upload_to_server/ symlinks | No |

---

## The speciesN Naming Convention

STEP_4 outputs use a `speciesN_` prefix where N is the count of selected species:

- `species69_gigantic_T1_proteomes/` - 69 species were selected
- `species71_gigantic_T1_blastp/` - 71 species were selected

This convention makes it immediately clear how many species are in the final set, and downstream subprojects can reference the correct directory.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "STEP_2 proteomes not found" | Config path wrong or STEP_2 not run | Verify path in `final_species_set_config.yaml`; run STEP_2 first |
| "STEP_3 BLAST databases not found" | Config path wrong or STEP_3 not run | Verify path in `final_species_set_config.yaml`; run STEP_3 first |
| "Species X not found in STEP_2" | Species in selection file but not in STEP_2 output | Check spelling in `selected_species.txt`; verify STEP_2 processed this species |
| "Species X not found in STEP_3" | Species in STEP_2 but missing from STEP_3 | Run STEP_3 for missing species; or remove from selection |
| "No species selected" | Empty selection file | Delete the file (defaults to all species) or add species names |
| "Permission denied" during copy | Insufficient permissions on source or target | Check file permissions with `ls -la` |
| output_to_input/ empty after run | Workflow may not have completed | Check workflow logs; re-run if needed |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| User says "run STEP_4" | "Have STEP_2 and STEP_3 completed? Do you want all species or a subset?" |
| User mentions species filtering | "Do you want to create INPUT_user/selected_species.txt with specific species, or start with all and remove some?" |
| Species count mismatch | "STEP_2 has N proteomes but STEP_3 has M databases. Some species may be missing from one. Should we proceed with the intersection?" |
| User asks about downstream | "STEP_4 outputs go to output_to_input/. Which downstream subproject do you want to configure next?" |

---

## Path Depth

From this step directory, project root is at `../../../`:

| Location | Relative path to project root |
|----------|-------------------------------|
| `STEP_4-create_final_species_set/` | `../../../` |
| `STEP_4-create_final_species_set/workflow-COPYME-*/` | `../../../../` |

---

## Research Notebook Location

All STEP_4 logs save to the genomesDB subproject location:
```
research_notebook/research_ai/subproject-genomesDB/
```

---

## Directory Structure

```
STEP_4-create_final_species_set/
├── README.md                              # Human-readable overview
├── AI_GUIDE-create_final_species_set.md   # THIS FILE
├── RUN-clean_and_record_subproject.sh     # Cleanup and session recording
├── RUN-update_upload_to_server.sh         # Manage upload_to_server/ symlinks
├── output_to_input/                       # Final species set for downstream
│   ├── speciesN_gigantic_T1_proteomes/    # Created by workflow
│   └── speciesN_gigantic_T1_blastp/       # Created by workflow
├── upload_to_server/                      # Curated data for GIGANTIC server
└── workflow-COPYME-create_final_species_set/
    ├── README.md
    ├── RUN-workflow.sh
    ├── RUN-workflow.sbatch
    ├── final_species_set_config.yaml
    ├── INPUT_user/
    │   └── selected_species.txt           # User species selection (optional)
    ├── OUTPUT_pipeline/
    │   ├── 1-output/                      # Validated species list
    │   └── 2-output/                      # Copied species files
    └── ai/
        ├── AI_GUIDE-create_final_species_set_workflow.md
        ├── main.nf
        ├── nextflow.config
        └── scripts/
            ├── 001_ai-python-validate_species_selection.py
            └── 002_ai-python-copy_selected_files.py
```
