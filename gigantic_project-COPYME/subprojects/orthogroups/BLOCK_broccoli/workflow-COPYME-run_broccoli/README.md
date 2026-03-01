# Broccoli Workflow

Runs Broccoli orthogroup detection with phylogenetic analysis and network-based label propagation.

## Prerequisites

- `module load conda`
- `conda activate ai_gigantic_orthogroups`
- `module load nextflow`
- genomesDB proteomes available

## Usage

```bash
vi broccoli_config.yaml
bash RUN-workflow.sh
# Or: sbatch RUN-workflow.sbatch
```

## Pipeline

6 steps: validate proteomes, convert headers to short IDs, run Broccoli, restore GIGANTIC identifiers, summary statistics, per-species QC.

See `ai/AI_GUIDE-broccoli_workflow.md` for detailed execution guide.
