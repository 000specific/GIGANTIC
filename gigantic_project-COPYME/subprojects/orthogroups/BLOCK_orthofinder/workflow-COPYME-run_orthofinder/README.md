# OrthoFinder Workflow

Runs OrthoFinder orthogroup detection with Diamond similarity search and MCL clustering.

## Prerequisites

- `module load conda`
- `conda activate ai_gigantic_orthogroups`
- `module load nextflow`
- genomesDB proteomes available

## Usage

```bash
# Edit configuration
vi orthofinder_config.yaml

# Run locally
bash RUN-workflow.sh

# Submit to SLURM (edit account/qos first)
sbatch RUN-workflow.sbatch
```

## Pipeline

6 steps: validate proteomes, prepare proteomes, run OrthoFinder (-X flag), standardize output, summary statistics, per-species QC.

See `ai/AI_GUIDE-orthofinder_workflow.md` for detailed execution guide.
