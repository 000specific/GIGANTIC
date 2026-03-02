# Paper Summary: McCoy & Fire (2024) - Gene Size Conservation and Neuronal Enrichment

**Citation**: McCoy MJ, Fire AZ. "Large, complex neuronal genes are conserved in size across evolution." *Current Biology* (2024). PMC10081198.

**URL**: https://pmc.ncbi.nlm.nih.gov/articles/PMC10081198/

---

## Overview

This study examines how gene size is preserved and evolves across 13 eukaryotic species, spanning animals, plants, fungi, and a choanoflagellate. The central finding is that the relative size ranking of genes is remarkably conserved across species separated by over a billion years of evolution, and that the largest genes are disproportionately enriched for brain and synaptic functions. The species set includes Homo sapiens, Mus musculus, Octopus sinensis, Hormiphora californensis (a ctenophore), Amphimedon queenslandica (sponge), and Salpingoeca rosetta (choanoflagellate), making it directly relevant to the GIGANTIC project's comparative genomics framework.

## Key Metrics and Methods

The authors measure gene size as the span from first exon start to last exon end, explicitly excluding UTRs to avoid annotation-quality artifacts across species. They also measure CDS size (total coding nucleotides), protein size (amino acid count), isoform count (number of annotated transcripts per gene), and dN/dS ratios for human-mouse orthologs. A critical methodological innovation is the use of relative gene size (quantile rank within each genome) rather than absolute sizes, enabling meaningful cross-species comparison even when absolute sizes differ by orders of magnitude due to intron and genome size variation. Orthology was established using OrthoFinder across all 13 species. Data sources included Ensembl BioMart for gene annotations, GenOrigin for gene age estimation, TimeTree for species phylogenies, and the Human Protein Atlas for tissue-enriched gene classification. All analyses were performed in R.

## Key Findings

While absolute gene sizes vary enormously across species (human genes average ~30x larger than C. elegans genes), the rank order of gene sizes is strikingly preserved: if a gene is among the top 10% largest in humans, its ortholog tends to be among the top 10% largest in other species. CDS size remains relatively constant across species - it is intron expansion that drives size variation. The top 10% largest human genes are enriched for brain and synaptic functions (neuron recognition, presynaptic membrane assembly, cell-cell adhesion) while testis-enriched and skin-enriched genes concentrate among the smallest genes. The largest genes are ancient (average inferred age ~953 million years) and under strong purifying selection (low dN/dS), yet have accumulated the most transcript isoforms, suggesting functional diversification through alternative splicing enabled by large introns. Octopus shows a parallel expansion of gene sizes to vertebrates despite 680+ million years of independent evolution, with both lineages independently evolving complex nervous systems. Of 134 brain-enriched orthogroups in humans, 71 are conserved in sponge and 47 in choanoflagellate, indicating these large ancient genes predate the nervous system.

## Relevance to GIGANTIC gene_sizes Subproject

This paper provides the methodological template for the gene_sizes subproject. The approach of extracting gene coordinates from annotation files (GFF/GTF), computing gene length, exonic length, intronic length, and exon counts, then ranking genes by quantile within each genome for cross-species comparison, maps directly onto GIGANTIC's species set and data infrastructure. The inclusion of Hormiphora californensis (ctenophore) makes this especially relevant to the project's ctenophore research focus.

---

## Notes

**EE_2026march03_1130**: The authors interpret relative rank conservation as evidence that gene size is functionally constrained. But there is an alternative explanation: intron expansion and contraction are genome-wide processes (driven by transposon activity, deletion bias, population size effects, etc.), so all genes inflate or deflate together like a rising or falling tide. Under this model, relative rank is conserved not because individual gene sizes are under selection, but because the same genome-wide forces act on all genes proportionally. The interesting biological question then becomes: which genes *deviate* from the genome-wide trend? Genes that resist genome-wide shrinkage (staying large when the genome compacts) or resist inflation (staying small when the genome expands) would be the ones under genuine size-related selective pressure. This is something we could test in our gene_sizes pipeline by looking at rank deviations across orthologs relative to the genome-wide scaling trend.
