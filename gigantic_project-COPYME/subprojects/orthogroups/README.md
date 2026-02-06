# orthogroups - Ortholog Group Identification

## Purpose

Identify ortholog groups across all species using complementary clustering methods. Orthogroups represent sets of genes descended from a single ancestral gene, providing the foundation for evolutionary analysis.

## Methods

| Method | Approach | Characteristics |
|--------|----------|----------------|
| OrthoHMM | Profile HMM-based clustering | Higher resolution, more groups, 100% sequence assignment |
| OrthoFinder | Phylogenetically-informed with Diamond | Broader gene families, ~90% sequence assignment |

Using both methods provides cross-validation and different perspectives on gene family evolution.

## Inputs

- Proteome FASTA files (from `genomesDB` subproject)

## Outputs

- Orthogroup assignment tables (per method, per species set)
- Orthogroup statistics and summaries
- Sequence-to-orthogroup mappings

## Outputs Shared Downstream (`output_to_input/`)

- Orthogroup definitions (used by `orthogroups_X_ocl`)
