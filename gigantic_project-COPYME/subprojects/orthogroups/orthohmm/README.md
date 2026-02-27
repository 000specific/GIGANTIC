# OrthoHMM - HMM-Based Ortholog Detection

**AI**: Claude Code | Opus 4.5 | 2026 February 27
**Human**: Eric Edsinger

---

## Purpose

Run OrthoHMM to identify orthologous gene groups using profile Hidden Markov Models (HMMs) for improved sensitivity with divergent sequences.

---

## Prerequisites

1. **genomesDB complete**: Proteomes available in `genomesDB/STEP_2.../output_to_input/gigantic_proteomes/`
2. **Conda environment**: `ai_gigantic_orthogroups` (contains OrthoHMM, HMMER, MCL)

---

## Quick Start

```bash
# Copy workflow template to create a run instance
cp -r workflow-COPYME-run_orthohmm workflow-RUN_01-run_orthohmm
cd workflow-RUN_01-run_orthohmm/

# Run locally (ensure conda environment is active)
module load conda  # HiPerGator only
conda activate ai_gigantic_orthogroups
bash RUN-workflow.sh

# Or run on SLURM (edit account/qos first)
nano RUN-workflow.sbatch  # Edit SBATCH headers
sbatch RUN-workflow.sbatch
```

---

## Workflow Scripts

The workflow runs six scripts in sequence:

| Script | Description |
|--------|-------------|
| 001 | Validate and list proteomes from genomesDB |
| 002 | Convert FASTA headers to short IDs (OrthoHMM requirement) |
| 003 | Run OrthoHMM clustering |
| 004 | Generate summary statistics |
| 005 | Per-species QC analysis |
| 006 | Restore full GIGANTIC identifiers |

---

## Outputs

| Output | Location | Description |
|--------|----------|-------------|
| Proteome list | `OUTPUT_pipeline/1-output/` | Validated proteome inventory |
| Header mapping | `OUTPUT_pipeline/2-output/` | Short ID to GIGANTIC ID mapping |
| OrthoHMM results | `OUTPUT_pipeline/3-output/` | Raw clustering output |
| Statistics | `OUTPUT_pipeline/4-output/` | Summary and size distributions |
| QC per species | `OUTPUT_pipeline/5-output/` | Per-species coverage |
| GIGANTIC IDs | `OUTPUT_pipeline/6-output/` | Results with full identifiers |

**Shared with downstream subprojects**: `output_to_input/`

---

## Directory Structure

```
orthohmm/
├── README.md                       # This file
├── AI_GUIDE-orthohmm.md            # AI assistant guide
├── user_research/                  # Personal workspace
├── output_to_input/                # Outputs for downstream
└── workflow-COPYME-run_orthohmm/   # Workflow template
    ├── RUN-workflow.sh             # Main workflow runner
    ├── RUN-workflow.sbatch         # SLURM submission
    ├── OUTPUT_pipeline/            # Results directory
    └── ai/
        └── scripts/                # Processing scripts
            ├── 001_ai-python-validate_and_list_proteomes.py
            ├── 002_ai-python-convert_headers_to_short_ids.py
            ├── 003_ai-bash-run_orthohmm.sh
            ├── 004_ai-python-generate_summary_statistics.py
            ├── 005_ai-python-qc_analysis_per_species.py
            └── 006_ai-python-restore_gigantic_identifiers.py
```

---

## See Also

- `../AI_GUIDE-orthogroups.md` - Overview of orthogroup tools
- `../orthofinder/` - Alternative sequence-similarity based detection
- `../broccoli/` - Fast phylogeny-aware orthogroup inference
