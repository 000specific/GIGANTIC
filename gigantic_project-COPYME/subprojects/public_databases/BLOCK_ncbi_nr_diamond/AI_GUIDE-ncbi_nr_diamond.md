# AI_GUIDE-ncbi_nr_diamond.md (Level 2: BLOCK Guide)

**For AI Assistants**: Read `../../AI_GUIDE-project.md` first for GIGANTIC overview and directory structure. This guide covers the NCBI nr DIAMOND database BLOCK.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE-project.md` |
| BLOCK overview | This file |
| Running the workflow | `workflow-COPYME-download_build_ncbi_nr_diamond/ai/AI_GUIDE-ncbi_nr_diamond_workflow.md` |

## What This BLOCK Does

Downloads the NCBI nr (non-redundant) protein FASTA database and builds a DIAMOND search database from it. The DIAMOND database enables fast protein sequence similarity searches used by downstream annotation and homolog discovery workflows.

**Input**: NCBI FTP URL (configured in user config)

**Output**: DIAMOND database file (`nr.dmnd`) ready for `diamond blastp` searches

## Pipeline Scripts (4 steps)

| # | Script | Purpose |
|---|--------|---------|
| 001 | `001_ai-bash-download_ncbi_nr.sh` | Download NCBI nr protein FASTA (nr.gz) |
| 002 | `002_ai-bash-build_diamond_database.sh` | Build DIAMOND database from nr.gz |
| 003 | `003_ai-python-validate_database.py` | Validate database integrity and sequence count |
| 004 | `004_ai-python-write_run_log.py` | Write timestamped run log |

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `START_HERE-user_config.yaml` | Project name, threads, paths | Yes |
| `RUN-workflow.sh` | Bash workflow runner | No |
| `RUN-workflow.sbatch` | SLURM wrapper (account/qos) | Yes (SLURM settings only) |
| `ai/main.nf` | NextFlow pipeline definition | No |
| `ai/nextflow.config` | NextFlow configuration | No |

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| Download stalls or fails | Network issue, NCBI maintenance | Retry; wget `-c` flag resumes partial downloads |
| Out of disk space | nr.gz is ~100 GB, nr.dmnd is ~150 GB | Ensure 300+ GB free space |
| DIAMOND build killed | Insufficient memory | Increase SLURM `--mem` (100 GB recommended) |
| `diamond: command not found` | Conda env not activated | Check `ai_gigantic_public_databases` env exists |
| Validation reports 0 sequences | Corrupted download | Delete nr.gz and re-download |

## Diagnostic Commands

```bash
# Check download progress (file size)
ls -lh OUTPUT_pipeline/1-output/nr.gz

# Check DIAMOND database
diamond dbinfo -d OUTPUT_pipeline/2-output/nr.dmnd

# Check validation report
cat OUTPUT_pipeline/3-output/validation_report.txt

# Check disk space
df -h .
```
