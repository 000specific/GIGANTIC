# annotations_hmms - Protein Functional Annotation Pipeline

## Purpose

Comprehensive functional annotation of all proteomes using multiple complementary annotation tools. Integrates domain/family predictions, subcellular localization, signal peptides, transmembrane topology, and intrinsic disorder.

## Annotation Tools

| Tool | Version | Annotation Type |
|------|---------|----------------|
| InterProScan | 5.x | Domain/family annotations (18 member databases including Pfam, SMART, Gene3D, PANTHER, Superfamily) + Gene Ontology mapping |
| DeepLoc | 2.1 | Subcellular localization prediction (10 compartments) |
| SignalP | 6 | Signal peptide prediction |
| tmbed | - | Transmembrane topology prediction |
| MetaPredict | - | Intrinsic disorder prediction |

## Inputs

- Proteome FASTA files (from `databases` subproject)
- Species manifest (TSV)

## Outputs

- Per-species annotation tables
- Summary statistics across all species
- Annotation coverage reports

## Outputs Shared Downstream (`output_to_input/`)

- Annotation tables for integration with OCL analysis (used by `annotations_X_ocl`)

## NextFlow Templates

- **TEMPLATE_01**: Five-tool annotation pipeline
