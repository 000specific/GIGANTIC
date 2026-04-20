# annotations_X_ocl

Origin-Conservation-Loss (OCL) analysis of annotation groups (annogroups) across species tree topologies.

## What This Subproject Does

Integrates per-species annotation data with species tree phylogenetic features to determine:

1. **Origin**: The most recent common ancestor (MRCA) clade where each annogroup first appeared
2. **Conservation**: Tracking which phylogenetic blocks retain the annogroup
3. **Loss**: Distinguishing first-loss events from downstream absences using the five-state block-state vocabulary (A/O/P/L/X)

Annogroups are the annotation analog to orthogroups -- sets of proteins grouped by their annotation pattern from a specific database. Each annogroup has a simple ID (`annogroup_{db}_N`) with full details in a companion map. The three annogroup subtypes are:

- **single**: proteins with exactly one annotation from the database
- **combo**: proteins with identical multi-annotation architecture
- **zero**: proteins with no annotations from the database

Processes all annogroups across user-selected species tree topologies in parallel.

## Terminology

- **Phylogenetic block**: A single parent-to-child edge of a species tree
  structure -- the parent clade, the child clade, and the edge joining them,
  with no intervening nodes. Written `parent_clade_id_name::child_clade_id_name`
  (e.g. `C069_Holozoa::C082_Metazoa`). Feature-agnostic: the block is a
  structural fact about the tree, independent of any annogroup. This is the
  computational atom on which OCL origins, conservation, and losses are
  resolved.

- **Phylogenetic block-state**: A phylogenetic block paired with a specific
  annogroup's state on that block, written
  `parent_clade_id_name::child_clade_id_name-LETTER` (e.g.
  `C069_Holozoa::C082_Metazoa-O`). The LETTER is one of five codes refining
  classical Dollo: **A** Inherited Absence (pre-origin), **O** Origin,
  **P** Inherited Presence (conservation), **L** Loss, **X** Inherited Loss
  (post-loss). Event blocks carry state O or L (evolutionary change);
  inheritance blocks carry state A, P, or X (state persists across the block).

- **Phylogenetic path**: The path on a given phylogenetic species tree from
  `C000_OOL` (Origin Of Life) down to a species leaf.

- **Phylogenetic path-state**: A path paired with a specific annogroup's state
  along each block of the path, written as concatenated five-state letters in
  OOL-end-to-species-end order (e.g. `AAAOPLXX`). The compact fingerprint of
  an annogroup's inferred evolutionary history along one species's lineage.

- **Clade ID (`clade_id_name`)**: identifies a **topologically-structured
  species set** -- a unique combination of descendant species and their
  branching arrangement. Produced upstream by
  `trees_species/BLOCK_permutations_and_features/`. Same biological clade
  receives the same `clade_id_name` across every candidate species tree
  structure. Used as the canonical atomic identifier throughout this subproject
  (never split into `clade_id` and `clade_name` for lookups).

For full canonical definitions of Rules 1-7, see `../../AI_GUIDE-project.md`.

## Design: COPYME for Multi-Database Exploration

The OCL algorithm is database-agnostic -- the same pipeline works regardless of which
annotation database (pfam, gene3d, deeploc, signalp, tmbed, metapredict) produced the input.

Each exploration (database + structure selection) is a separate COPYME copy:
- `workflow-RUN_01-ocl_analysis/` with run_label "species70_pfam"
- `workflow-RUN_02-ocl_analysis/` with run_label "species70_gene3d"

Different explorations coexist in output_to_input via run_label-based subdirectories.

### Database-Specific Subtype Defaults

| Database Category | Databases | Subtypes |
|---|---|---|
| Domain databases | pfam, gene3d, superfamily, smart, cdd, prosite_profiles | single, combo, zero |
| Simple databases | deeploc, signalp, tmbed, metapredict | single only |

## Running the Workflow

Single entry point -- `bash RUN-workflow.sh`. Execution location is controlled
by `execution_mode` in `START_HERE-user_config.yaml`:

- `execution_mode: "local"` -> runs on the current machine
- `execution_mode: "slurm"` -> self-submits to SLURM with cpus/memory/time/account/qos from the same yaml

The conda environment (`aiG-annotations_X_ocl-ocl_analysis`) is created on-demand
from `ai/conda_environment.yml` on first run -- no separate install step needed.

## Fail-Fast Validation

Script 005 validates all results with strict fail-fast behavior: ANY validation failure
causes exit code 1 and stops the pipeline. Edge cases (division by zero for zero-transition
annogroups) are handled explicitly in Scripts 003-004 so they never produce invalid metrics
that validation would flag.

## Directory Structure

```
annotations_X_ocl/
├── README.md                              # THIS FILE
├── AI_GUIDE-annotations_X_ocl.md          # AI guidance
├── RUN-clean_and_record_subproject.sh
│
├── output_to_input/
│   └── BLOCK_ocl_analysis/               # Populated by RUN-workflow.sh symlinks
│       ├── species70_pfam/                # run_label from RUN_01
│       │   ├── structure_001/
│       │   └── ...
│       └── species70_gene3d/              # run_label from RUN_02
│
├── upload_to_server/
├── research_notebook/ai_research/
│
└── BLOCK_ocl_analysis/
    ├── AI_GUIDE-ocl_analysis.md
    └── workflow-COPYME-ocl_analysis/
        ├── START_HERE-user_config.yaml
        ├── RUN-workflow.sh                # Self-submits to SLURM if execution_mode=slurm
        ├── INPUT_user/                    # structure_manifest.tsv
        ├── OUTPUT_pipeline/               # Results per structure
        └── ai/
            ├── conda_environment.yml      # Per-BLOCK env (on-demand create)
            ├── main.nf
            ├── nextflow.config
            └── scripts/                   # 6 Python scripts (001-006)
```

## Dependencies

### annotations_X_ocl reads FROM:
- `trees_species/output_to_input/BLOCK_permutations_and_features/` - Phylogenetic blocks,
  paths, parent-child relationships, clade-species mappings
- `annotations_hmms/output_to_input/BLOCK_build_annotation_database/` - Per-species
  annotation files (7-column TSV per species per database)

### annotations_X_ocl provides TO:
- Integration with orthogroups_X_ocl for combined functional/orthology views
- Cross-database comparison analyses
- upload_to_server for GIGANTIC server
