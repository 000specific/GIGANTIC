# Architecture Overview

This document explains how GIGANTIC subprojects connect and data flows through the system.

---

## Subproject Dependency Diagram

```
[1] genomesDB                Proteome database curation and BLAST setup
       |
[2] phylonames               Phylogenetic naming system (genus_species <-> full taxonomy)
       |
       +---------------------------+--------------------------+
       |                           |                          |
[3] annotations_hmms      [4] orthogroups          [6] trees_gene_families
    Functional annotation      Ortholog group             Gene family
    (InterProScan, DeepLoc,    identification             phylogenetics
     SignalP, tmbed,           (OrthoHMM,                 (BLAST, MAFFT,
     MetaPredict)               OrthoFinder)               FastTree, IQ-TREE)
       |                           |
       |                    [5] trees_species
       |                        All possible species
       |                        tree topologies
       |                           |
       |                    [7] orthogroups_X_ocl
       |                        Gene origin, conservation,
       |                        and loss analysis (OCL)
       |                           |
       +---------------------------+
                       |
              [8] annotations_X_ocl
                  Integration of functional
                  annotations with evolutionary
                  dynamics
```

## Data Flow

### Foundation Layer (1-2)
- **genomesDB**: Curates proteome files and builds BLAST databases
- **phylonames**: Establishes the naming convention used throughout

### Analysis Layer (3-6)
- **annotations_hmms**: Functional annotation of all proteins
- **orthogroups**: Groups proteins into ortholog families
- **trees_species**: Generates all possible species tree topologies
- **trees_gene_families**: Builds phylogenies for individual gene families

### Integration Layer (7-8)
- **orthogroups_X_ocl**: Analyzes evolutionary dynamics (origin, conservation, loss)
- **annotations_X_ocl**: Integrates functional annotations with evolutionary patterns

## The `output_to_input/` Convention

Subprojects share data through standardized `output_to_input/` directories:

```
subproject_A/
└── output_to_input/          # Outputs shared downstream
    └── data_for_subproject_B.tsv

subproject_B/
└── workflow-COPYME/
    └── INPUT_user/           # References data from subproject_A
```

This creates clear dependency chains and reproducible data flow.

## The 105 Topologies

A unique feature of GIGANTIC is exhaustive topology analysis. For 5 major clades, there are exactly 105 possible unrooted bifurcating trees:

```
(2N - 3)!! = 7!! = 7 × 5 × 3 × 1 = 105
```

By analyzing all topologies, findings can be assessed for robustness to phylogenetic uncertainty.

---

*Documentation under development. Check back for updates.*
