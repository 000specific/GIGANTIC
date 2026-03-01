# AI_GUIDE-generate_phylonames.md (Level 2: BLOCK Guide)

**For AI Assistants**: Read `../AI_GUIDE-phylonames.md` first for subproject overview and phylonames concepts. This guide covers the generate_phylonames workflow.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE-project.md` |
| Phylonames concepts, numbered clades, user phylonames | `../AI_GUIDE-phylonames.md` |
| BLOCK overview | This file |
| Running the workflow | `workflow-COPYME-generate_phylonames/ai/AI_GUIDE-phylonames_workflow.md` |

## Workflow Overview

Downloads the NCBI taxonomy database and generates phylogenetically-informative species identifiers that encode the complete taxonomic lineage.

**Input**: Species list (e.g., `Homo_sapiens`, `Octopus_bimaculoides`)

**Output**: Mapping of `genus_species` to `phyloname` to `phyloname_taxonid`

## Pipeline Scripts (6 steps)

| # | Script | Purpose |
|---|--------|---------|
| 001 | `001_ai-bash-download_ncbi_taxonomy.sh` | Download NCBI taxonomy database |
| 002 | `002_ai-python-generate_phylonames.py` | Generate phylonames for all NCBI species |
| 003 | `003_ai-python-create_species_mapping.py` | Create project-specific mapping |
| 004 | `004_ai-python-apply_user_phylonames.py` | (Optional) Apply user-provided phylonames |
| 005 | `005_ai-python-generate_taxonomy_summary.py` | Generate taxonomy summary (MD + HTML) |
| 006 | `006_ai-python-write_run_log.py` | Write run log to research notebook |

## Configuration

Edit `workflow-COPYME-generate_phylonames/phylonames_config.yaml`:
- `project_name`: Your project name (used in output filenames)
- `user_phylonames`: (Optional) Path to custom phylonames TSV
- `mark_unofficial`: Whether to mark user clades as UNOFFICIAL (default: true)
