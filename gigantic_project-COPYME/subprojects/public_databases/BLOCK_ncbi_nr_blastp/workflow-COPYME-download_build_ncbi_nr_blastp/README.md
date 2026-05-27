# NCBI nr BLAST Protein Database Workflow

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March 01 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK: [`../AI_GUIDE.md`](../AI_GUIDE.md) — BLOCK_ncbi_nr_blastp concepts
- Parent (subproject): [`../../README.md`](../../README.md)
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Reads from: NCBI nr FTP
- Outputs to: `../../output_to_input/BLOCK_ncbi_nr_blastp/` (symlinks from `OUTPUT_pipeline/`)
- 4 scripts (download / build / validate / `write_run_log`)
- Conda env: `aiG-public_databases`

---

Downloads the NCBI non-redundant (nr) protein FASTA and builds a BLAST protein database using `makeblastdb`. The resulting database is used by downstream BLASTp homology searches across GIGANTIC subprojects.

## Prerequisites

- `ai_gigantic_public_databases` conda environment (created automatically on first run)
- BLAST+ installed in conda environment (provides `makeblastdb` and `blastdbcmd`)
- Nextflow available
- Sufficient disk space (~300 GB for nr.gz + uncompressed + database files)
- Sufficient memory (~100 GB for makeblastdb)

## Usage

```bash
vi START_HERE-user_config.yaml
bash RUN-workflow.sh         # Local
sbatch RUN-workflow.sh   # SLURM
```

## Pipeline

4 steps: download NCBI nr FASTA, build BLAST protein database with makeblastdb, validate database with blastdbcmd, write run log.

## Outputs

- BLAST protein database files (nr.pdb, nr.phr, nr.pin, nr.psq, etc.) in `OUTPUT_pipeline/2-output/`
- Validation report in `OUTPUT_pipeline/3-output/`
- Symlinked to `output_to_input/BLOCK_ncbi_nr_blastp/` for downstream subprojects
