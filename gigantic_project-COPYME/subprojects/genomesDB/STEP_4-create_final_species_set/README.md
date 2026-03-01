# STEP_4-create_final_species_set - Create Final Species Set

**AI**: Claude Code | Opus 4.6 | 2026 February 28
**Human**: Eric Edsinger

---

## Purpose

STEP_4 of the genomesDB pipeline. **Creates the final species set** by selecting and copying proteomes and BLAST databases from STEP_2 and STEP_3 outputs.

This is the **final step** in the genomesDB pipeline. Downstream subprojects (orthogroups, gene trees, etc.) read their species data from this step's `output_to_input/` directory.

**Part of**: genomesDB subproject (see `../README.md`)

---

## What This Step Does

STEP_4 is a **copy/filter** step, not a processing step:

1. User reviews STEP_2 quality metrics and decides which species to keep
2. User configures species selection in `INPUT_user/selected_species.txt` (or uses all species by default)
3. Script 001 validates the selection against STEP_2 and STEP_3 outputs
4. Script 002 copies selected proteomes and BLAST databases
5. Final outputs go to `output_to_input/` with `speciesN_` naming convention

---

## Quick Start

```bash
# 1. Copy workflow template
cp -r workflow-COPYME-create_final_species_set workflow-RUN_01-create_final_species_set
cd workflow-RUN_01-create_final_species_set

# 2. Edit configuration with paths to STEP_2 and STEP_3 outputs
nano final_species_set_config.yaml

# 3. Optional: edit species selection (defaults to all species)
nano INPUT_user/selected_species.txt

# 4. Run locally:
bash RUN-workflow.sh

# 4b. Or on SLURM (edit account/qos first):
sbatch RUN-workflow.sbatch
```

---

## Inputs

| Source | Data | Location |
|--------|------|----------|
| STEP_2 | Cleaned proteomes | Configured in `final_species_set_config.yaml` |
| STEP_3 | BLAST databases | Configured in `final_species_set_config.yaml` |
| User | Species selection (optional) | `INPUT_user/selected_species.txt` |

---

## Outputs

| Output | Location | Description |
|--------|----------|-------------|
| Final proteomes | `output_to_input/speciesN_gigantic_T1_proteomes/` | For downstream subprojects |
| Final BLAST DBs | `output_to_input/speciesN_gigantic_T1_blastp/` | For BLAST searches |

Where N = count of selected species (e.g., species69, species71).

---

## Dependencies

- **STEP_2-standardize_and_evaluate** must complete first (provides cleaned proteomes)
- **STEP_3-databases** must complete first (provides BLAST databases)
- **Conda environment**: `ai_gigantic_genomesdb` with NextFlow installed

---

## Research Notebook

All logs and sessions saved to:
```
research_notebook/research_ai/subproject-genomesDB/
```

---

## Directory Structure

```
STEP_4-create_final_species_set/
├── README.md                              # This file
├── AI_GUIDE-create_final_species_set.md   # Guide for AI assistants
├── RUN-clean_and_record_subproject.sh     # Cleanup and session recording
├── RUN-update_upload_to_server.sh         # Manage upload_to_server/ symlinks
├── output_to_input/                       # Final species set for downstream subprojects
├── upload_to_server/                      # Curated data for GIGANTIC server
└── workflow-COPYME-create_final_species_set/
    ├── README.md
    ├── RUN-workflow.sh
    ├── RUN-workflow.sbatch
    ├── final_species_set_config.yaml
    ├── INPUT_user/
    │   └── selected_species.txt           # Species selection (optional)
    └── ai/
        ├── AI_GUIDE-create_final_species_set_workflow.md
        ├── main.nf
        ├── nextflow.config
        └── scripts/
            ├── 001_ai-python-validate_species_selection.py
            └── 002_ai-python-copy_selected_files.py
```
