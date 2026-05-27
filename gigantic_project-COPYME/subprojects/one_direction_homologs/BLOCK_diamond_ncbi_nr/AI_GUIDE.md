# AI_GUIDE.md (Level 2: BLOCK Guide)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March 01 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (subproject AI guide): [`../AI_GUIDE.md`](../AI_GUIDE.md)
- Parent (subproject README): [`../README.md`](../README.md)
- Workflow template: [`workflow-COPYME-diamond_ncbi_nr/`](workflow-COPYME-diamond_ncbi_nr/)
- Workflow AI guide: [`workflow-COPYME-diamond_ncbi_nr/ai/AI_GUIDE.md`](workflow-COPYME-diamond_ncbi_nr/ai/AI_GUIDE.md)
- Reads FROM: `../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/` + NCBI nr DIAMOND db
- Outputs TO: `../output_to_input/BLOCK_diamond_ncbi_nr/`
- Downstream BLOCK: (none — single-BLOCK subproject); downstream consumers are external (dark_proteomes, server)
- 7 scripts (validate / split / diamond / combine / top_hits / stats / `write_run_log` per §45)
- Conda env: `aiG-one_direction_homologs` (§53 short form — single BLOCK)

---

**For AI Assistants**: Read `../AI_GUIDE.md` first for subproject overview and one-directional homolog concepts. This guide covers the DIAMOND NCBI nr search workflow.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE.md` |
| One-direction homologs concepts, self-hit logic | `../AI_GUIDE.md` |
| BLOCK overview | This file |
| Running the workflow | `workflow-COPYME-diamond_ncbi_nr/ai/AI_GUIDE.md` |

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

Edit `workflow-COPYME-diamond_ncbi_nr/START_HERE-user_config.yaml`:
- `diamond.database`: Path to DIAMOND nr database (REQUIRED)
- `diamond.evalue`: E-value threshold (default: 1e-5)
- `diamond.max_target_sequences`: Max hits per query (default: 10)
- `diamond.num_parts`: Splits per species proteome (default: 40)
- `diamond.threads_per_job`: CPUs per DIAMOND job (default: 1)
