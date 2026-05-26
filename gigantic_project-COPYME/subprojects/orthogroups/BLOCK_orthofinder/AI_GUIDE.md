# AI_GUIDE — BLOCK_orthofinder (orthogroups)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 February 28 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

**For AI Assistants**: Read `../AI_GUIDE.md` first for subproject overview and tool comparison. This guide covers OrthoFinder-specific concepts.

## Where this fits

- Parent subproject: [`../AI_GUIDE.md`](../AI_GUIDE.md) — orthogroups overview + tool comparison
- Parent project: [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- Sibling BLOCK (parallel variant): [`../BLOCK_orthofinder_array/`](../BLOCK_orthofinder_array/) — prefer for ≥30 species
- Workflow to run: [`workflow-COPYME-run_orthofinder/README.md`](workflow-COPYME-run_orthofinder/README.md)
- Reads from: `../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs to: `../output_to_input/BLOCK_orthofinder/` (standardized orthogroups table per §38, §2)

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE.md` |
| Orthogroups overview, tool comparison | `../AI_GUIDE.md` |
| OrthoFinder concepts (this BLOCK = standard, single-process) | This file |
| Running the standard workflow | `workflow-COPYME-run_orthofinder/ai/AI_GUIDE.md` |
| **Parallel-DIAMOND variant for ≥30 species** | `../BLOCK_orthofinder_array/AI_GUIDE.md` |

> **For ≥30 species**, prefer `BLOCK_orthofinder_array` — it parallelizes
> the slow DIAMOND all-vs-all step across SLURM burst-mode job arrays
> using OrthoFinder's `-op` and `-b` flags. Standard `BLOCK_orthofinder`
> (this BLOCK) is simpler and fine for smaller sets, but at scale it
> can take days.

## OrthoFinder Overview

OrthoFinder identifies orthogroups using Diamond all-vs-all sequence similarity search followed by MCL (Markov Cluster Algorithm) graph-based clustering. It also constructs species trees, gene trees, and identifies hierarchical orthogroups (HOGs).

**Key advantage**: The `-X` flag preserves original sequence identifiers in output files, eliminating the need for header conversion and restoration. This simplifies the pipeline compared to OrthoHMM and Broccoli.

## Pipeline Scripts (7 steps — includes write_run_log per §45)

| # | Script | Purpose |
|---|--------|---------|
| 001 | `001_ai-python-validate_proteomes.py` | Validate proteomes from genomesDB |
| 002 | `002_ai-python-prepare_proteomes.py` | Copy proteomes to OrthoFinder input directory |
| 003 | `003_ai-bash-run_orthofinder.sh` | Run OrthoFinder with Diamond and -X flag |
| 004 | `004_ai-python-standardize_output.py` | Parse OrthoFinder matrix output to GIGANTIC format |
| 005 | `005_ai-python-generate_summary_statistics.py` | Summary statistics |
| 006 | `006_ai-python-qc_analysis_per_species.py` | Per-species QC analysis |

**Note**: Script 002 prepares proteomes (copy to input dir) rather than converting headers, because OrthoFinder preserves original headers with `-X`. Script 004 standardizes OrthoFinder's species-column matrix format to the GIGANTIC tab-separated format.

## OrthoFinder Output Format

OrthoFinder produces `Orthogroups.tsv` as a species-column matrix:
```
Orthogroup    Species1.aa    Species2.aa    ...
OG0000000     gene1, gene2   gene3          ...
```

Script 004 converts this to the GIGANTIC standardized format:
```
OG0000000    gene1    gene2    gene3    ...
```

## Configuration

Edit `workflow-COPYME-run_orthofinder/START_HERE-user_config.yaml`:
- `cpus`: Number of threads (default: 8)
- `search_method`: `diamond` or `blast` (default: diamond)
- `mcl_inflation`: MCL inflation parameter (default: 1.5)
