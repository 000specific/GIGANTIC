# GIGANTIC Conda Environments

This directory contains conda environment definitions for GIGANTIC subprojects.

Each subproject will eventually have its own dedicated conda environment. Environments are created as subprojects are developed and their tool dependencies are finalized.

## Quick Start

Run the setup script to create all environments:

```bash
cd gigantic_project-[your_project]/
bash RUN-setup_environments.sh
```

## Environment Naming Convention

All GIGANTIC environments follow this pattern:
```
ai_gigantic_[subproject]
```

## Current Environments

These environments have finalized yml definitions:

| Environment | Subproject | Purpose |
|-------------|------------|---------|
| `ai_gigantic_phylonames` | phylonames | NCBI taxonomy and phyloname generation |
| `ai_gigantic_genomesdb` | genomesDB | Proteome database setup, standardization, and BLAST |
| `ai_gigantic_orthogroups` | orthogroups | Ortholog group identification (OrthoHMM, OrthoFinder, Broccoli) |
| `ai_gigantic_trees_gene_families` | trees_gene_families | Gene family homolog discovery, alignment, and phylogenetic analysis |

## Per-Tool Environments (trees_gene_families)

STEP_2 phylogenetic analysis uses per-tool conda environments. NextFlow activates the correct environment for each process automatically.

| Environment | Tool | Purpose |
|-------------|------|---------|
| `ai_gigantic_mafft` | MAFFT | Multiple sequence alignment |
| `ai_gigantic_clipkit` | ClipKit | Alignment trimming |
| `ai_gigantic_fasttree` | FastTree | Approximate ML phylogenetics (default) |
| `ai_gigantic_iqtree` | IQ-TREE | Publication-quality ML phylogenetics |
| `ai_gigantic_veryfasttree` | VeryFastTree | Parallelized ML (large datasets) |
| `ai_gigantic_phylobayes` | PhyloBayes-MPI | Bayesian phylogenetics |
| `ai_gigantic_ete3` | ETE3 | Phylogenetic tree visualization |

## Environment Files

| File | Description |
|------|-------------|
| `ai_gigantic_phylonames.yml` | Phylonames subproject (Python, NextFlow, wget) |
| `ai_gigantic_genomesdb.yml` | Genomes database (Python, BLAST+, BUSCO, gfastats, NextFlow) |
| `ai_gigantic_orthogroups.yml` | Orthogroups (Python, HMMER, MCL, OrthoHMM, NextFlow) |
| `ai_gigantic_trees_gene_families.yml` | Trees gene families (Python, BLAST+, NextFlow - workflow orchestration) |
| `ai_gigantic_mafft.yml` | MAFFT (Python, mafft) |
| `ai_gigantic_clipkit.yml` | ClipKit (Python, clipkit) |
| `ai_gigantic_fasttree.yml` | FastTree (Python, fasttree) |
| `ai_gigantic_iqtree.yml` | IQ-TREE (Python, iqtree) |
| `ai_gigantic_veryfasttree.yml` | VeryFastTree (Python, veryfasttree) |
| `ai_gigantic_phylobayes.yml` | PhyloBayes-MPI (Python, phylobayes-mpi) |
| `ai_gigantic_ete3.yml` | ETE3 (Python, ete3) |

## Planned Environments

These environments will be created as their subprojects are developed:

| Environment | Subproject |
|-------------|------------|
| `ai_gigantic_trees_species` | trees_species |
| `ai_gigantic_trees_gene_groups` | trees_gene_groups |
| `ai_gigantic_annotations_hmms` | annotations_hmms |
| `ai_gigantic_annotations_X_ocl` | annotations_X_ocl |
| `ai_gigantic_orthogroups_X_ocl` | orthogroups_X_ocl |
| `ai_gigantic_dark_proteome` | dark_proteome |
| `ai_gigantic_gene_sizes` | gene_sizes |
| `ai_gigantic_hot_spots` | hot_spots |
| `ai_gigantic_synteny` | synteny |
| `ai_gigantic_transcriptomes` | transcriptomes |
| `ai_gigantic_rnaseq_integration` | rnaseq_integration |
| `ai_gigantic_xenologs_vs_artifacts` | xenologs_vs_artifacts |
| `ai_gigantic_one_direction_homologs` | one_direction_homologs |
| `ai_gigantic_gene_names` | gene_names |
| `ai_gigantic_hgnc_automation` | hgnc_automation |

## Manual Installation

To install a single environment:

```bash
# Using mamba (recommended - faster)
mamba env create -f conda_environments/ai_gigantic_phylonames.yml

# Using conda
conda env create -f conda_environments/ai_gigantic_phylonames.yml
```

## Activating Environments

```bash
# On HiPerGator or module-based systems
module load conda
conda activate ai_gigantic_phylonames

# On local systems with conda in PATH
conda activate ai_gigantic_phylonames
```

## Notes

- Subproject environments include NextFlow for workflow execution
- Per-tool environments contain only the tool and Python (NextFlow activates them per-process)
- Python 3.11+ is required for all environments
- Use `mamba` instead of `conda` for faster installation
- Environment files are version-controlled for reproducibility
