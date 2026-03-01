# Cross-Method Comparison Workflow

Compares orthogroup detection results from OrthoFinder, OrthoHMM, and Broccoli.

## Prerequisites

- At least 2 of 3 tool projects must have completed pipelines
- Tool `output_to_input/` directories must be populated
- `module load conda && conda activate ai_gigantic_orthogroups && module load nextflow`

## Usage

```bash
bash RUN-workflow.sh
# Or: sbatch RUN-workflow.sbatch
```

## Pipeline

2 steps: load standardized results from tool projects, compare methods (overlap, statistics, size distributions).

See `ai/AI_GUIDE-comparison_workflow.md` for detailed execution guide.
