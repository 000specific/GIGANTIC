# SignalP Workflow

Runs SignalP signal peptide prediction across all genomesDB proteomes. SignalP predicts the presence and location of signal peptide cleavage sites, identifying proteins targeted to the secretory pathway.

## Prerequisites

- genomesDB proteomes available in `INPUT_user/`
- `ai_signalp` conda environment created
- SignalP 6.0 manually downloaded from DTU Health Tech (academic license required)

## Usage

```bash
vi START_HERE-user_config.yaml
bash RUN-workflow.sh         # Local
sbatch RUN-workflow.sbatch   # SLURM
```

## Pipeline

2 steps: validate proteome inputs, run SignalP prediction on each species proteome.

## Outputs

- Per-species TSV files with signal peptide predictions, cleavage positions, and type classifications (Sec/SPI, Sec/SPII, Tat/SPI)
- Results published to `OUTPUT_pipeline/` and symlinked to `output_to_input/BLOCK_signalp/`
