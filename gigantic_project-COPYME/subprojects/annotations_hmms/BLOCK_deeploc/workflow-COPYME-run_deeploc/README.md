# DeepLoc Workflow

Runs DeepLoc subcellular localization prediction across all genomesDB proteomes. DeepLoc uses deep learning to predict protein localization to 10 subcellular compartments (nucleus, cytoplasm, extracellular, membrane, mitochondrion, etc.).

## Prerequisites

- genomesDB proteomes available in `INPUT_user/`
- `ai_deeploc` conda environment created
- DeepLoc manually downloaded from DTU Health Tech (academic license required)
- GPU recommended for reasonable runtime (CPU mode is very slow)

## Usage

```bash
vi deeploc_config.yaml
bash RUN-workflow.sh         # Local
sbatch RUN-workflow.sbatch   # SLURM
```

## Pipeline

2 steps: validate proteome inputs, run DeepLoc prediction on each species proteome.

## Outputs

- Per-species TSV files with localization predictions and confidence scores
- Results published to `OUTPUT_pipeline/` and symlinked to `output_to_input/BLOCK_deeploc/`
