# OrthoHMM Workflow

Runs OrthoHMM orthogroup detection with profile HMMs (HMMER) and MCL clustering.

## Prerequisites

- genomesDB proteomes available
- `ai_gigantic_orthogroups` conda environment created (run `bash RUN-setup_environments.sh` at project root)

**Note:** `RUN-workflow.sh` automatically activates and deactivates the conda environment.

## Usage

```bash
vi orthohmm_config.yaml
bash RUN-workflow.sh
# Or: sbatch RUN-workflow.sbatch
```

## Pipeline

6 steps: validate proteomes, convert headers to short IDs, run OrthoHMM, restore GIGANTIC identifiers, summary statistics, per-species QC.

See `ai/AI_GUIDE-orthohmm_workflow.md` for detailed execution guide.
