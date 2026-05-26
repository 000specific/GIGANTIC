# OrthoHMM Workflow

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 February 28 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK: [`../AI_GUIDE.md`](../AI_GUIDE.md) — BLOCK_orthohmm concepts
- Parent subproject: [`../../README.md`](../../README.md) — orthogroups overview
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Reads from: `../../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs to: `../../output_to_input/BLOCK_orthohmm/`
- Parallel variant (≥30 species): `../../BLOCK_orthohmm_GIGANTIC/workflow-COPYME-run_orthohmm_GIGANTIC/`

---

Runs OrthoHMM orthogroup detection with profile HMMs (HMMER) and MCL clustering.

## Prerequisites

- genomesDB proteomes available
- `aiG-orthogroups-orthohmm` conda environment (auto-created on first run from `ai/conda_environment.yml` per §28)

**Note:** `RUN-workflow.sh` automatically activates and deactivates the conda environment.

## Usage

```bash
vi START_HERE-user_config.yaml
bash RUN-workflow.sh
# Or: sbatch RUN-workflow.sh
```

## Pipeline

6 steps: validate proteomes, convert headers to short IDs, run OrthoHMM, restore GIGANTIC identifiers, summary statistics, per-species QC.

See `ai/AI_GUIDE.md` for detailed execution guide.
