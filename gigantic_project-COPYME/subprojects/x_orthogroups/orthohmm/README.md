# OrthoHMM - HMM-Based Ortholog Detection

**AI**: Claude Code | Opus 4.5 | 2026 February 26
**Human**: Eric Edsinger

---

## Purpose

Run OrthoHMM to identify orthologous gene groups using profile Hidden Markov Models (HMMs) for improved sensitivity with divergent sequences.

---

## Prerequisites

1. **genomesDB complete**: Proteomes available in `genomesDB/STEP_2.../output_to_input/gigantic_proteomes/`
2. **OrthoHMM installed**: Available via conda environment `ai_gigantic_orthogroups`

---

## Quick Start

```bash
cd workflow-COPYME-run_orthohmm/

# Edit config
nano orthohmm_config.yaml

# Copy proteomes to INPUT_user/
cp /path/to/proteomes/*.aa INPUT_user/

# Run locally
bash RUN-orthohmm.sh

# Or run on SLURM
sbatch RUN-orthohmm.sbatch
```

---

## Outputs

| Output | Location | Description |
|--------|----------|-------------|
| Orthogroups | `OUTPUT_pipeline/orthohmm_orthogroups.txt` | Gene family assignments |
| Gene counts | `OUTPUT_pipeline/orthohmm_gene_count.txt` | Counts per species |
| HMM profiles | `OUTPUT_pipeline/HMM_profiles/` | Profile HMMs for annotation |

**Shared with downstream subprojects**: `output_to_input/OrthoHMM/`

---

## Directory Structure

```
orthohmm/
├── README.md                       # This file
├── AI_GUIDE-orthohmm.md            # AI assistant guide
├── user_research/                  # Personal workspace
├── output_to_input/                # Outputs for downstream
├── upload_to_server/               # Server sharing
└── workflow-COPYME-run_orthohmm/   # Workflow template
    ├── RUN-orthohmm.sh
    ├── RUN-orthohmm.sbatch
    ├── orthohmm_config.yaml
    ├── INPUT_user/
    ├── OUTPUT_pipeline/
    └── ai/
```

---

## See Also

- `../AI_GUIDE-orthogroups.md` - Overview of orthogroup tools
- `../orthofinder/` - Alternative sequence-similarity based detection
