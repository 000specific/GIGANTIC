# AI_GUIDE.md (Level 3: Workflow Execution Guide)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March 01 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md)
- Parent (subproject AI guide): [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- Workflow README: [`../README.md`](../README.md)
- Reads from: NCBI nr FTP (network download)
- Outputs to: `../../../output_to_input/BLOCK_ncbi_nr_blastp/`
- 4 scripts; final = `write_run_log` per §45
- Conda env: `aiG-public_databases`

---

**For AI Assistants**: Read the BLOCK guide (`../../AI_GUIDE.md`) first. This guide focuses on running the workflow.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../AI_GUIDE.md` |
| Public databases overview | `../../../AI_GUIDE.md` |
| NCBI nr BLAST concepts | `../../AI_GUIDE.md` |
| Running the workflow | This file |

## Quick Start

```bash
vi START_HERE-user_config.yaml
bash RUN-workflow.sh
```

## Pipeline Steps

1. **Download NCBI nr** - wget downloads nr.gz from NCBI FTP (~100 GB compressed)
2. **Build BLAST database** - Decompress nr.gz, run makeblastdb to create protein database
3. **Validate database** - Run blastdbcmd -info to verify sequence count and database integrity
4. **Write run log** - Create timestamped log for provenance

## Key Configuration

- `START_HERE-user_config.yaml` - Set download URL, threads, output directory
- No INPUT_user files needed (downloads from NCBI)

## Verification Commands

```bash
# Check download completed (nr.gz is ~100 GB)
ls -lh OUTPUT_pipeline/1-output/nr.gz

# Verify BLAST database files exist
ls -la OUTPUT_pipeline/2-output/nr.p*

# Check database info
blastdbcmd -db OUTPUT_pipeline/2-output/nr -info

# Read validation report
cat OUTPUT_pipeline/3-output/3_ai-validation_report.txt

# Check run log
cat OUTPUT_pipeline/4-output/4_ai-run_log.txt
```

## Common Errors

| Error | Solution |
|-------|----------|
| Download incomplete | Re-run; wget uses `-c` flag for resume support |
| `makeblastdb: not found` | Activate conda environment with BLAST+ installed |
| Disk space error during gunzip | nr uncompressed is ~300 GB; ensure sufficient space |
| makeblastdb memory error | Request 100+ GB RAM; nr requires significant memory |
| Stale cached results after script update | Delete `work/` and `.nextflow*`, re-run without `-resume` |

## Resource Notes

- **Download**: ~100 GB, speed depends on network (1-12 hours typical)
- **Decompress**: nr.gz to nr is ~300 GB uncompressed
- **makeblastdb**: Requires ~100 GB RAM, 15+ CPUs recommended, ~2-6 hours
- **Total disk**: Plan for ~500 GB (compressed + uncompressed + database files)
