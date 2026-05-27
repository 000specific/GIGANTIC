# AI_GUIDE.md (Level 2: BLOCK Guide)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March 01 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (subproject AI guide): [`../AI_GUIDE.md`](../AI_GUIDE.md) — two-BLOCK overview
- Parent (subproject README): [`../README.md`](../README.md)
- Workflow template: [`workflow-COPYME-download_build_ncbi_nr_blastp/`](workflow-COPYME-download_build_ncbi_nr_blastp/)
- Workflow AI guide: [`workflow-COPYME-download_build_ncbi_nr_blastp/ai/AI_GUIDE.md`](workflow-COPYME-download_build_ncbi_nr_blastp/ai/AI_GUIDE.md)
- Builds: BLAST+ blastp database
- Reads FROM: NCBI nr FTP (network)
- Outputs TO: `../output_to_input/BLOCK_ncbi_nr_blastp/`
- Sibling BLOCK: `../BLOCK_ncbi_nr_diamond/` — same input, different output format
- 4 scripts (download / build / validate / `write_run_log` per §45)
- Conda env: `aiG-public_databases` (shared with sibling per §53)

---

**For AI Assistants**: Read `../AI_GUIDE.md` first for subproject overview. This guide covers NCBI nr BLAST protein database specifics.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE.md` |
| Public databases overview | `../AI_GUIDE.md` |
| NCBI nr BLAST concepts | This file |
| Running the workflow | `workflow-COPYME-download_build_ncbi_nr_blastp/ai/AI_GUIDE.md` |

## What This BLOCK Does

Downloads the NCBI non-redundant (nr) protein FASTA from NCBI FTP, then builds a BLAST protein database using `makeblastdb`. The resulting database is used by downstream BLASTp homology searches.

## Directory Structure

```
BLOCK_ncbi_nr_blastp/
├── AI_GUIDE.md                        # This file
└── workflow-COPYME-download_build_ncbi_nr_blastp/     # Template for new runs
    ├── START_HERE-user_config.yaml
    ├── RUN-workflow.sh
    ├── RUN-workflow.sh
    └── ai/
```

## Pipeline Scripts (4 steps)

| # | Script | Purpose |
|---|--------|---------|
| 001 | `001_ai-bash-download_ncbi_nr.sh` | Download NCBI nr FASTA (nr.gz) from FTP |
| 002 | `002_ai-bash-build_blastp_database.sh` | Decompress nr.gz and build BLAST protein database with makeblastdb |
| 003 | `003_ai-python-validate_database.py` | Validate database using blastdbcmd -info |
| 004 | `004_ai-python-write_run_log.py` | Write timestamped run log |

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `START_HERE-user_config.yaml` | Download URL, threads, output paths | Yes |
| `RUN-workflow.sh` | Bash workflow runner | No |
| `RUN-workflow.sh` | SLURM wrapper | Yes (account, qos) |
| `ai/nextflow.config` | Nextflow resource allocation | Rarely |
| `ai/main.nf` | Pipeline definition | No |

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| Download incomplete / corrupt | Network interruption | Re-run; wget uses `-c` (continue) |
| `makeblastdb` fails | Insufficient disk or memory | nr requires ~300 GB disk, 100 GB RAM |
| `blastdbcmd -info` reports 0 sequences | Database build failed silently | Check makeblastdb stderr, re-run build step |
| Stale cached results | Nextflow work/ cache | Delete `work/` and `.nextflow*`, re-run |

## Diagnostic Commands

```bash
# Check download file size (nr.gz is ~100 GB)
ls -lh OUTPUT_pipeline/1-output/nr.gz

# Verify BLAST database files exist
ls OUTPUT_pipeline/2-output/nr.p*

# Query database info
blastdbcmd -db OUTPUT_pipeline/2-output/nr -info

# Check validation report
cat OUTPUT_pipeline/3-output/3_ai-validation_report.txt
```

## GIGANTIC Convention: No -parse_seqids

BLAST databases in GIGANTIC are built WITHOUT `-parse_seqids` because many NCBI nr identifiers exceed the 50-character limit imposed by that flag. Omitting it avoids build failures on long identifiers.
