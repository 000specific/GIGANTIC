# annotations_X_ocl

Origin-Conservation-Loss (OCL) analysis of annotation groups across species tree topologies.

## What This Subproject Does

Groups proteins by their annotation patterns from a specific database into "annogroups,"
then traces these annotation patterns across species tree phylogenetic features to determine:

1. **Origin**: The most recent common ancestor (MRCA) clade where each annotation pattern first appeared
2. **Conservation**: Tracking which phylogenetic blocks retain the annotation pattern
3. **Loss**: Distinguishing first-loss events ("loss at origin") from downstream absences
   ("continued absence") using TEMPLATE_03 dual-metric tracking

Works with **all 24 annotation databases** from `annotations_hmms`. Each database exploration
is a separate COPYME copy with its own `run_label`.

## Terminology

- **Annogroup**: A set of proteins that share the same annotation pattern from a specific
  database. The annotation analog to orthogroups. ID format: `annogroup_{db}_N` where `{db}`
  is the database name and `N` is a sequential integer.

- **Annogroup map**: The lookup table (`1_ai-annogroup_map.tsv`) linking every annogroup ID
  to its full details: subtype, accessions, species, sequences. This is the Rosetta Stone
  for all downstream analysis.

- **Annogroup subtypes**: Three ways a protein can relate to an annotation database:
  - `single` - exactly one annotation hit, grouped by accession
  - `combo` - identical multi-annotation architecture, grouped by accession set
  - `zero` - no annotation hits (singleton annogroups)

- **Phylogenetic block**: A single parent-to-child transition on a given phylogenetic tree.
  Format: `Parent::Child` (e.g., `Metazoa::Bilateria`). The computational unit for
  tracking origins, conservation, and loss.

- **Phylogenetic path**: The path on a given phylogenetic tree from a node to the root.
  Example: `Homo_sapiens > Hominidae > Primates > ... > Basal`

These are exclusively "phylogenetic" (model-derived from tree topologies), not "evolutionary"
(which refers to actual biological history).

## Design: COPYME for Multi-Database Exploration

The OCL algorithm is database-agnostic - the same pipeline works regardless of which
annotation database produced the input. Each exploration (database + structure selection)
is a separate COPYME copy:
- `workflow-RUN_01-ocl_analysis/` with run_label "Species71_pfam"
- `workflow-RUN_02-ocl_analysis/` with run_label "Species71_gene3d"
- `workflow-RUN_03-ocl_analysis/` with run_label "Species71_deeploc"

Different explorations coexist in output_to_input via run_label-based subdirectories.

## Fail-Fast Validation

Script 005 validates all results with 8 checks and strict fail-fast behavior: ANY validation
failure causes exit code 1 and stops the pipeline. Check 8 is annotation-specific, verifying
annogroup subtype consistency, no duplicate IDs, and ID format compliance. Edge cases
(division by zero for zero-transition annogroups, floating-point rounding) are handled
explicitly in Scripts 003-004 so they never produce invalid metrics.

## Directory Structure

```
annotations_X_ocl/
├── README.md                              # THIS FILE
├── AI_GUIDE-annotations_X_ocl.md          # AI guidance
├── RUN-clean_and_record_subproject.sh
│
├── output_to_input/
│   └── BLOCK_ocl_analysis/                # Populated by RUN-workflow.sh symlinks
│       ├── Species71_pfam/                # run_label from RUN_01
│       │   ├── structure_001/
│       │   └── ...
│       ├── Species71_gene3d/              # run_label from RUN_02
│       └── Species71_deeploc/             # run_label from RUN_03
│
├── upload_to_server/
├── research_notebook/ai_research/
│
└── BLOCK_ocl_analysis/
    ├── AI_GUIDE-ocl_analysis.md
    └── workflow-COPYME-ocl_analysis/
        ├── START_HERE-user_config.yaml
        ├── RUN-workflow.sh
        ├── RUN-workflow.sbatch
        ├── INPUT_user/                    # structure_manifest.tsv
        ├── OUTPUT_pipeline/               # Results per structure
        └── ai/
            ├── main.nf
            ├── nextflow.config
            └── scripts/                   # 5 Python scripts
```

## Dependencies

### annotations_X_ocl reads FROM:
- `trees_species/output_to_input/BLOCK_permutations_and_features/` - Phylogenetic blocks,
  paths, parent-child relationships, clade-species mappings
- `annotations_hmms/output_to_input/BLOCK_build_annotation_database/annotation_databases/database_{name}/` -
  Per-species annotation files (7-column TSV format)

### annotations_X_ocl provides TO:
- Cross-database comparison and integration analyses
- Integration with orthogroups_X_ocl for combined functional/orthology views
- upload_to_server for GIGANTIC server
