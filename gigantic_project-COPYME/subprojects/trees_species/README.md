# trees_species

Species tree topology analysis for GIGANTIC comparative genomics.

## What This Subproject Does

Takes a user-provided species phylogenetic tree and:

1. **Generates topology permutations** by rearranging user-specified unresolved nodes
   (e.g., 5 early-branching metazoan clades yield 105 alternative topologies)
2. **Extracts phylogenetic features** from each topology:
   - Phylogenetic paths (root-to-tip traversals)
   - Phylogenetic blocks (parent::child transitions)
   - Parent-child and parent-sibling relationships
   - Clade-to-species membership mappings
   - Tree visualizations (PDF/SVG)
3. **Shares structured data downstream** for origin-conservation-loss (OCL) analyses

Zero permutations is valid - the pipeline works on a single tree.

## Terminology

### Phylogenetic Path vs Evolutionary Path

- **Phylogenetic path**: The path on a given phylogenetic TREE from a node to the root.
  A computational/analytical concept tied to a specific tree topology.
  Example: On structure_001, `Homo_sapiens → Hominidae → Primates → ... → Basal`

- **Evolutionary path**: The actual biological path through time - all real individuals
  and populations that existed in the evolutionary history of a species or clade.
  This is the biological reality that phylogenetic paths attempt to model.

### Phylogenetic Block vs Evolutionary Block

- **Phylogenetic block**: A single parent→child transition on a given phylogenetic TREE.
  Format: `Parent::Child` (e.g., `Cydippida::Pleurobrachia_bachei`).
  A computational unit for tracking origins, conservation, and loss across tree topologies.

- **Evolutionary block**: The actual biological transition - the real evolutionary divergence
  event and subsequent independent evolution of a clade from its parent group.

### Key Distinction

Phylogenetic paths/blocks are **models** (computed from tree topologies).
Evolutionary paths/blocks are **reality** (what actually happened in nature).
Multiple phylogenetic trees can model the same evolutionary history differently,
which is exactly why the permutation approach is valuable - it explores alternative
models of the same underlying evolutionary reality.

## Directory Structure

```
trees_species/
├── README.md                              # THIS FILE
├── AI_GUIDE-trees_species.md              # AI guidance
├── RUN-clean_and_record_subproject.sh
├── RUN-update_upload_to_server.sh
│
├── output_to_input/                       # Single canonical downstream location
│   ├── BLOCK_de_novo_species_tree/        # Placeholder (future)
│   └── BLOCK_permutations_and_features/   # Populated by workflow
│
├── upload_to_server/                      # Curated data for GIGANTIC server
├── user_research/                         # Personal workspace
├── research_notebook/
│
├── BLOCK_de_novo_species_tree/            # FUTURE: Build species tree de novo
│   └── workflow-COPYME-build_species_tree/
│
└── BLOCK_permutations_and_features/       # ACTIVE: Permutation + feature extraction
    └── workflow-COPYME-permutations_and_features/
        ├── RUN-workflow.sh
        ├── RUN-workflow.sbatch
        ├── permutations_and_features_config.yaml
        ├── INPUT_user/                    # User provides: tree + clade names
        ├── OUTPUT_pipeline/               # Results (N-output/ per script)
        └── ai/
            ├── main.nf
            ├── nextflow.config
            └── scripts/                   # 9 Python scripts
```

## BLOCKs

### BLOCK_permutations_and_features (Active)

Full permutation and feature extraction pipeline. Takes a single species tree,
optionally generates N permuted topologies, and extracts comprehensive
phylogenetic features from each.

### BLOCK_de_novo_species_tree (Future - Skeletal)

Classical phylogenomics supermatrix pipeline for building species trees de novo:
BUSCO sequences → MAFFT alignment → ClipKit trimming → IQ-TREE/FastTree.
Placeholder for future development.

## Dependencies

### trees_species reads FROM:
- `phylonames/output_to_input/` - Clade naming conventions

### trees_species provides TO:
- `orthogroups_X_ocl` - Phylogenetic blocks, clade-species mappings, evolutionary paths
- `annotations_X_ocl` - Same data for annotation-level OCL analysis
- Any future OCL integration subproject
