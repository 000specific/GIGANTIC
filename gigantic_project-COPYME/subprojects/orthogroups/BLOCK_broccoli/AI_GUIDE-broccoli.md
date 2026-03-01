# AI_GUIDE-broccoli.md (Level 2: Tool Project Guide)

**For AI Assistants**: Read `../AI_GUIDE-orthogroups.md` first for subproject overview and tool comparison. This guide covers Broccoli-specific concepts.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE-project.md` |
| Orthogroups overview, tool comparison | `../AI_GUIDE-orthogroups.md` |
| Broccoli concepts | This file |
| Running the workflow | `workflow-COPYME-run_broccoli/ai/AI_GUIDE-broccoli_workflow.md` |

## Broccoli Overview

Broccoli identifies orthogroups using a phylogeny-network approach: rapid phylogenetic tree construction (FastTree) combined with network-based label propagation. It executes a four-step internal pipeline: kmer clustering, Diamond similarity search + tree construction, network analysis + orthogroup identification, and pairwise ortholog extraction.

**Key advantage**: Chimeric protein (gene fusion) detection. Broccoli identifies proteins that appear to be fusions of two or more ancestral genes.

**Header requirement**: Like OrthoHMM, Broccoli requires short sequence headers. The pipeline handles header conversion (script 002) and restoration (script 004).

## Pipeline Scripts (6 steps)

| # | Script | Purpose |
|---|--------|---------|
| 001 | `001_ai-python-validate_proteomes.py` | Validate proteomes from genomesDB |
| 002 | `002_ai-python-convert_headers_to_short_ids.py` | Convert GIGANTIC headers to short IDs |
| 003 | `003_ai-bash-run_broccoli.sh` | Run Broccoli four-step pipeline |
| 004 | `004_ai-python-restore_gigantic_identifiers.py` | Restore full GIGANTIC identifiers |
| 005 | `005_ai-python-generate_summary_statistics.py` | Summary statistics |
| 006 | `006_ai-python-qc_analysis_per_species.py` | Per-species QC analysis |

## Broccoli Internal Steps

1. **Kmer clustering**: Initial fast grouping based on k-mer composition
2. **Diamond + trees**: Similarity search within clusters, phylogenetic tree construction
3. **Network analysis**: Label propagation on phylogenetic network to identify orthogroups
4. **Pairwise orthologs**: Extract ortholog pairs from orthogroup assignments

## Configuration

Edit `workflow-COPYME-run_broccoli/broccoli_config.yaml`:
- `cpus`: Number of threads (default: 8)
- `tree_method`: Tree construction method - `nj` (neighbor joining), `me` (minimum evolution), `ml` (maximum likelihood)
