# workflow-COPYME-create_final_species_set

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 February 27 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent STEP: [`../README.md`](../README.md) — STEP_4-create_final_species_set overview
- Parent subproject: [`../../README.md`](../../README.md) — genomesDB overview
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Reads from: `../../output_to_input/STEP_2-standardize_and_evaluate/` (cleaned proteomes + annotations)
  + `../../output_to_input/STEP_3-databases/` (BLAST databases)
- **Downstream consumers** (per §40): every "real" GIGANTIC subproject —
  `orthogroups`, `annotations_hmms`, `trees_species`, `trees_gene_families`,
  `trees_gene_groups`, `gene_sizes`, `hotspots`, etc. all read the
  `speciesN_*` outputs from `output_to_input/STEP_4-create_final_species_set/`.

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
nano START_HERE-user_config.yaml

# Optional: Edit species selection (defaults to all species)
nano INPUT_user/selected_species.txt
```

**Run:**
```bash
bash RUN-workflow.sh
```

The unified driver runs locally or self-submits to SLURM based on
`execution_mode` in `START_HERE-user_config.yaml` (per §29). For SLURM,
also set `slurm_account` / `slurm_qos` in that YAML.

---

## Prerequisites

- **STEP_2** complete (provides cleaned proteomes and quality metrics)
- **STEP_3** complete (provides BLAST databases)
- **User evaluation** of STEP_2 quality metrics to decide species selection
- **Conda environment**: `aiG-genomesDB` with NextFlow installed

---

## Directory Structure

```
workflow-COPYME-create_final_species_set/
├── README.md                              # This file
├── RUN-workflow.sh        # Local runner (calls NextFlow)
├── START_HERE-user_config.yaml          # User-editable configuration
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
| Species with annotations | `1-output/1_ai-species_with_genome_annotations.txt` | Species that have GFF/GTF files |
| Final proteomes | `2-output/speciesN_gigantic_T1_proteomes/` | Copied proteome files |
| Final BLAST DBs | `2-output/speciesN_gigantic_T1_blastp/` | Copied BLAST database files |
| Genome annotations | `2-output/speciesN_gigantic_genome_annotations/` | Copied GFF/GTF files (subset) |
| Copy manifest | `2-output/2_ai-copy_manifest.tsv` | Record of all copied files |

---

## Final Outputs in output_to_input/

The workflow automatically creates symlinks in `../../output_to_input/STEP_4-create_final_species_set/`:
- `speciesN_gigantic_T1_proteomes/` - For downstream subprojects (orthohmm, etc.)
- `speciesN_gigantic_T1_blastp/` - For BLAST searches
- `speciesN_gigantic_genome_annotations/` - GFF/GTF files (subset with annotations)

Where N = count of selected species (e.g., species71)

---

## Next Step

After this workflow completes, downstream subprojects can access:
```
genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/
genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_blastp/
genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_genome_annotations/
```
