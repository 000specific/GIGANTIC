# STEP_4-create_final_species_set — Assemble the Final speciesN Set

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 February 28 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent subproject: [`../README.md`](../README.md) — genomesDB overview
- Parent project: [`../../../README.md`](../../../README.md)
- This STEP's AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)
- Workflow to run: [`workflow-COPYME-create_final_species_set/README.md`](workflow-COPYME-create_final_species_set/README.md)
- Reads from: [`../STEP_2-standardize_and_evaluate/`](../STEP_2-standardize_and_evaluate/) (cleaned proteomes + annotations)
  + [`../STEP_3-databases/`](../STEP_3-databases/) (BLAST databases)
- **This is the last STEP in genomesDB.** Output `speciesN_*` directories
  feed into every downstream subproject — `orthogroups`, `annotations_hmms`,
  `trees_species`, `trees_gene_families`, `trees_gene_groups`, etc.

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
4. Script 002 copies selected proteomes and BLAST databases (→ `2-output/`)
5. Script 003 builds per-species (id + sequence) TSV tables from the proteomes (→ `3-output/speciesN_gigantic_T1_sequence_tables/`)
6. Script 004 writes the run log
7. Final outputs are exposed via `output_to_input/` with `speciesN_` naming convention

---

## Quick Start

```bash
# 1. Copy workflow template
cp -r workflow-COPYME-create_final_species_set workflow-RUN_01-create_final_species_set
cd workflow-RUN_01-create_final_species_set

# 2. Edit configuration with paths to STEP_2 and STEP_3 outputs
nano START_HERE-user_config.yaml

# 3. Optional: edit species selection (defaults to all species)
nano INPUT_user/selected_species.txt

# 4. Run (unified driver — local or SLURM via execution_mode YAML key, §29)
bash RUN-workflow.sh
```

---

## Inputs

| Source | Data | Location |
|--------|------|----------|
| STEP_2 | Cleaned proteomes | Configured in `START_HERE-user_config.yaml` |
| STEP_3 | BLAST databases | Configured in `START_HERE-user_config.yaml` |
| User | Species selection (optional) | `INPUT_user/selected_species.txt` |

---

## Outputs

| Output | Location | Description |
|--------|----------|-------------|
| Final proteomes | `../../output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/` | For downstream subprojects |
| Final BLAST DBs | `../../output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_blastp/` | For BLAST searches |
| Genome annotations | `../../output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_genome_annotations/` | GFF/GTF files (subset) |
| Sequence tables | `../../output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_sequence_tables/` | Per-species TSV: Phyloname, Gigantic_Protein_Identifier, Sequence_Length, Protein_Sequence |

Where N = count of selected species (e.g., species71).

---

## Dependencies

- **STEP_2-standardize_and_evaluate** must complete first (provides cleaned proteomes)
- **STEP_3-databases** must complete first (provides BLAST databases)
- **Conda environment**: `aiG-genomesDB` with NextFlow installed

---

## Research Notebook

Workflow run logs are saved to each workflow's `ai/logs/` directory. AI sessions are extracted project-wide to `research_notebook/research_ai/sessions/`.

---

## Directory Structure

```
STEP_4-create_final_species_set/
├── README.md                              # This file
├── AI_GUIDE.md   # Guide for AI assistants
├── RUN-update_upload_to_server.sh         # Manage upload_to_server/ symlinks
├── output_to_input/                       # Final species set for downstream subprojects
├── upload_to_server/                      # Curated data for GIGANTIC server
└── workflow-COPYME-create_final_species_set/
    ├── README.md
    ├── RUN-workflow.sh
    ├── START_HERE-user_config.yaml
    ├── INPUT_user/
    │   └── selected_species.txt           # Species selection (optional)
    └── ai/
        ├── AI_GUIDE.md
        ├── main.nf
        ├── nextflow.config
        └── scripts/
            ├── 001_ai-python-validate_species_selection.py
            ├── 002_ai-python-copy_selected_files.py
            ├── 003_ai-python-build_per_species_sequence_tables.py
            └── 004_ai-python-write_run_log.py
```
