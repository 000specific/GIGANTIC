# trees_gene_families - Gene Family Phylogenetic Analysis

## Purpose

Build phylogenetic trees for individual gene families using a reciprocal best hit (RBH) approach. Starting from reference gene sequences (RGS), discover homologs across all species via reciprocal BLAST, align sequences, trim alignments, and infer phylogenetic trees.

## Workflow

```
Block 1: RGS Preparation
  Curate reference gene sequences for each gene family

Block 2: Homolog Discovery
  Forward BLAST (RGS vs. all species databases)
  Reverse BLAST (top hits vs. RGS database)
  Extract reciprocal best hits
  Filter species for tree building
  Remap identifiers to GIGANTIC phylonames
  Concatenate sequences

Block 3: Phylogenetic Analysis
  MAFFT alignment
  ClipKit trimming
  FastTree tree building
  IQ-TREE inference (TEMPLATE_01 only)
  Tree visualization
```

## Inputs

- Reference gene sequences (RGS) per gene family (FASTA)
- Gene families manifest (TSV): gene_family_name, rgs_fasta_filename
- Species keeper list (optional): which species to include
- BLAST databases (from `genomesDB` subproject)

## Outputs

- Multiple sequence alignments (FASTA)
- Trimmed alignments (FASTA)
- Phylogenetic trees (Newick)
- Tree visualizations (PNG, SVG, PDF)
- Homolog sequence collections

## NextFlow Templates

- **TEMPLATE_01-original**: Full pipeline with FastTree AND IQ-TREE (slower, publication quality)
- **TEMPLATE_02-fasttree_only**: FastTree only (faster, good for exploratory analysis)
