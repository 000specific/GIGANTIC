# AI Guide: public_databases Subproject

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March 01 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (project): [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — GIGANTIC overview + general patterns
- Subproject README: [`README.md`](README.md)
- Two BLOCKs (independent, same input, different output format):
-   - [`BLOCK_ncbi_nr_blastp/AI_GUIDE.md`](BLOCK_ncbi_nr_blastp/AI_GUIDE.md) — BLAST+ db for blastp searches
-   - [`BLOCK_ncbi_nr_diamond/AI_GUIDE.md`](BLOCK_ncbi_nr_diamond/AI_GUIDE.md) — DIAMOND db for fast vs-nr searches
- Reads FROM: NCBI nr FTP (network download)
- Outputs TO (`output_to_input/`): per-tool prepared database directories (large binary files)
- Downstream consumers: `one_direction_homologs` (axis_a — diamond db), any subproject doing vs-nr BLAST
- Conda env: `aiG-public_databases` (shared by both BLOCKs per §53; both need blast+ and diamond)

---

**For AI Assistants**: Read `../../AI_GUIDE.md` first for GIGANTIC overview, directory structure, and general patterns. This guide covers public_databases-specific concepts and troubleshooting.

**Location**: `gigantic_project-*/subprojects/public_databases/`

---

## CRITICAL: Surface Discrepancies - No Silent Changes

**The user is managing this project - you must surface discrepancies so the user can make decisions. Silent changes undermine project management.**

- NEVER silently do something different than requested
- NEVER assume you know better and proceed without asking
- ALWAYS stop and explain the discrepancy
- ALWAYS ask for clarification before proceeding

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../AI_GUIDE.md` |
| Public databases concepts, troubleshooting | This file |
| DIAMOND nr database setup | `BLOCK_ncbi_nr_diamond/AI_GUIDE.md` |
| DIAMOND nr workflow execution | `BLOCK_ncbi_nr_diamond/workflow-COPYME-*/ai/AI_GUIDE.md` |
| BLAST nr database setup | `BLOCK_ncbi_nr_blastp/AI_GUIDE.md` |
| BLAST nr workflow execution | `BLOCK_ncbi_nr_blastp/workflow-COPYME-*/ai/AI_GUIDE.md` |

---

## What This Subproject Does

**Purpose**: Download, build, and maintain public reference databases used by downstream GIGANTIC subprojects.

**Two-BLOCK Architecture**:

| BLOCK | Purpose | When to run |
|-------|---------|-------------|
| **BLOCK_ncbi_nr_diamond** | Download NCBI nr, build DIAMOND database | Before running one_direction_homologs with DIAMOND |
| **BLOCK_ncbi_nr_blastp** | Download NCBI nr, build BLAST protein database | Before running one_direction_homologs with BLAST |

**Input**: No user-provided inputs — databases are downloaded from public sources

**Output**: Pre-built, indexed databases ready for homology searching

---

## Directory Structure (relative to subproject root)

```
public_databases/
├── README.md                        # Human documentation
├── AI_GUIDE.md     # THIS FILE
│
├── user_research/                   # Personal workspace
├── upload_to_server/                # Server sharing
│
├── output_to_input/                                # Outputs for downstream subprojects
│   ├── BLOCK_ncbi_nr_diamond/                     # DIAMOND database symlink
│   └── BLOCK_ncbi_nr_blastp/                      # BLAST database symlink
│
├── BLOCK_ncbi_nr_diamond/
│   ├── AI_GUIDE.md          # BLOCK-level guide
│   └── workflow-COPYME-download_build_ncbi_nr_diamond/
│       ├── RUN-workflow.sh                  # bash RUN-workflow.sh
│       ├── RUN-workflow.sh              # sbatch RUN-workflow.sh
│       ├── START_HERE-user_config.yaml      # User edits download settings
│       ├── INPUT_user/                      # No inputs needed
│       ├── OUTPUT_pipeline/                 # Database files
│       └── ai/                              # Nextflow pipeline and scripts
│
└── BLOCK_ncbi_nr_blastp/
    ├── AI_GUIDE.md           # BLOCK-level guide
    └── workflow-COPYME-download_build_ncbi_nr_blastp/
        ├── RUN-workflow.sh
        ├── RUN-workflow.sh
        ├── START_HERE-user_config.yaml
        ├── INPUT_user/
        ├── OUTPUT_pipeline/
        └── ai/
```

---

## Public Database Concepts

### NCBI Non-Redundant (nr) Protein Database

**What it is**: The most comprehensive public protein sequence collection, aggregating sequences from GenBank, RefSeq, PDB, SwissProt, PIR, and PRF.

| Concept | Explanation |
|---------|-------------|
| What it contains | Hundreds of millions of protein sequences from all organisms |
| Why "non-redundant" | Identical sequences from different sources are merged into single entries |
| Update frequency | Weekly by NCBI |
| Size | ~100 GB compressed, ~300 GB uncompressed |
| Source FTP | `ftp.ncbi.nlm.nih.gov/blast/db/FASTA/nr.gz` |

### DIAMOND vs. BLAST

| Feature | DIAMOND | BLAST |
|---------|---------|-------|
| Speed | ~1000x faster | Gold standard (slower) |
| Sensitivity | High (comparable to BLAST) | Highest |
| Memory | Higher (~150 GB for nr) | Lower (~100 GB for nr) |
| Use case | Large-scale, all-proteome searches | Targeted, publication-quality searches |
| Tool | `diamond blastp` | `blastp` |

### Database Versioning

Each download creates a versioned directory:
```
ncbi_nr_YYYYMMDD/
```

This ensures reproducibility — you always know which version of NCBI nr produced your results.

---

## Disk Space Considerations

**CRITICAL**: Public database workflows require substantial disk space.

| Phase | DIAMOND | BLAST |
|-------|---------|-------|
| Download (nr.gz) | ~100 GB | ~100 GB |
| Uncompressed (nr) | ~300 GB | ~300 GB |
| Built database | ~150 GB | ~100 GB |
| **Total during build** | **~550 GB** | **~500 GB** |
| **Final (after cleanup)** | **~250 GB** | **~200 GB** |

The workflow cleans up the uncompressed FASTA after building to save space.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "No space left on device" | Insufficient disk space | Need ~550 GB free for DIAMOND, ~500 GB for BLAST |
| Download interrupted | Network issues or NCBI server load | Re-run workflow — download resumes with wget -c |
| "diamond makedb" killed | Insufficient memory | Increase SLURM memory allocation (recommend 100+ GB) |
| "makeblastdb" fails | Insufficient disk or corrupted download | Verify md5sum of download, re-download if needed |
| Permission denied | Scripts not executable | `chmod +x ai/scripts/*.sh` |
| Slow download | NCBI FTP congestion | Try during off-peak hours (US nights/weekends) |

### Diagnostic Commands

```bash
# Check disk space
df -h .

# Check download progress (file size)
ls -lh OUTPUT_pipeline/1-output/nr.gz

# Check DIAMOND database exists and is valid
diamond dbinfo -d OUTPUT_pipeline/2-output/nr.dmnd

# Check BLAST database exists
blastdbcmd -db OUTPUT_pipeline/2-output/nr -info

# Check workflow logs
ls -la ai/logs/
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `BLOCK_*/workflow-*/START_HERE-user_config.yaml` | Download and build settings | **YES** |
| `BLOCK_*/workflow-*/RUN-workflow.sh` | SLURM account/qos/resources | **YES** (SLURM) |
| `output_to_input/BLOCK_ncbi_nr_diamond/` | DIAMOND database for downstream | No |
| `output_to_input/BLOCK_ncbi_nr_blastp/` | BLAST database for downstream | No |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| General help | "Which database format do you need — DIAMOND (fast) or BLAST (highest quality)?" |
| Disk space concerns | "Do you have at least 550 GB free? Building databases requires substantial temporary space." |
| Download failed | "Was the download interrupted? We can resume it." |
| Which to use | "For proteome-level searches (all proteins in all species), DIAMOND is recommended. For targeted gene family searches, BLAST provides the highest sensitivity." |
| Both needed | "You can build both independently — they share the same source data but produce different database formats." |

---

## Session hygiene (per §61)

For productive project work:
- **Root every chat session at this named `gigantic_project-*/` directory**.
  Not at `GIGANTIC/` (framework root, reserved for framework dev per §16),
  not at `subprojects/<X>/`, not at a `workflow-COPYME-*/` dir, not at
  any directory deeper than the named project root.
- **One chat session per subproject** you're actively working in — keeps
  context focused and prevents cross-subproject confusion.
- **Continue the same session over many compactions** (lossless per §9)
  until it becomes muddled or slow; then start fresh in a new session,
  same root, same subproject focus.
- **Keep a separate "small questions" session** for one-off questions
  so subproject sessions stay focused.

See `ai/ai_FYIs/gigantic_conventions.md` §61 for the full rationale.
