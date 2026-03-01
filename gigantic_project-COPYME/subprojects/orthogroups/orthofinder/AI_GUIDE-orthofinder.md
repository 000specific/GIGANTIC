# AI_GUIDE-orthofinder.md (Level 2: Tool Project Guide)

**For AI Assistants**: Read `../AI_GUIDE-orthogroups.md` first for subproject overview and tool comparison. This guide covers OrthoFinder-specific concepts.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE-project.md` |
| Orthogroups overview, tool comparison | `../AI_GUIDE-orthogroups.md` |
| OrthoFinder concepts | This file |
| Running the workflow | `workflow-COPYME-run_orthofinder/ai/AI_GUIDE-orthofinder_workflow.md` |

## OrthoFinder Overview

OrthoFinder identifies orthogroups using Diamond all-vs-all sequence similarity search followed by MCL (Markov Cluster Algorithm) graph-based clustering. It also constructs species trees, gene trees, and identifies hierarchical orthogroups (HOGs).

**Key advantage**: The `-X` flag preserves original sequence identifiers in output files, eliminating the need for header conversion and restoration. This simplifies the pipeline compared to OrthoHMM and Broccoli.

## Pipeline Scripts (6 steps)

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

Edit `workflow-COPYME-run_orthofinder/orthofinder_config.yaml`:
- `cpus`: Number of threads (default: 8)
- `search_method`: `diamond` or `blast` (default: diamond)
- `mcl_inflation`: MCL inflation parameter (default: 1.5)
