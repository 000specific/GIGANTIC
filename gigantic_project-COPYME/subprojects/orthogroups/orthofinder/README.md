# OrthoFinder - Ortholog Detection

**AI**: Claude Code | Opus 4.5 | 2026 February 26
**Human**: Eric Edsinger

---

## Purpose

Run OrthoFinder to identify orthologous gene groups across species using sequence similarity (all-vs-all Diamond/BLAST).

---

## Prerequisites

1. **genomesDB complete**: Proteomes available in `genomesDB/STEP_2.../output_to_input/gigantic_proteomes/`
2. **OrthoFinder installed**: Available via conda environment `ai_gigantic_orthogroups`

---

## Quick Start

```bash
cd workflow-COPYME-run_orthofinder/

# Edit config
nano orthofinder_config.yaml

# Copy proteomes to INPUT_user/
cp /path/to/proteomes/*.aa INPUT_user/

# Run locally
bash RUN-orthofinder.sh

# Or run on SLURM
sbatch RUN-orthofinder.sbatch
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
    ├── RUN-orthofinder.sh
    ├── RUN-orthofinder.sbatch
    ├── orthofinder_config.yaml
    ├── INPUT_user/
    ├── OUTPUT_pipeline/
    └── ai/
```

---

## See Also

- `../AI_GUIDE-orthogroups.md` - Overview of orthogroup tools
- `../orthohmm/` - Alternative HMM-based ortholog detection
