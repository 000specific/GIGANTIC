# OrthoFinder Workflow

Runs OrthoFinder orthogroup detection with Diamond similarity search and MCL clustering.

## Prerequisites

- genomesDB proteomes available
- `ai_gigantic_orthogroups` conda environment created (run `bash RUN-setup_environments.sh` at project root)

**Note:** `RUN-workflow.sh` automatically activates and deactivates the conda environment.

## Usage

```bash
# Edit configuration
vi START_HERE-user_config.yaml

# Run locally
bash RUN-workflow.sh

# Submit to SLURM (edit account/qos first)
sbatch RUN-workflow.sbatch
```

## Pipeline

6 steps: validate proteomes, prepare proteomes, run OrthoFinder (-X flag), standardize output, summary statistics, per-species QC.

See `ai/AI_GUIDE-orthofinder_workflow.md` for detailed execution guide.
