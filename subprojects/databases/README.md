# databases - Proteome Database Curation

## Purpose

Curate and organize proteome FASTA files for all species in your study, and build BLAST databases for downstream similarity searches.

## Inputs

- Proteome FASTA files (`.aa` format) downloaded from NCBI, UniProt, or other sources
- Species manifest (TSV) mapping species names to proteome file paths

## Outputs

- Standardized proteome files with GIGANTIC phyloname-based filenames
- BLAST databases (blastp format) for each species
- Species metadata tables

## Outputs Shared Downstream (`output_to_input/`)

- Proteome file paths and metadata for use by `annotations_hmms`, `orthogroups`, and `trees_gene_families`

## Usage

1. Place your proteome FASTAs in `000_user/`
2. Create a species manifest in `nf_workflow-TEMPLATE_01/INPUT_user/`
3. Run the setup scripts to standardize naming and build BLAST databases

## File Naming Convention

Proteome files follow this structure:
```
phyloname___ncbi_taxonomy_id-genome_assembly_id-download_date-data_type.aa
```

Example:
```
Metazoa_Mollusca_Cephalopoda_Octopoda_Octopodidae_Octopus_bimaculoides___37653-ncbi_GCF_001194135.2-downloaded_20241011-gene_models_T1.aa
```
