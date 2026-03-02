# Paper Summary: McCoy & Fire (2020) - Intron and Gene Size Expansion During Nervous System Evolution

**Citation**: McCoy MJ, Fire AZ. "Intron and gene size expansion during nervous system evolution." *BMC Genomics* 21, 360 (2020). PMC7222433.

**URL**: https://pmc.ncbi.nlm.nih.gov/articles/PMC7222433/

**GitHub**: https://github.com/mjmccoy/BMC_Genomics_2020

---

## Overview

This large-scale comparative study examines gene and intron size across 325 eukaryotic species to test whether gene size expansion correlates with nervous system evolution. The authors demonstrate that animals with nervous systems have significantly longer genes than animals without them, and that the longest genes in any genome are preferentially expressed in neuronal tissues. This pattern holds across vertebrates and invertebrates that evolved complex nervous systems independently, suggesting a fundamental relationship between gene size and neural complexity.

## Key Metrics and Methods

Gene length is measured as end_position minus start_position from annotation coordinates, excluding UTRs to avoid annotation completeness biases. Exonic length is computed as the union of all annotated exon-coding sequences per gene (collapsing overlapping exon annotations from different isoforms). Intronic length is derived as gene length minus exonic length. Exon counts and intron lengths by ordinal position (first intron, second intron, etc.) are also tracked. The top 10% longest genes are defined using the 90th percentile threshold. Gene annotations for all 325 species were obtained from Ensembl BioMart, filtered to protein-coding genes only, spanning Ensembl portals for Chordata, Metazoa, Plants, Fungi, and Protists. RNA-seq expression data came from SRA BioProjects and the EMBL Expression Atlas for multiple species. Ortholog identification used DIOPT version 8.0, integrating predictions from nine tools including Ensembl Compara, OrthoMCL, and TreeFam. All analyses were performed in R (version 3.5.0) using biomaRt for Ensembl queries, Rsubread for RNA-seq alignment, qsmooth for quantile normalization, and ape/phylobase for comparative phylogenetic analyses.

## Key Findings

Gene length increases dramatically in animals compared to non-animal eukaryotes: chordates average 12.88 kb median gene length versus 7.29 kb for non-animal eukaryotes, with the top 10% longest vertebrate genes reaching 129.23 kb versus 7.29 kb in non-animals. Animals without nervous systems (sponges, placozoans) have significantly shorter genes than animals with nervous systems (p = 4.0e-10 in invertebrates alone). The expansion is predominantly intronic - intron sizes drive the vast majority of gene length variation, not exon number or exon length. A positional bias exists: 5-prime introns are larger and contain more conserved sequences in neuronal genes, declining toward the 3-prime end. Across diverse species (human, cattle, chicken, lizard, opossum, octopus, fly, nematode), the longest genes show enriched expression in neuronal tissues, and this relationship holds across species separated by hundreds of millions of years of evolution. Neurexin-1 (NRXN1) serves as a case study: it is one of the longest genes in the human genome, is critical for synaptic function, and its ortholog length varies across species correlating with nervous system complexity.

## Relevance to GIGANTIC gene_sizes Subproject

This paper establishes the foundational approach for the gene_sizes subproject at much larger scale (325 species). The computational pipeline is straightforward: parse annotation files for gene and exon coordinates, compute gene/exon/intron lengths and exon counts, generate per-species summary statistics, and compare across species. The published R pipeline on GitHub (https://github.com/mjmccoy/BMC_Genomics_2020) provides a reference implementation. For GIGANTIC, this analysis would be implemented in Python using GFF files from the genomesDB subproject, with cross-species comparisons enabled by ortholog data from the orthogroups subproject and taxonomic context from phylonames. The 325-species scope validates that this type of analysis scales well to large species sets.

---

## Notes

**EE_2026march03_1130**: The correlation between gene size and nervous system complexity may conflate two distinct phenomena. Intron expansion and contraction operate as genome-wide processes - driven by transposon activity, deletion bias, effective population size, and other neutral/nearly-neutral forces. If these forces inflate or compact all genes proportionally, then relative gene size rank is conserved trivially (like measuring height in a population where everyone grows at the same rate). The rank conservation finding does not by itself distinguish functional constraint on individual gene sizes from genome-wide proportional scaling. A more informative analysis would identify genes whose size *deviates* from the genome-wide scaling trend: genes that resist compaction in compact genomes, or resist inflation in expanded genomes. These deviations - not rank conservation - would be the signature of selection acting on gene size itself. This is something we could build into our gene_sizes pipeline as a "rank deviation" analysis, testing whether neuronal genes specifically resist genome-wide trends more than other functional categories.
