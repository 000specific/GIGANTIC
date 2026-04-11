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
   - Species tree visualizations (PDF/SVG)
3. **Shares structured data downstream** for origin-conservation-loss (OCL) analyses

Zero permutations is valid - the pipeline works on a single species tree.

## Terminology

### Phylogenetic Path vs Evolutionary Path

- **Phylogenetic path**: The path on a given phylogenetic species tree from a node to the root.
  A computational/analytical concept tied to a specific species tree topology.
  Example: On structure_001, `Homo_sapiens → Hominidae → Primates → ... → Basal`

- **Evolutionary path**: The actual biological path through time - all real individuals
  and populations that existed in the evolutionary history of a species or clade.
  This is the biological reality that phylogenetic paths attempt to model.

### Phylogenetic Block vs Evolutionary Block

- **Phylogenetic block**: A single parent→child transition on a given phylogenetic species tree.
  Format: `Parent::Child` (e.g., `Cydippida::Pleurobrachia_bachei`).
  A computational unit for tracking origins, conservation, and loss across species tree topologies.

- **Evolutionary block**: The actual biological transition - the real evolutionary divergence
  event and subsequent independent evolution of a clade from its parent group.

### Key Distinction

Phylogenetic paths/blocks are **models** (computed from species tree topologies).
Evolutionary paths/blocks are **reality** (what actually happened in nature).
Multiple phylogenetic species trees can model the same evolutionary history differently,
which is exactly why the permutation approach is valuable - it explores alternative
models of the same underlying evolutionary reality.

### Structure vs Topology (Species Tree)

GIGANTIC distinguishes two related but distinct concepts when working with
permuted species trees: structure and topology. These definitions apply
specifically to species trees as produced by `trees_species/`. (GIGANTIC also
works with gene trees, which have their own vocabulary — see "Tree References
Must Be Explicit" below.)

- A **structure** is one of the resolved binary species tree variants tracked
  through the pipeline, identified persistently by `structure_NNN` (e.g.,
  `structure_001` through `structure_105` for 5 unresolved clades). A
  structure has a persistent identity that does not change as the pipeline
  operates on it — the same identifier refers to the same species tree
  variant from the moment it is enumerated to the moment downstream OCL
  pipelines consume it. A structure is the *who* — the persistent identity
  of one specific species tree variant.

- A **topology** is the abstract branching pattern of a structure — the
  arrangement of clades that distinguishes one structure from another.
  Topologies ignore clade identifiers, branch lengths, and metadata. Two
  structures have different topologies if and only if their branching
  arrangements differ. The (2N-3)!! formula for N unresolved clades counts
  topologies. A topology is the *what* — the branching pattern that defines
  one structure as distinct from another.

The two terms are not synonyms. The relationship is:

> Every structure has a topology; every topology becomes one structure when
> the pipeline instantiates it (assigns clade identifiers, grafts species
> subtrees from the input species tree, adds branch lengths and metadata).

#### Lifecycle of a structure through the pipeline

| Pipeline stage (Script) | What the structure looks like at this stage |
|---|---|
| 002 enumerate_topologies | a bare species tree topology (Newick skeleton, species at leaves only, no clade IDs) |
| 003 assign_clade_identifiers | an annotated species tree topology (topology + CXXX_Name internal node IDs) |
| 004 build_complete_trees | a **complete species tree** (annotated topology + grafted species subtrees from the input species tree + branch lengths) |
| 005–009 extract features | derived data products (parent-child tables, phylogenetic blocks and paths, clade-species mappings, species tree visualizations) all keyed by `structure_id` |
| Downstream OCL | input to evolutionary analysis; OCL pipelines iterate over structures via `structure_manifest.tsv` |

Across this lifecycle, `structure_NNN` is the persistent identifier and the
topology is unchanged from Script 002 onward — what changes is the level of
instantiation as a complete species tree.

#### When to use which term

- Use **structure** when referring to the persistent identity (`structure_042`,
  "the 105 structures we tracked," "OCL operates on each structure," "the
  structure_manifest.tsv lists which structures to analyze"). Use it whenever
  you need to identify a specific species tree variant or refer to its
  complete labeled form.

- Use **topology** when referring to the branching pattern itself ("this
  structure has the same topology as that one — the difference is purely in
  branch lengths," "Script 002 enumerates topologies," "the (2N-3)!! count
  is the number of distinct topologies"). Use it whenever you mean the
  abstract branching arrangement, especially when bridging to phylogenetic
  literature.

- Use **complete species tree** when emphasizing the fully instantiated form
  produced by Script 004 — annotated topology with grafted species subtrees,
  branch lengths, and full metadata, ready for downstream OCL consumption.

#### Resolved vs Unresolved Input Species Tree

A user-supplied input species tree may be either:

- **Resolved**: every internal node has exactly two children (no polytomies,
  no ambiguities). The pipeline produces exactly one structure
  (`structure_001`), which is identical to the input species tree.

- **Unresolved**: one or more internal nodes have ambiguous branching order
  (polytomies, or nodes explicitly flagged for permutation in
  `START_HERE-user_config.yaml` under `unresolved_clades`). For N unresolved
  internal nodes, the pipeline enumerates all `(2N-3)!!` possible binary
  resolutions. Example: 5 unresolved clades produce 105 structures
  (`structure_001` through `structure_105`).

**Every structure produced by the pipeline is itself resolved by
construction. The resolution status is a property of the input, not of any
specific structure.** What changes between the resolved and unresolved input
cases is only how many structures the pipeline produces:

| Input species tree | Structures generated |
|---|---|
| Resolved | 1 (`structure_001` = the input species tree) |
| Unresolved at N nodes | (2N-3)!! (`structure_001` through `structure_NNN`) |

### Tree References Must Be Explicit: Species Tree vs Gene Tree

GIGANTIC works with both **species trees** and **gene trees**, and the two
are often analyzed together. They are fundamentally different objects:

- A **species tree** represents the phylogenetic relationships between
  species. There is one species tree per species set (or, when ambiguity is
  permuted, a small set of variant structures of the same species set).
  Species trees are produced by the `trees_species/` subproject. Leaves are
  species; internal nodes are clades.

- A **gene tree** represents the phylogenetic relationships between gene
  copies within and across species, for a specific gene family or gene
  group. There is typically one gene tree per gene family (in
  `trees_gene_families/`) or per gene group (in `trees_gene_groups/`).
  Leaves are gene copies (each annotated with the species it comes from);
  internal nodes are inferred ancestral gene states.

References to "a tree" without qualification are ambiguous in GIGANTIC.

**Rule (documentation)**: Always qualify tree references as **species tree**
or **gene tree** in documentation — in READMEs, AI_GUIDEs, design documents,
INPUT_user READMEs, and config file comments. The qualification "phylogenetic
tree" alone is also ambiguous (it could be either) and should be made
specific ("phylogenetic species tree" or "phylogenetic gene tree") whenever
the type matters.

**Atomic terms exception**: `phylogenetic block` and `phylogenetic path` are
single named concepts in GIGANTIC vocabulary that refer specifically to
edges and root-to-tip walks on a phylogenetic species tree. Do NOT inject
`species tree` into these compound terms (i.e., do not write "phylogenetic
species tree block"). Instead, qualify the surrounding context if needed.

**Why**: The same orthogroup can be analyzed against a species tree (asking:
where did this gene family originate, where is it conserved, where was it
lost across the species phylogeny?) and against a gene tree (asking: what
are the duplication and loss histories within the gene family itself?).
These are different evolutionary questions and the same word "tree"
referring to both creates real confusion. Explicit qualification eliminates
the ambiguity at the source.

**Code is context-tolerant**: In code (Python scripts, NextFlow main.nf,
bash scripts, variable/function names), bare `tree` references are
acceptable when the surrounding subproject context makes the kind of tree
unambiguous. Strict qualification is for documentation, where readers may
not have the surrounding context.

### Hierarchies vs Trees: Origin vs Root

GIGANTIC also works with the **NCBI taxonomic hierarchy** (encoded in
phylonames). A hierarchy is structurally similar to a tree but conceptually
distinct, and GIGANTIC keeps the vocabulary separate:

- A **tree** (species tree, gene tree) represents inferred biological
  relationships. Edges in a tree represent evolutionary descent or
  divergence — they are inferences from data. Trees can be **rooted** or
  unrooted; rooting is an analytical choice (midpoint, outgroup, etc.).
  GIGANTIC trees use **root** as the term for the topmost node.

- A **hierarchy** (the NCBI taxonomic classification) represents membership
  and containment. Edges in a hierarchy represent set inclusion (e.g.,
  `Mammalia ⊂ Chordata ⊂ Metazoa`). They are not inferences; they are
  definitional. A hierarchy is intrinsically singly-originated by its
  construction — there is no such thing as an "unrooted hierarchy."
  GIGANTIC hierarchies use **origin** as the term for the topmost node.

**Rule**: In GIGANTIC documentation, do not refer to taxonomy as a "tree" or
to its topmost node as a "root." Use "hierarchy" and "origin" instead. Do
not write "rooted hierarchy" — this is a category error.

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
├── BLOCK_gigantic_species_tree/           # ACTIVE: Standardize and label a user-provided species tree
│   └── workflow-COPYME-gigantic_species_tree/
│       ├── RUN-workflow.sh
│       ├── RUN-workflow.sbatch
│       ├── START_HERE-user_config.yaml
│       ├── INPUT_user/                    # User provides: species_tree.newick
│       ├── OUTPUT_pipeline/               # Results (N-output/ per script)
│       └── ai/
│           ├── main.nf
│           ├── nextflow.config
│           └── scripts/                   # 7 Python scripts
│
└── BLOCK_permutations_and_features/       # ACTIVE: Permutation + feature extraction
    └── workflow-COPYME-permutations_and_features/
        ├── RUN-workflow.sh
        ├── RUN-workflow.sbatch
        ├── START_HERE-user_config.yaml
        ├── INPUT_user/                    # User provides: species tree + clade names
        ├── OUTPUT_pipeline/               # Results (N-output/ per script)
        └── ai/
            ├── main.nf
            ├── nextflow.config
            └── scripts/                   # 9 Python scripts
```

## BLOCKs

### BLOCK_gigantic_species_tree (Active)

Standardization and labeling BLOCK. Takes a raw user-provided species tree
(Newick format, `Genus_species` at leaves, optional clade names at internals)
and produces a fully standardized, labeled, validated species tree in all
canonical GIGANTIC formats. Fills in `ancestral_clade_NNN` names for unlabeled
internal nodes and assigns `CXXX_` clade identifiers to every node. Emits
three Newick variants (simple, full, ids-only), a clade map TSV, and an SVG
visualization. This is typically the first step for any new species set.

### BLOCK_permutations_and_features (Active)

Full permutation and feature extraction pipeline. Takes a labeled species tree
(typically from `BLOCK_gigantic_species_tree`), optionally generates N permuted
topologies for user-specified unresolved clades, and extracts comprehensive
phylogenetic features from each permutation.

### BLOCK_de_novo_species_tree (Future - Skeletal)

Classical phylogenomics supermatrix pipeline for building species trees de novo:
BUSCO sequences → MAFFT alignment → ClipKit trimming → IQ-TREE/FastTree.
Placeholder for future development.

### BLOCK Pipeline Order

For a new species set, the typical BLOCK execution order is:

```
User provides initial species tree      OR      BLOCK_de_novo_species_tree (future)
                 ↓                                         ↓
                        BLOCK_gigantic_species_tree
                        (validate, standardize, label)
                                       ↓
                        BLOCK_permutations_and_features
                        (enumerate topology permutations,
                         extract phylogenetic features)
                                       ↓
                        trees_species/output_to_input/
                                       ↓
                        Downstream: orthogroups_X_ocl, annotations_X_ocl
```

## Dependencies

### trees_species reads FROM:
- `phylonames/output_to_input/` - Clade naming conventions

### trees_species provides TO:
- `orthogroups_X_ocl` - Phylogenetic blocks, clade-species mappings, phylogenetic paths
- `annotations_X_ocl` - Same data for annotation-level OCL analysis
- Any future OCL integration subproject
