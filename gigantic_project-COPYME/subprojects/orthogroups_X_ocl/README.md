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

- **Phylogenetic block**: A single parent-to-child edge of a species tree
  structure — the parent clade, the child clade, and the edge joining them,
  with no intervening nodes. Written `parent_clade_id_name::child_clade_id_name`
  (e.g. `C069_Holozoa::C082_Metazoa`). Feature-agnostic: the block is a
  structural fact about the tree, independent of any orthogroup. This is the
  computational atom on which OCL origins, conservation, and losses are
  resolved.

- **Phylogenetic block-state**: A phylogenetic block paired with a specific
  orthogroup's state on that block, written
  `parent_clade_id_name::child_clade_id_name-LETTER` (e.g.
  `C069_Holozoa::C082_Metazoa-O`). The LETTER is one of five codes refining
  classical Dollo: **A** Inherited Absence (pre-origin), **O** Origin,
  **P** Inherited Presence (conservation), **L** Loss, **X** Inherited Loss
  (post-loss). Event blocks carry state O or L (evolutionary change);
  inheritance blocks carry state A, P, or X (state persists across the block).

- **Phylogenetic path**: The path on a given phylogenetic species tree from a
  node to the root. Example: `Homo_sapiens > Hominidae > Primates > ... >
  Basal`

- **Clade ID (`clade_id_name`)**: identifies a **topologically-structured
  species set** — a unique combination of descendant species and their
  branching arrangement. Produced upstream by
  `trees_species/BLOCK_permutations_and_features/`. Same biological clade
  receives the same `clade_id_name` across every candidate species tree
  structure it appears in — so OCL can treat it as a stable key when
  reasoning across structures. Used as the canonical atomic identifier
  throughout this subproject (never split into `clade_id` and `clade_name`
  for lookups).

For full canonical definitions of `phylogenetic` vs `evolutionary`, structure
vs topology, the resolved-vs-unresolved input species tree distinction, the
species-tree-vs-gene-tree explicitness rule, the topologically-structured
species sets rule for clade IDs, and the phylogenetic block / block-state
five-state vocabulary, see `../trees_species/README.md` (Terminology section)
and Rules 1-7 of `../../AI_GUIDE-project.md`. The complete specification of
blocks, block-states, and the five-state vocabulary is in
`research_notebook/ai_research/planning-phylogenetic_blocks_and_locks/whitepaper.md`.

## Design: COPYME for Multi-Tool Exploration

The OCL algorithm is tool-agnostic - the same pipeline works regardless of which
orthogroup clustering tool (OrthoFinder, OrthoHMM, Broccoli) produced the input.

Each exploration (tool + structure selection) is a separate COPYME copy:
- `workflow-RUN_01-ocl_analysis/` with run_label "species70_X_OrthoHMM"
- `workflow-RUN_02-ocl_analysis/` with run_label "species70_X_OrthoFinder"

Different explorations coexist in output_to_input via run_label-based subdirectories.

## Running the Workflow

Single entry point — `bash RUN-workflow.sh`. Execution location is controlled
by `execution_mode` in `START_HERE-user_config.yaml`:

- `execution_mode: "local"` → runs on the current machine
- `execution_mode: "slurm"` → self-submits to SLURM with cpus/memory/time/account/qos from the same yaml

**CPU/memory sizing (for parallel runs):** OCL parallelizes naturally across tree
structures. For a run covering `N` structures (e.g., 105 for species70 with 5
unresolved clades), request `cpus: N + 1` and match memory to HiPerGator's
standard 7.5 GB per CPU ratio (so `memory_gb: (N + 1) × 7.5`). For 105 structures
that is `cpus: 106, memory_gb: 795`. See the "CPU and Memory Configuration"
section of `../../AI_GUIDE-project.md` for the full rationale and non-HiPerGator
adjustments.

The conda environment (`aiG-orthogroups_X_ocl-ocl_analysis`) is created on-demand
from `ai/conda_environment.yml` on first run — no separate install step needed.

## Fail-Fast Validation

Script 005 validates all results with strict fail-fast behavior: ANY validation failure
causes exit code 1 and stops the pipeline. Edge cases (division by zero for zero-transition
orthogroups, floating-point rounding) are handled explicitly in Scripts 003-004 so they
never produce invalid metrics that validation would flag.

## Planned STEP_2: Tree Structure Ranking

`STEP_2-occams_tree/` (planned) will aggregate STEP_1's
per-structure OCL summaries across all topology permutations and rank candidate
species trees by total-loss minimization. Since trees_species always assigns
`structure_001` to the user-provided species tree, STEP_2's ranking directly
reports how the user's input tree compares to alternative topologies under an
Occam's-razor (fewest-losses) criterion.

## Directory Structure

```
orthogroups_X_ocl/
├── README.md                              # THIS FILE
├── AI_GUIDE-orthogroups_X_ocl.md          # AI guidance
├── RUN-clean_and_record_subproject.sh
│
├── output_to_input/
│   └── BLOCK_ocl_analysis/               # Populated by RUN-workflow.sh symlinks
│       ├── species70_X_OrthoHMM/          # run_label from RUN_01
│       │   ├── structure_001/
│       │   └── ...
│       └── species70_X_OrthoFinder/       # run_label from RUN_02
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

### orthogroups_X_ocl reads FROM:
- `trees_species/output_to_input/BLOCK_permutations_and_features/` - Phylogenetic blocks,
  paths, parent-child relationships, clade-species mappings
- `orthogroups/output_to_input/BLOCK_orthofinder/` (or BLOCK_orthohmm, BLOCK_broccoli) -
  Orthogroup assignments in GIGANTIC identifiers
- `genomesDB/output_to_input/STEP_4-.../` - Proteome FASTA files

### orthogroups_X_ocl provides TO:
- Downstream analysis and visualization subprojects
- upload_to_server for GIGANTIC server
