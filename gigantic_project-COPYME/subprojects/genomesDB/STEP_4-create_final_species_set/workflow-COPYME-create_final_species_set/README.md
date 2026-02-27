# workflow-COPYME-create_final_species_set

**AI**: Claude Code | Opus 4.6 | 2026 February 27
**Human**: Eric Edsinger

---

## Purpose

STEP_4 workflow for creating the final species set for downstream subprojects.

**Part of**: STEP_4-create_final_species_set (see `../README.md`)

---

## What This Workflow Does

STEP_4 is a **COPY/FILTER** step, not a processing step:

1. **Validates Species Selection** (Script 001)
   - Checks that all selected species exist in STEP_2 and STEP_3 outputs
   - Defaults to all species if no selection file provided

2. **Copies Selected Files** (Script 002)
   - Copies proteomes from STEP_2 for selected species
   - Copies BLAST databases from STEP_3 for selected species
   - Creates directories with `speciesN_` naming convention

---

## Usage

**Copy this template to create a run directory:**
```bash
cp -r workflow-COPYME-create_final_species_set workflow-RUN_01-create_final_species_set
cd workflow-RUN_01-create_final_species_set
```

**Configure your run:**
```bash
# Edit the configuration file with paths to STEP_2 and STEP_3 outputs
nano final_species_set_config.yaml

# Optional: Edit species selection (defaults to all species)
nano INPUT_user/selected_species.txt
```

**Run locally:**
```bash
bash RUN-create_final_species_set.sh
```

**Run on SLURM:**
```bash
# Edit RUN-create_final_species_set.sbatch to set --account and --qos
sbatch RUN-create_final_species_set.sbatch
```

---

## Prerequisites

- **STEP_2** complete (provides cleaned proteomes and quality metrics)
- **STEP_3** complete (provides BLAST databases)
- **User evaluation** of STEP_2 quality metrics to decide species selection
- **Conda environment**: `ai_gigantic_genomesdb` with NextFlow installed

---

## Directory Structure

```
workflow-COPYME-create_final_species_set/
├── README.md                              # This file
├── RUN-create_final_species_set.sh        # Local runner (calls NextFlow)
├── RUN-create_final_species_set.sbatch    # SLURM wrapper
├── final_species_set_config.yaml          # User-editable configuration
├── INPUT_user/                            # User inputs
│   └── selected_species.txt               # Species selection (optional)
├── OUTPUT_pipeline/                       # Workflow outputs
│   ├── 1-output/                          # Validated species list
│   └── 2-output/                          # Final species directories
└── ai/
    ├── main.nf                            # NextFlow pipeline definition
    ├── nextflow.config                    # NextFlow settings
    └── scripts/
        ├── 001_ai-python-validate_species_selection.py
        └── 002_ai-python-copy_selected_files.py
```

---

## Outputs

| Output | Location | Description |
|--------|----------|-------------|
| Validated species list | `1-output/1_ai-validated_species_list.txt` | Species that passed validation |
| Species count | `1-output/1_ai-species_count.txt` | Number of selected species (N) |
| Final proteomes | `2-output/speciesN_gigantic_T1_proteomes/` | Copied proteome files |
| Final BLAST DBs | `2-output/speciesN_gigantic_T1_blastp/` | Copied BLAST database files |
| Copy manifest | `2-output/2_ai-copy_manifest.tsv` | Record of all copied files |

---

## Final Outputs in output_to_input/

The workflow automatically copies final outputs to `../../output_to_input/`:
- `speciesN_gigantic_T1_proteomes/` - For downstream subprojects (orthohmm, etc.)
- `speciesN_gigantic_T1_blastp/` - For BLAST searches

Where N = count of selected species (e.g., species69, species71)

---

## Next Step

After this workflow completes, downstream subprojects can access:
```
genomesDB/output_to_input/speciesN_gigantic_T1_proteomes/
genomesDB/output_to_input/speciesN_gigantic_T1_blastp/
```
