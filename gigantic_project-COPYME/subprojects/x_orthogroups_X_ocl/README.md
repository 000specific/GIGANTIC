# orthogroups_X_ocl - Evolutionary Dynamics Analysis

## Purpose

Analyze the evolutionary dynamics of orthogroups across all possible species tree topologies. For each orthogroup and each tree topology, determine:

- **Origin**: Where in the tree did the orthogroup first appear? (Most Recent Common Ancestor)
- **Conservation**: In how many descendant lineages is the orthogroup retained?
- **Loss**: In how many descendant lineages has the orthogroup been lost?

## Key Concept: Origin-Conservation-Loss (OCL)

The OCL framework tracks evolutionary events at every phylogenetic block (parent-child transition) across all tree topologies:

```
Origin:        The phylogenetic block where an orthogroup first appears
Conservation:  Retention of the orthogroup in descendant lineages
Loss:          Absence of the orthogroup in descendant lineages where it was expected
```

Because the analysis runs across ALL possible tree topologies, the results reveal which evolutionary patterns are robust regardless of phylogenetic uncertainty.

## Inputs

- Orthogroup data (from `orthogroups` subproject)
- Phylogenetic structures (from `trees_species` subproject)
- Phyloname mappings (from `phylonames` subproject)

## Outputs

- Per-orthogroup OCL metrics across all tree topologies
- Conservation rate percentages
- Loss rate percentages
- Tree coverage statistics

## Outputs Shared Downstream (`output_to_input/`)

- OCL tables per phylogenetic structure (used by `annotations_X_ocl`)

## NextFlow Templates

- **TEMPLATE_01**: Complete OCL analysis pipeline with 5 Python scripts
