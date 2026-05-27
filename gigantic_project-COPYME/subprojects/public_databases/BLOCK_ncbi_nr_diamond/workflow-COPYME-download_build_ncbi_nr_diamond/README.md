# NCBI nr DIAMOND Database Workflow

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March 01 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK: [`../AI_GUIDE.md`](../AI_GUIDE.md) — BLOCK_ncbi_nr_diamond concepts
- Parent (subproject): [`../../README.md`](../../README.md)
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Reads from: NCBI nr FTP
- Outputs to: `../../output_to_input/BLOCK_ncbi_nr_diamond/` (symlinks from `OUTPUT_pipeline/`)
- 4 scripts (download / build / validate / `write_run_log`)
- Conda env: `aiG-public_databases`

---

Download the NCBI nr protein database and build a DIAMOND search database.

## Quick Start

1. Edit `START_HERE-user_config.yaml` with your project name and settings
2. Edit `RUN-workflow.sh` with your SLURM account and qos (for HPC)
3. Run the workflow:
   - **Local**: `bash RUN-workflow.sh`
   - **SLURM**: `sbatch RUN-workflow.sh`

## Results

The DIAMOND database appears in `OUTPUT_pipeline/2-output/nr.dmnd` and is symlinked to:
- `../../output_to_input/BLOCK_ncbi_nr_diamond/nr.dmnd` (for downstream subprojects)

## Resource Requirements

- **Disk**: ~300 GB free (nr.gz ~100 GB + nr.dmnd ~150 GB)
- **Memory**: ~100 GB for DIAMOND database build
- **Time**: 6-24 hours depending on network speed and CPU count

## Need Help?

Ask your AI assistant to read `ai/AI_GUIDE.md` for detailed guidance.
