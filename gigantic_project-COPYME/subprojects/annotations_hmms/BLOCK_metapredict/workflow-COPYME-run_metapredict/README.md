# MetaPredict Workflow

Runs MetaPredict intrinsic disorder prediction across all genomesDB proteomes. MetaPredict predicts per-residue disorder scores, identifying intrinsically disordered regions (IDRs) that lack stable 3D structure and play key roles in signaling, regulation, and protein-protein interactions.

## Prerequisites

- genomesDB proteomes available in `INPUT_user/`
- `ai_metapredict` conda environment created
- No additional downloads required (lightweight, CPU-only tool)

## Usage

```bash
vi START_HERE-user_config.yaml
bash RUN-workflow.sh         # Local
sbatch RUN-workflow.sbatch   # SLURM
```

## Pipeline

2 steps: validate proteome inputs, run MetaPredict disorder prediction on each species proteome.

## Outputs

- Per-species TSV files with per-residue disorder scores and disordered region boundaries
- Results published to `OUTPUT_pipeline/` and symlinked to `output_to_input/BLOCK_metapredict/`
