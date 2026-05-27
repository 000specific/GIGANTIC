# AI_GUIDE.md (Level 2: Tool Project Guide)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (subproject): [`../AI_GUIDE.md`](../AI_GUIDE.md)
- Parent (subproject README): [`../README.md`](../README.md)
- Workflow template: [`workflow-COPYME-run_interproscan/`](workflow-COPYME-run_interproscan/)
- This BLOCK's workflow AI guide: [`workflow-COPYME-run_interproscan/ai/AI_GUIDE.md`](workflow-COPYME-run_interproscan/ai/AI_GUIDE.md)
- Tool: InterProScan 5
- Scripts: 6 (final = `write_run_log` per §45)
- Conda env: `aiG-annotations_hmms-interproscan`
- Reads FROM: `../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs TO: `../output_to_input/BLOCK_interproscan/` (symlinks)
- Downstream: `../BLOCK_build_annotation_database/` consumes for integrated 7-column DB
- Note: Chunked + burst-friendly; see HiPerGator drain-node race note in subproject AI_GUIDE.

---

**For AI Assistants**: Read `../AI_GUIDE.md` first for subproject overview and tool comparison. This guide covers InterProScan-specific concepts.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE.md` |
| Annotations overview, tool comparison | `../AI_GUIDE.md` |
| InterProScan concepts | This file |
| Running the workflow | `workflow-COPYME-run_interproscan/ai/AI_GUIDE.md` |

## InterProScan Overview

InterProScan 5 is a comprehensive protein domain and function annotation tool that integrates 19 component databases (Pfam, Gene3D, SUPERFAMILY, SMART, PANTHER, CDD, PRINTS, ProSitePatterns, ProSiteProfiles, HAMAP, SFLD, FunFam, NCBIfam, PIRSF, Coils, MobiDB-lite, AntiFam, and more) plus Gene Ontology (GO) term assignments.

**Key feature**: Single tool run produces annotations from 19+ databases simultaneously, plus GO terms. The database builder parses these into separate per-database files.

**Installation**: InterProScan is NOT recommended to install via conda. Use the official download from EBI instead. Run `bash DOWNLOAD_SOFTWARE-interproscan.sh` at the BLOCK level to download and install InterProScan into `software/interproscan/`. This shared installation is used by all workflow runs (RUN_1, RUN_2, etc.).

## Directory Structure

```
BLOCK_interproscan/
├── DOWNLOAD_SOFTWARE-interproscan.sh      # Downloads InterProScan from EBI (run once)
├── software/interproscan/                 # Shared installation (created by download script)
├── AI_GUIDE.md               # This file
├── workflow-COPYME-run_interproscan/      # Template for new runs
└── workflow-RUN_1-run_interproscan/       # Species70, Pfam + GO annotations
```

## Active Workflow Runs

| Run | Species Set | Applications | Notes |
|-----|-------------|-------------|-------|
| RUN_1 | genomesDB (early build) | Pfam + GO terms | 25 CPUs, 187 GB RAM, SLURM account=moroz. Reference only; current canonical layout follows RUN_3. |
| RUN_2 | species70 | CDD,NCBIfam,PANTHER,SMART,SUPERFAMILY | Superseded by RUN_3 (config errors + drain-node death; valuable as diagnostic record). |
| RUN_3 | species70 | CDD,NCBIfam,PANTHER,SMART,SUPERFAMILY | **Canonical reference run.** moroz-b burst, 10 CPU / 75 GB / 96h per chunk, `errorStrategy='ignore'`, gap-detection enabled. 1413 chunks, ~12-15 hr wall, ~2.3% drain-node failure rate. |

## Pipeline Scripts (6 steps)

| # | Script | Purpose |
|---|--------|---------|
| 001 | `001_ai-python-validate_proteome_manifest.py` | Validate proteome manifest and file existence |
| 002 | `002_ai-python-chunk_proteomes.py` | Split large proteomes into chunks for parallel processing |
| 003 | `003_ai-bash-run_interproscan.sh` | Run InterProScan on each chunk |
| 004 | `004_ai-python-combine_interproscan_results.py` | Combine chunk results back into per-species files |
| 005 | `005_ai-python-write_run_log.py` | Write run log (called LAST in workflow order, not pipeline order) |
| 006 | `006_ai-python-detect_failed_chunks.py` | **Gap detection** — diff expected vs successful chunks, write `6_ai-failed_chunks.tsv` listing chunks that did not produce output |

**Chunking strategy**: Large proteomes are split into configurable-size chunks (default 1000 sequences) before running InterProScan. This enables per-chunk parallelism and prevents memory issues. Results are combined back per species after all chunks complete.

**Failure semantics**: `run_interproscan` uses `errorStrategy = 'ignore'` (an **explicit, documented override** of the CLAUDE.md "NEVER use 'ignore'" rule). Rationale: the cluster-side HiPerGator drain-node race (see subproject-level AI_GUIDE) kills ~1-3% of burst submissions transiently, and fail-fast loses the whole multi-day run. With `'ignore'`, failed chunks are silently dropped; step 006 enumerates the gaps to a TSV the user can drive a follow-up RUN_N from.

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

InterProScan is CPU-heavy and memory-intensive. **Per-chunk** (in burst mode) is the sizing that matters once you're chunking; the older "per-job" sizing applied only to non-chunked invocations.

| Mode | CPU / chunk | Memory / chunk | Time / chunk | Notes |
|------|-------------|----------------|--------------|-------|
| Burst (canonical for chunked work) | 10 | 75 GB | 96h | moroz convention: 7.5 GB/CPU. Concurrency capped by `burst_qos` (moroz-b = 450 CPU = ~45 concurrent at 10 CPU/chunk) |
| Single-allocation slurm mode | full alloc (e.g. 50) | full alloc (e.g. 375 GB) | 96h+ | Per-chunk sizing inside the allocation comes from `burst_cpus_per_chunk` / `burst_memory_gb_per_chunk` — enables N-way in-allocation parallelism |
| Local | system | system | system | Testing only |

**Disk**: InterProScan databases require ~100 GB (full install ~15 GB download). The install is shared across all RUNs via `software/interproscan/`.

**Empirical (RUN_3, 2026-05-25):** 70 species, 1,375,926 sequences, chunk_size 1000 → 1413 chunks. 5 tools per chunk (CDD,NCBIfam,PANTHER,SMART,SUPERFAMILY). 10 CPU / 75 GB / 96h per chunk on moroz-b. Wall time ~12-15 hours. ~2.3% of chunks died from drain-node race (handled silently via `errorStrategy='ignore'`, listed in `6_ai-failed_chunks.tsv`).
