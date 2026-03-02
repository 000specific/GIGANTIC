# AI_GUIDE-diamond_ncbi_nr.md (Level 2: BLOCK Guide)

**For AI Assistants**: Read `../AI_GUIDE-one_direction_homologs.md` first for subproject overview and one-directional homolog concepts. This guide covers the DIAMOND NCBI nr search workflow.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE-project.md` |
| One-direction homologs concepts, self-hit logic | `../AI_GUIDE-one_direction_homologs.md` |
| BLOCK overview | This file |
| Running the workflow | `workflow-COPYME-diamond_ncbi_nr/ai/AI_GUIDE-diamond_ncbi_nr_workflow.md` |

## Workflow Overview

Searches species proteomes against the NCBI non-redundant (nr) protein database using DIAMOND blastp. Identifies top hits per protein, distinguishes self-hits from non-self-hits, and compiles per-species statistics.

**Input**: Species proteomes from genomesDB `output_to_input/`, NCBI nr DIAMOND database

**Output**: Per-protein top hits with NCBI headers and sequences, self/non-self hit classification, per-species and cross-species statistics

## Pipeline Scripts (6 steps)

| # | Script | Purpose |
|---|--------|---------|
| 001 | `001_ai-python-validate_proteomes.py` | Validate proteome files and manifest |
| 002 | `002_ai-python-split_proteomes_for_diamond.py` | Split proteomes into N parts for parallelization |
| 003 | `003_ai-bash-run_diamond_search.sh` | Run DIAMOND blastp per split file (parallel) |
| 004 | `004_ai-python-combine_diamond_results.py` | Combine split results per species |
| 005 | `005_ai-python-identify_top_hits.py` | Identify top self/non-self hits per protein |
| 006 | `006_ai-python-compile_statistics.py` | Compile master statistics table |

## Configuration

Edit `workflow-COPYME-diamond_ncbi_nr/diamond_ncbi_nr_config.yaml`:
- `diamond.database`: Path to DIAMOND nr database (REQUIRED)
- `diamond.evalue`: E-value threshold (default: 1e-5)
- `diamond.max_target_sequences`: Max hits per query (default: 10)
- `diamond.num_parts`: Splits per species proteome (default: 40)
- `diamond.threads_per_job`: CPUs per DIAMOND job (default: 1)
