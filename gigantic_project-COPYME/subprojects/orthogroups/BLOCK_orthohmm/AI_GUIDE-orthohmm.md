# AI_GUIDE-orthohmm.md (Level 2: Tool Project Guide)

**For AI Assistants**: Read `../AI_GUIDE-orthogroups.md` first for subproject overview and tool comparison. This guide covers OrthoHMM-specific concepts.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE-project.md` |
| Orthogroups overview, tool comparison | `../AI_GUIDE-orthogroups.md` |
| OrthoHMM concepts | This file |
| Running the workflow | `workflow-COPYME-run_orthohmm/ai/AI_GUIDE-orthohmm_workflow.md` |

## OrthoHMM Overview

OrthoHMM identifies orthogroups using profile Hidden Markov Models (HMMER) for sequence comparison, followed by MCL graph-based clustering. Profile HMMs capture position-specific amino acid preferences and are more sensitive than pairwise sequence comparison for detecting distant homologs.

**Key advantage**: Better sensitivity for divergent sequences compared to simple pairwise methods. Produces HMM profiles that can be used for downstream annotation.

**Header requirement**: OrthoHMM requires short sequence headers in `Genus_species-N` format. The pipeline handles header conversion (script 002) and restoration (script 004).

## Pipeline Scripts (6 steps)

| # | Script | Purpose |
|---|--------|---------|
| 001 | `001_ai-python-validate_proteomes.py` | Validate proteomes from genomesDB |
| 002 | `002_ai-python-convert_headers_to_short_ids.py` | Convert GIGANTIC headers to short IDs |
| 003 | `003_ai-bash-run_orthohmm.sh` | Run OrthoHMM clustering |
| 004 | `004_ai-python-restore_gigantic_identifiers.py` | Restore full GIGANTIC identifiers |
| 005 | `005_ai-python-generate_summary_statistics.py` | Summary statistics |
| 006 | `006_ai-python-qc_analysis_per_species.py` | Per-species QC analysis |

## Header Conversion

GIGANTIC headers (`g_GENEID-t_TRANSID-p_PROTID-n_Kingdom_Phylum_..._Genus_species`) are converted to `Genus_species-N` format for OrthoHMM compatibility. Script 002 creates a mapping file (`2_ai-header_mapping.tsv`) that script 004 uses to restore the original identifiers in the final output.

## Configuration

Edit `workflow-COPYME-run_orthohmm/orthohmm_config.yaml`:
- `cpus`: Number of threads (default: 8)
- `evalue`: E-value threshold (default: 0.0001)
- `single_copy_threshold`: Threshold for single-copy orthogroups (default: 0.5)
