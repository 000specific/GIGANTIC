# tmbed Workflow

Runs tmbed transmembrane topology prediction across all genomesDB proteomes. tmbed uses protein language model embeddings to predict transmembrane helices, signal peptides, and inside/outside topology with high accuracy.

## Prerequisites

- genomesDB proteomes available in `INPUT_user/`
- `ai_tmbed` conda environment created
- GPU recommended for reasonable runtime (CPU mode supported but slow)

## Usage

```bash
vi START_HERE-user_config.yaml
bash RUN-workflow.sh         # Local
sbatch RUN-workflow.sbatch   # SLURM
```

## Pipeline

2 steps: validate proteome inputs, run tmbed prediction on each species proteome.

## Outputs

- Per-species 3-line format files with topology predictions (inside/outside/transmembrane per residue)
- Results published to `OUTPUT_pipeline/` and symlinked to `output_to_input/BLOCK_tmbed/`
