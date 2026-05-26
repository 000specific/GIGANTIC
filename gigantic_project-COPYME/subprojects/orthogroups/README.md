# orthogroups - Ortholog Group Identification

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 February 28 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

`orthogroups` runs after `genomesDB STEP_4` produces the final species
proteomes. Each BLOCK runs an independent orthogroup-discovery tool;
their standardized outputs feed `orthogroups_X_ocl` and other
downstream OCL-flavored analyses.

- Parent project landing page: [`../../README.md`](../../README.md)
- Parent project AI guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md)
- This subproject's AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)
- Prerequisite: [`../genomesDB/STEP_4-create_final_species_set/`](../genomesDB/STEP_4-create_final_species_set/) — provides standardized proteomes
- Prerequisite (naming): [`../phylonames/`](../phylonames/)

---

## Purpose

Identify orthologous gene groups (orthogroups) across species using multiple independent methods, then compare results. An orthogroup is a set of genes from different species that descended from a single gene in the last common ancestor.

---

## Architecture

Six BLOCKs — three tools × {standard, array} for the search-based tools, plus Broccoli and a cross-method comparison:

| BLOCK | Tool | Method | When to use |
|---|---|---|---|
| `BLOCK_orthofinder/` | OrthoFinder | Diamond + MCL clustering | Standard; small species sets (< ~20) |
| `BLOCK_orthofinder_array/` | OrthoFinder | DIAMOND fan-out via SLURM job array | ≥ 30 species; bit-identical results, parallelized search |
| `BLOCK_orthohmm/` | OrthoHMM | Profile HMM (HMMER) + MCL | Standard; small species sets |
| `BLOCK_orthohmm_GIGANTIC/` | OrthoHMM | phmmer fan-out via SLURM job array | ≥ 30 species; bit-identical results, parallelized search |
| `BLOCK_broccoli/` | Broccoli | Phylogeny (FastTree) + network label propagation | Gene-fusion detection, phylogeny-aware |
| `BLOCK_comparison/` | Cross-method | Compares results from all tool BLOCKs | After ≥ 2 tool BLOCKs complete |

Each tool BLOCK follows a common pipeline pattern: validate, prepare/convert, run tool, standardize/restore, statistics, QC, audit log. Script counts (each includes a final `write_run_log` script per §45):

- **BLOCK_orthofinder**: 7 scripts (no header conversion — uses `-X` flag to preserve original identifiers)
- **BLOCK_orthofinder_array**: 9 scripts (adds extract-commands + pool-and-verify for parallel DIAMOND fan-out)
- **BLOCK_orthohmm**: 7 scripts (with header conversion + restoration)
- **BLOCK_orthohmm_GIGANTIC**: 9 scripts (adds extract-commands + pool-and-verify for parallel phmmer fan-out)
- **BLOCK_broccoli**: 7 scripts (with header conversion + restoration)
- **BLOCK_comparison**: 3 scripts (compare + visualize + write_run_log)

---

## Prerequisites

1. **genomesDB STEP_4 complete**: Standardized proteomes in `../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
2. **Conda environments** (per-BLOCK, auto-created on first run): `aiG-orthogroups-orthofinder`, `aiG-orthogroups-orthohmm`, `aiG-orthogroups-broccoli`, `aiG-orthogroups-comparison`. Each BLOCK's `ai/conda_environment.yml` carries its tool dependencies.
3. **NextFlow**: provided by each BLOCK's conda env

---

## Quick Start

```bash
# 1. Copy a workflow template for your run
cp -r BLOCK_orthofinder/workflow-COPYME-run_orthofinder BLOCK_orthofinder/workflow-RUN_01-run_orthofinder
cd BLOCK_orthofinder/workflow-RUN_01-run_orthofinder/

# 2. Edit configuration (project name, paths, execution_mode, slurm_account/qos)
vi START_HERE-user_config.yaml

# 3. Run — unified §29 driver: local or self-submits to SLURM via execution_mode YAML key
bash RUN-workflow.sh
```

Same pattern for BLOCK_orthohmm, BLOCK_orthofinder_array, BLOCK_orthohmm_GIGANTIC, BLOCK_broccoli, and BLOCK_comparison.

**Note:** `RUN-workflow.sh` auto-creates the per-BLOCK conda env on first run from `ai/conda_environment.yml`. No manual activation required.

---

## Standardized Output

All tool BLOCKs produce identical files in `output_to_input/BLOCK_*/`:

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
├── AI_GUIDE.md                          # AI assistant guide (subproject level)
├── TODO.md                              # Open items + tracking
├── RUN-update_upload_to_server.sh       # Subproject-level publisher (§38)
├── upload_to_server/                    # Single publish destination per §38
│   (no per-subproject research_notebook/ — single project-root sandbox at
│   gigantic_project-COPYME/research_notebook/ per §1, §9, §25)
│
├── output_to_input/                     # Per-BLOCK outputs for downstream consumers (§2, §38)
│   ├── BLOCK_orthofinder/               # OrthoFinder standardized outputs
│   ├── BLOCK_orthofinder_array/         # OrthoFinder (array variant) standardized outputs
│   ├── BLOCK_orthohmm/                  # OrthoHMM standardized outputs
│   ├── BLOCK_orthohmm_GIGANTIC/         # OrthoHMM (array variant) standardized outputs
│   ├── BLOCK_broccoli/                  # Broccoli standardized outputs
│   └── BLOCK_comparison/                # Comparison outputs
│
├── BLOCK_orthofinder/                   # OrthoFinder standard (7 scripts)
│   ├── AI_GUIDE.md
│   └── workflow-COPYME-run_orthofinder/
│       ├── README.md
│       ├── RUN-workflow.sh              # Unified driver (§29; local or SLURM via execution_mode)
│       ├── START_HERE-user_config.yaml
│       └── ai/                          # main.nf, nextflow.config, conda_environment.yml, AI_GUIDE.md, scripts/
│
├── BLOCK_orthofinder_array/             # OrthoFinder DIAMOND fan-out (9 scripts; ≥30 species)
│   ├── AI_GUIDE.md
│   └── workflow-COPYME-run_orthofinder_array/
│       ├── README.md
│       ├── RUN-workflow.sh
│       ├── START_HERE-user_config.yaml
│       └── ai/
│
├── BLOCK_orthohmm/                      # OrthoHMM standard (7 scripts)
│   ├── AI_GUIDE.md
│   └── workflow-COPYME-run_orthohmm/
│       ├── README.md
│       ├── RUN-workflow.sh
│       ├── START_HERE-user_config.yaml
│       └── ai/
│
├── BLOCK_orthohmm_GIGANTIC/             # OrthoHMM phmmer fan-out (9 scripts; ≥30 species)
│   ├── AI_GUIDE.md
│   └── workflow-COPYME-run_orthohmm_GIGANTIC/
│       ├── README.md
│       ├── RUN-workflow.sh
│       ├── START_HERE-user_config.yaml
│       └── ai/
│
├── BLOCK_broccoli/                      # Broccoli (7 scripts)
│   ├── AI_GUIDE.md
│   └── workflow-COPYME-run_broccoli/
│       ├── README.md
│       ├── RUN-workflow.sh
│       ├── START_HERE-user_config.yaml
│       └── ai/
│
└── BLOCK_comparison/                    # Cross-method comparison (3 scripts; runs after ≥2 tool BLOCKs)
    ├── AI_GUIDE.md
    └── workflow-COPYME-compare_methods/
        ├── README.md
        ├── RUN-workflow.sh
        ├── START_HERE-user_config.yaml
        └── ai/
```

---

## Outputs Shared Downstream (`output_to_input/`)

Per §38 + §2, downstream subprojects read from the per-BLOCK
subdirectories under `output_to_input/`. **Downstream consumers (per §40)**:

- **orthogroups_X_ocl** — reads any tool BLOCK's standardized orthogroups
  table to compute orthogroup-level OCL inferences across species tree
  structures
- **gene_sizes**, **dark_proteomes**, **hotspots**, **secretome**,
  **one_direction_homologs** — orthogroup-aware analyses can use
  any tool BLOCK's output
- **occams_tree** (planned) — cross-structure aggregation

---

## See Also

- `AI_GUIDE.md` — AI assistant guidance (subproject level)
- `BLOCK_<tool>/AI_GUIDE.md` — Per-BLOCK AI guides
- `TODO.md` — Open items and tracking
