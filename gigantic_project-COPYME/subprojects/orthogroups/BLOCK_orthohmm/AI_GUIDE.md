# AI_GUIDE — BLOCK_orthohmm (orthogroups)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 February 28 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

**For AI Assistants**: Read `../AI_GUIDE.md` first for subproject overview and tool comparison. This guide covers OrthoHMM-specific concepts.

## Where this fits

- Parent subproject: [`../AI_GUIDE.md`](../AI_GUIDE.md) — orthogroups overview + tool comparison
- Parent project: [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- Sibling BLOCK (parallel variant): [`../BLOCK_orthohmm_GIGANTIC/`](../BLOCK_orthohmm_GIGANTIC/) — prefer for ≥30 species
- Workflow to run: [`workflow-COPYME-run_orthohmm/README.md`](workflow-COPYME-run_orthohmm/README.md)
- Reads from: `../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs to: `../output_to_input/BLOCK_orthohmm/` (standardized orthogroups table per §38, §2)

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE.md` |
| Orthogroups overview, tool comparison | `../AI_GUIDE.md` |
| OrthoHMM concepts (this BLOCK = standard, single-process) | This file |
| Running the standard workflow | `workflow-COPYME-run_orthohmm/ai/AI_GUIDE.md` |
| **Parallel-phmmer variant for ≥30 species** | `../BLOCK_orthohmm_GIGANTIC/AI_GUIDE.md` |

> **For ≥30 species**, prefer `BLOCK_orthohmm_GIGANTIC` — it parallelizes
> the slow phmmer all-vs-all step across SLURM burst-mode job arrays.
> Standard `BLOCK_orthohmm` (this BLOCK) is simpler and fine for smaller
> sets, but at scale it can take days and may hit per-process timeouts.

## OrthoHMM Overview

OrthoHMM identifies orthogroups using profile Hidden Markov Models (HMMER) for sequence comparison, followed by MCL graph-based clustering. Profile HMMs capture position-specific amino acid preferences and are more sensitive than pairwise sequence comparison for detecting distant homologs.

**Key advantage**: Better sensitivity for divergent sequences compared to simple pairwise methods. Produces HMM profiles that can be used for downstream annotation.

**Header requirement**: OrthoHMM requires short sequence headers in `Genus_species-N` format. The pipeline handles header conversion (script 002) and restoration (script 004).

## Pipeline Scripts (7 steps)

| # | Script | Purpose |
|---|--------|---------|
| 001 | `001_ai-python-validate_proteomes.py` | Validate proteomes from genomesDB |
| 002 | `002_ai-python-convert_headers_to_short_ids.py` | Convert GIGANTIC headers to short IDs |
| 003 | `003_ai-bash-run_orthohmm.sh` | Run OrthoHMM clustering |
| 004 | `004_ai-python-restore_gigantic_identifiers.py` | Restore full GIGANTIC identifiers |
| 005 | `005_ai-python-generate_summary_statistics.py` | Summary statistics |
| 006 | `006_ai-python-qc_analysis_per_species.py` | Per-species QC analysis |
| 007 | `007_ai-python-write_run_log.py` | Write timestamped run log |

## Header Conversion

GIGANTIC headers (`g_GENEID-t_TRANSID-p_PROTID-n_Kingdom_Phylum_..._Genus_species`) are converted to `Genus_species-N` format for OrthoHMM compatibility. Script 002 creates a mapping file (`2_ai-header_mapping.tsv`) that script 004 uses to restore the original identifiers in the final output.

## Configuration

Edit `workflow-COPYME-run_orthohmm/START_HERE-user_config.yaml`:
- `cpus`: Number of threads (default: 8)
- `evalue`: E-value threshold (default: 0.0001)
- `single_copy_threshold`: Threshold for single-copy orthogroups (default: 0.5)
