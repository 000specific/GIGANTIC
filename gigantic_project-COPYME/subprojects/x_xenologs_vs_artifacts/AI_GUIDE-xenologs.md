# AI Guide: Xenologs vs Artifacts

## Subproject Context

This is a **post-orthogroup analysis** subproject focused on distinguishing true horizontal gene transfer events (xenologs) from technical artifacts in genomic data.

## Key Concepts

### Xenologs
Homologous genes that arose through horizontal gene transfer (HGT) rather than vertical inheritance. These appear in unexpected lineages based on the species tree.

### Common Artifacts
1. **Contamination** - Foreign DNA in sequencing/assembly
2. **Assembly errors** - Misassembled chimeric sequences
3. **Annotation errors** - Incorrect gene predictions

## Upstream Data

This subproject uses outputs from:
- `orthogroups/` - To identify genes with unusual distributions
- `trees_gene_families/` - To examine phylogenetic placement
- `trees_species/` - To define expected inheritance patterns

## Implementation Notes

*This subproject is currently structural. Implementation details will be added when workflows are developed.*
