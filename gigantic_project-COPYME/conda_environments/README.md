# GIGANTIC Conda Environments

This directory contains conda environment definitions for all GIGANTIC subprojects.

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

| Environment | Subproject | Purpose |
|-------------|------------|---------|
| `ai_gigantic_phylonames` | phylonames | NCBI taxonomy and phyloname generation |
| `ai_gigantic_genomesdb` | x_genomesDB | Proteome database setup and BLAST |
| `ai_gigantic_orthogroups` | x_orthogroups | Ortholog group identification |
| `ai_gigantic_trees` | x_trees_species | Species tree generation |
| `ai_gigantic_annotations` | x_annotations_hmms | HMM-based functional annotation |

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

## Environment Files

| File | Description |
|------|-------------|
| `ai_gigantic_phylonames.yml` | Phylonames subproject (Python, NextFlow, wget) |
| `ai_gigantic_genomesdb.yml` | Genomes database (Python, BLAST+, NextFlow) |
| `ai_gigantic_orthogroups.yml` | Orthogroups (Python, OrthoFinder, NextFlow) |
| `ai_gigantic_trees.yml` | Tree building (Python, IQ-TREE, FastTree, NextFlow) |
| `ai_gigantic_annotations.yml` | Annotations (Python, HMMER, NextFlow) |

## Notes

- All environments include NextFlow for workflow execution
- Python 3.9+ is required for all environments
- Use `mamba` instead of `conda` for faster installation
- Environment files are version-controlled for reproducibility
