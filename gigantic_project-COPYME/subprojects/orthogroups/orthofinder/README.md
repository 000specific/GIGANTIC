# OrthoFinder - Ortholog Detection

**AI**: Claude Code | Opus 4.5 | 2026 February 26
**Human**: Eric Edsinger

---

## Purpose

Run OrthoFinder to identify orthologous gene groups across species using sequence similarity (all-vs-all Diamond/BLAST).

---

## Prerequisites

1. **genomesDB complete**: Proteomes available in `genomesDB/output_to_input/speciesN_gigantic_T1_proteomes/`
2. **Conda environment**: `ai_gigantic_orthogroups` (contains OrthoFinder, Diamond)

---

## Quick Start

```bash
# Copy workflow template to create a run instance
cp -r workflow-COPYME-run_orthofinder workflow-RUN_01-run_orthofinder
cd workflow-RUN_01-run_orthofinder/

# Add inputs (see INPUT_user/README.md)
# - Species tree in INPUT_user/
# - Proteomes directory in INPUT_user/

# Run locally (ensure conda environment is active)
module load conda  # HiPerGator only
conda activate ai_gigantic_orthogroups
bash RUN_orthofinder.sh

# Or run on SLURM (edit account/qos first)
sbatch SLURM_orthofinder.sbatch
```

---

## Outputs

| Output | Location | Description |
|--------|----------|-------------|
| Orthogroups | `OUTPUT_pipeline/Orthogroups/Orthogroups.txt` | Gene family assignments |
| Species tree | `OUTPUT_pipeline/Species_Tree/` | Inferred species tree |
| Statistics | `OUTPUT_pipeline/Comparative_Genomics_Statistics/` | Summary stats |

**Shared with downstream subprojects**: `output_to_input/Orthogroups/`

---

## Directory Structure

```
orthofinder/
├── README.md                          # This file
├── AI_GUIDE-orthofinder.md            # AI assistant guide
├── user_research/                     # Personal workspace
├── output_to_input/                   # Outputs for downstream
├── upload_to_server/                  # Server sharing
└── workflow-COPYME-run_orthofinder/   # Workflow template
    ├── RUN_orthofinder.sh             # Main workflow runner
    ├── SLURM_orthofinder.sbatch       # SLURM submission
    ├── INPUT_user/
    ├── OUTPUT_pipeline/
    └── ai/
```

---

## See Also

- `../AI_GUIDE-orthogroups.md` - Overview of orthogroup tools
- `../orthohmm/` - Alternative HMM-based ortholog detection
