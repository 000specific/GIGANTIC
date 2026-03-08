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

**Installation**: InterProScan is NOT recommended to install via conda. Use the official download from EBI instead. Run `bash DOWNLOAD_SOFTWARE-interproscan.sh` at the BLOCK level to download and install InterProScan into `software/interproscan/`. This shared installation is used by all workflow runs (RUN_1, RUN_2, etc.).

## Directory Structure

```
BLOCK_interproscan/
├── DOWNLOAD_SOFTWARE-interproscan.sh      # Downloads InterProScan from EBI (run once)
├── software/interproscan/                 # Shared installation (created by download script)
├── AI_GUIDE-interproscan.md               # This file
├── workflow-COPYME-run_interproscan/      # Template for new runs
└── workflow-RUN_1-run_interproscan/       # Species70, Pfam + GO annotations
```

## Active Workflow Runs

| Run | Species Set | Applications | Notes |
|-----|-------------|-------------|-------|
| RUN_1 | genomesDB-species70 (70 proteomes) | Pfam + GO terms | 25 CPUs, 187 GB RAM, SLURM account=moroz |

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

## Installation

InterProScan should NOT be installed via conda (per EBI recommendation). Instead:

```bash
cd BLOCK_interproscan/
bash DOWNLOAD_SOFTWARE-interproscan.sh
```

This downloads InterProScan from EBI FTP, extracts it to `software/interproscan-{version}/`, creates a stable symlink at `software/interproscan`, and runs initial database indexing. The version can be updated by editing `INTERPROSCAN_VERSION` in the download script.

**Prerequisites**: Java 11+ must be available (provided by the `ai_gigantic_interproscan` conda environment via `openjdk`).

## Configuration

Edit `workflow-*/START_HERE-user_config.yaml`:
- `interproscan_install_path`: Path to InterProScan installation (default: `../software/interproscan`)
- `chunk_size`: Sequences per chunk (default: 1000)
- `cpus_per_job`: Threads per InterProScan run
- `applications`: Which InterProScan databases to run (`"all"` or comma-separated list like `"Pfam"`, `"Pfam,Gene3D"`)

The `-goterms` flag is always enabled in script 003, so GO annotations are included regardless of which applications are selected.

## Resource Requirements

InterProScan is CPU-heavy and memory-intensive:
- **CPU**: 8+ cores recommended (25 used in RUN_1)
- **Memory**: 128+ GB recommended (187 GB used in RUN_1)
- **Time**: 96 hours for large species sets (less with Pfam-only)
- **Disk**: InterProScan databases require ~100 GB (full install ~15 GB download)
