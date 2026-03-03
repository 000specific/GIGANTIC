# InterProScan Workflow

Runs InterProScan domain and function annotation across all genomesDB proteomes. InterProScan integrates 19 component databases (Pfam, PANTHER, CDD, Gene3D, SUPERFAMILY, etc.) and assigns GO terms, providing comprehensive protein domain and function annotation.

## Prerequisites

- genomesDB proteomes available in `INPUT_user/`
- `ai_interproscan` conda environment created
- InterProScan standalone installation (requires manual download from EBI)
- Java 11+ available on system
- Sufficient disk space for InterProScan databases (~80 GB)

## Usage

```bash
vi interproscan_config.yaml
bash RUN-workflow.sh         # Local
sbatch RUN-workflow.sbatch   # SLURM
```

## Pipeline

4 steps: validate proteome inputs, chunk proteomes into batches for parallel processing, run InterProScan on each chunk, combine results into per-species annotation files.

## Outputs

- Per-species TSV files with domain hits, GO terms, and pathway annotations
- Results published to `OUTPUT_pipeline/` and `ai/output_to_input/`
