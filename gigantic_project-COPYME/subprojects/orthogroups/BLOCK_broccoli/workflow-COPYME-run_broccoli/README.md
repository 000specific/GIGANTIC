# Broccoli Workflow

Runs Broccoli orthogroup detection with phylogenetic analysis and network-based label propagation.

## Prerequisites

- genomesDB proteomes available
- `ai_gigantic_orthogroups` conda environment created (run `bash RUN-setup_environments.sh` at project root)

**Note:** `RUN-workflow.sh` automatically activates and deactivates the conda environment.

## Usage

```bash
vi broccoli_config.yaml
bash RUN-workflow.sh
# Or: sbatch RUN-workflow.sbatch
```

## Pipeline

6 steps: validate proteomes, convert headers to short IDs, run Broccoli, restore GIGANTIC identifiers, summary statistics, per-species QC.

See `ai/AI_GUIDE-broccoli_workflow.md` for detailed execution guide.
