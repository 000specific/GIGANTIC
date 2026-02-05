# annotations_X_ocl - Annotation-Evolution Integration

## Purpose

Integrate functional annotations with Origin-Conservation-Loss (OCL) evolutionary dynamics. This subproject answers questions like:

- Which functional domains are associated with recently evolved gene families?
- Which annotation groups show high conservation vs. high loss?
- How do functional signatures vary across different tree topologies?

## Workflow

1. Create annotation groups from functional annotation data
2. Determine annotation group origins (MRCA analysis)
3. Quantify conservation and loss per annotation group
4. Generate comprehensive OCL summaries
5. Integrate functional and evolutionary metrics

## Inputs

- Functional annotations (from `annotations_hmms` subproject)
- OCL data (from `origins_conservation_loss` subproject)
- Species tree structures (from `trees_species` subproject)

## Outputs

- Annotation group OCL metrics
- Integrated annotation-evolution tables
- Conservation and loss rates per functional category

## NextFlow Templates

- **TEMPLATE_01**: Full annotation-OCL integration pipeline
