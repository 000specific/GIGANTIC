# OrthoHMM Workflow

Runs OrthoHMM orthogroup detection with profile HMMs (HMMER) and MCL clustering.

## Prerequisites

- `module load conda`
- `conda activate ai_gigantic_orthogroups`
- `module load nextflow`
- genomesDB proteomes available

## Usage

```bash
vi orthohmm_config.yaml
bash RUN-workflow.sh
# Or: sbatch RUN-workflow.sbatch
```

## Pipeline

6 steps: validate proteomes, convert headers to short IDs, run OrthoHMM, restore GIGANTIC identifiers, summary statistics, per-species QC.

See `ai/AI_GUIDE-orthohmm_workflow.md` for detailed execution guide.
