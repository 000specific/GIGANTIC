# AI_GUIDE-interproscan.md (Level 2: Tool Project Guide)

**For AI Assistants**: Read `../AI_GUIDE-annotations_hmms.md` first for subproject overview and tool comparison. This guide covers InterProScan-specific concepts.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE-project.md` |
| Annotations overview, tool comparison | `../AI_GUIDE-annotations_hmms.md` |
| InterProScan concepts | This file |
| Running the workflow | `workflow-COPYME-run_interproscan/ai/AI_GUIDE-interproscan_workflow.md` |

## InterProScan Overview

InterProScan 5 is a comprehensive protein domain and function annotation tool that integrates 19 component databases (Pfam, Gene3D, SUPERFAMILY, SMART, PANTHER, CDD, PRINTS, ProSitePatterns, ProSiteProfiles, HAMAP, SFLD, FunFam, NCBIfam, PIRSF, Coils, MobiDB-lite, AntiFam, and more) plus Gene Ontology (GO) term assignments.

**Key feature**: Single tool run produces annotations from 19+ databases simultaneously, plus GO terms. The database builder parses these into separate per-database files.

## Pipeline Scripts (4 steps)

| # | Script | Purpose |
|---|--------|---------|
| 001 | `001_ai-python-validate_proteome_manifest.py` | Validate proteome manifest and file existence |
| 002 | `002_ai-python-chunk_proteomes.py` | Split large proteomes into chunks for parallel processing |
| 003 | `003_ai-bash-run_interproscan.sh` | Run InterProScan on each chunk |
| 004 | `004_ai-python-combine_interproscan_results.py` | Combine chunk results back into per-species files |

**Chunking strategy**: Large proteomes are split into configurable-size chunks (default 1000 sequences) before running InterProScan. This enables per-chunk parallelism and prevents memory issues. Results are combined back per species after all chunks complete.

## InterProScan Command

The core command (preserved from GIGANTIC_0):
```bash
interproscan.sh -i INPUT -goterms -dp -f tsv -cpu N -d output/
```

Flags:
- `-goterms`: Include Gene Ontology term assignments
- `-dp`: Disable precalculated match lookup (ensures fresh analysis)
- `-f tsv`: Output as tab-separated values
- `-cpu N`: Number of threads

## InterProScan Output Format

15-column TSV with no header:
```
protein_id  md5  length  analysis_db  signature_id  signature_desc  start  stop  score  status  date  interpro_id  interpro_desc  go_terms  pathway
```

The database builder (BLOCK_build_annotation_database) parses column 4 (analysis_db) to split results into 19 separate database files.

## Configuration

Edit `workflow-COPYME-run_interproscan/START_HERE-user_config.yaml`:
- `interproscan_install_path`: Path to InterProScan installation
- `chunk_size`: Sequences per chunk (default: 1000)
- `cpus_per_job`: Threads per InterProScan run (default: 16)

## Resource Requirements

InterProScan is CPU-heavy and memory-intensive:
- **CPU**: 8+ cores recommended
- **Memory**: 128 GB recommended
- **Time**: 96 hours for large species sets
- **Disk**: InterProScan databases require ~100 GB
