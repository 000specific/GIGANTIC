# Cross-Method Comparison Workflow

Compares orthogroup detection results from OrthoFinder, OrthoHMM, and Broccoli.

## Prerequisites

- At least 2 of 3 tool projects must have completed pipelines
- Subproject-root `output_to_input/BLOCK_*/` directories must be populated
- `ai_gigantic_orthogroups` conda environment created (run `bash RUN-setup_environments.sh` at project root)

**Note:** `RUN-workflow.sh` automatically activates and deactivates the conda environment.

## Usage

```bash
bash RUN-workflow.sh
# Or: sbatch RUN-workflow.sbatch
```

## Pipeline

2 steps: load standardized results from tool projects, compare methods (overlap, statistics, size distributions).

See `ai/AI_GUIDE-comparison_workflow.md` for detailed execution guide.
