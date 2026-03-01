# orthogroups - Ortholog Group Identification

**AI**: Claude Code | Opus 4.6 | 2026 February 28
**Human**: Eric Edsinger

---

## Purpose

Identify orthologous gene groups (orthogroups) across species using three independent methods, then compare results. An orthogroup is a set of genes from different species that descended from a single gene in the last common ancestor.

---

## Architecture

Four equivalent, self-contained projects (mirroring genomesDB STEP pattern):

| Project | Tool | Method |
|---------|------|--------|
| `orthofinder/` | OrthoFinder | Diamond + MCL clustering |
| `orthohmm/` | OrthoHMM | Profile HMM (HMMER) + MCL |
| `broccoli/` | Broccoli | Phylogeny (FastTree) + network label propagation |
| `comparison/` | Cross-method | Compares results from all three tools |

Each tool project follows a common pipeline pattern: validate, prepare/convert, run tool, standardize/restore, statistics, QC. OrthoFinder uses 6 scripts (no header conversion needed, uses -X flag to preserve original identifiers). OrthoHMM and Broccoli each use 6 scripts (with header conversion and restoration). The comparison project uses 2 scripts.

---

## Prerequisites

1. **genomesDB complete**: Proteomes in `genomesDB/output_to_input/gigantic_proteomes/`
2. **Conda environment**: `ai_gigantic_orthogroups`
3. **Nextflow**: `module load nextflow`

---

## Quick Start

```bash
# 1. Copy a workflow template for your run
cp -r orthofinder/workflow-COPYME-run_orthofinder orthofinder/workflow-RUN_01-run_orthofinder
cd orthofinder/workflow-RUN_01-run_orthofinder/

# 2. Edit configuration
vi orthofinder_config.yaml

# 3. Activate environment
module load conda
conda activate ai_gigantic_orthogroups
module load nextflow

# 4. Run
bash RUN-workflow.sh       # Local
sbatch RUN-workflow.sbatch # SLURM (edit account/qos first)
```

Same pattern for orthohmm, broccoli, and comparison.

---

## Standardized Output

All three tools produce identical files in `output_to_input/`:

| File | Contents |
|------|----------|
| `orthogroups_gigantic_ids.tsv` | Orthogroup assignments with full GIGANTIC identifiers |
| `gene_count_gigantic_ids.tsv` | Gene counts per orthogroup per species |
| `summary_statistics.tsv` | Overall clustering statistics |
| `per_species_summary.tsv` | Per-species orthogroup statistics |

---

## Directory Structure

```
orthogroups/
├── README.md                            # This file
├── AI_GUIDE-orthogroups.md              # AI assistant guide (Level 2)
├── TODO.md
├── output_to_input/                     # Final outputs for downstream
├── upload_to_server/
├── RUN-clean_and_record_subproject.sh
├── RUN-update_upload_to_server.sh
│
├── orthofinder/                         # OrthoFinder project (6 scripts)
│   ├── AI_GUIDE-orthofinder.md
│   ├── output_to_input/
│   └── workflow-COPYME-run_orthofinder/
│       ├── ai/ (main.nf, nextflow.config, scripts/)
│       ├── RUN-workflow.sh
│       ├── RUN-workflow.sbatch
│       └── orthofinder_config.yaml
│
├── orthohmm/                            # OrthoHMM project (6 scripts)
│   ├── AI_GUIDE-orthohmm.md
│   ├── output_to_input/
│   └── workflow-COPYME-run_orthohmm/
│       ├── ai/ (main.nf, nextflow.config, scripts/)
│       ├── RUN-workflow.sh
│       ├── RUN-workflow.sbatch
│       └── orthohmm_config.yaml
│
├── broccoli/                            # Broccoli project (6 scripts)
│   ├── AI_GUIDE-broccoli.md
│   ├── output_to_input/
│   └── workflow-COPYME-run_broccoli/
│       ├── ai/ (main.nf, nextflow.config, scripts/)
│       ├── RUN-workflow.sh
│       ├── RUN-workflow.sbatch
│       └── broccoli_config.yaml
│
└── comparison/                          # Cross-method comparison (2 scripts)
    ├── AI_GUIDE-comparison.md
    ├── output_to_input/
    └── workflow-COPYME-compare_methods/
        ├── ai/ (main.nf, nextflow.config, scripts/)
        ├── RUN-workflow.sh
        ├── RUN-workflow.sbatch
        └── comparison_config.yaml
```

---

## See Also

- `AI_GUIDE-orthogroups.md` - AI assistant guidance
- `{tool}/AI_GUIDE-{tool}.md` - Tool-specific AI guides
- `TODO.md` - Open items and tracking
