# trees_species - Exhaustive Species Tree Topology Generation

## Purpose

Generate ALL mathematically possible rooted bifurcating tree topologies for a set of major clades, then graft full species subtrees onto each topology. This provides a comprehensive phylogenetic framework that accounts for uncertainty in deep phylogenetic relationships.

## The Approach

For N major clades, the number of possible unrooted bifurcating trees is:

```
(2N - 3)!! = (2N-3) x (2N-5) x ... x 3 x 1
```

Examples:
- 3 clades: 3 topologies
- 4 clades: 15 topologies
- 5 clades: 105 topologies
- 6 clades: 945 topologies

Each topology represents a distinct hypothesis about how the major clades are related. By analyzing all topologies, findings can be assessed for robustness to phylogenetic uncertainty.

## Key Concept: Phylogenetic Blocks

A phylogenetic block represents the evolutionary branch where a clade diverges from its ancestor, expressed in Parent::Child notation:

```
Bilateria::Mollusca          # The branch where Mollusca diverges from Bilateria
Metazoa::Bilateria           # The branch where Bilateria diverges from Metazoa
```

## Inputs

- Reference species tree (Newick format) with species assignments
- Major clade definitions
- Species-to-clade assignments

## Outputs

- Complete Newick trees for all possible topologies
- Tree visualizations (PDF, SVG)
- Evolutionary path tables
- Parent-child relationship tables
- Phylogenetic block definitions

## Outputs Shared Downstream (`output_to_input/`)

- Phylogenetic block definitions (used by `orthogroups_X_ocl`)
- Parent-child relationship tables (used by `orthogroups_X_ocl`)
- Species membership mappings (used by downstream analyses)

## NextFlow Templates

- **TEMPLATE_01**: Full species tree generation pipeline with 7 sequential Python scripts
