# orthogroups_X_ocl

Origin-Conservation-Loss (OCL) analysis of orthogroups across species tree topologies.

## What This Subproject Does

Integrates orthogroup clustering results with species tree phylogenetic features to determine:

1. **Origin**: The most recent common ancestor (MRCA) clade where each orthogroup first appeared
2. **Conservation**: Tracking which phylogenetic blocks retain the orthogroup
3. **Loss**: Distinguishing first-loss events ("loss at origin") from downstream absences
   ("continued absence") using TEMPLATE_03 dual-metric tracking

Processes all orthogroups across user-selected species tree topologies in parallel.

## Terminology

- **Phylogenetic block**: A single parent-to-child transition on a given phylogenetic tree.
  Format: `Parent::Child` (e.g., `Metazoa::Bilateria`). The computational unit for
  tracking origins, conservation, and loss.

- **Phylogenetic path**: The path on a given phylogenetic tree from a node to the root.
  Example: `Homo_sapiens > Hominidae > Primates > ... > Basal`

These are exclusively "phylogenetic" (model-derived from tree topologies), not "evolutionary"
(which refers to actual biological history).

## Design: COPYME for Multi-Tool Exploration

The OCL algorithm is tool-agnostic - the same pipeline works regardless of which
orthogroup clustering tool (OrthoFinder, OrthoHMM, Broccoli) produced the input.

Each exploration (tool + structure selection) is a separate COPYME copy:
- `workflow-RUN_01-ocl_analysis/` with run_label "Species71_X_OrthoFinder"
- `workflow-RUN_02-ocl_analysis/` with run_label "Species71_X_OrthoHMM"

Different explorations coexist in output_to_input via run_label-based subdirectories.

## Fail-Fast Validation

Script 005 validates all results with strict fail-fast behavior: ANY validation failure
causes exit code 1 and stops the pipeline. Edge cases (division by zero for zero-transition
orthogroups, floating-point rounding) are handled explicitly in Scripts 003-004 so they
never produce invalid metrics that validation would flag.

## Directory Structure

```
orthogroups_X_ocl/
├── README.md                              # THIS FILE
├── AI_GUIDE-orthogroups_X_ocl.md          # AI guidance
├── RUN-clean_and_record_subproject.sh
│
├── output_to_input/
│   └── BLOCK_ocl_analysis/                # Populated by RUN-workflow.sh symlinks
│       ├── Species71_X_OrthoFinder/       # run_label from RUN_01
│       │   ├── structure_001/
│       │   └── ...
│       └── Species71_X_OrthoHMM/          # run_label from RUN_02
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

### orthogroups_X_ocl reads FROM:
- `trees_species/output_to_input/BLOCK_permutations_and_features/` - Phylogenetic blocks,
  paths, parent-child relationships, clade-species mappings
- `orthogroups/output_to_input/BLOCK_orthofinder/` (or BLOCK_orthohmm, BLOCK_broccoli) -
  Orthogroup assignments in GIGANTIC identifiers
- `genomesDB/output_to_input/STEP_4-.../` - Proteome FASTA files

### orthogroups_X_ocl provides TO:
- Downstream analysis and visualization subprojects
- upload_to_server for GIGANTIC server
