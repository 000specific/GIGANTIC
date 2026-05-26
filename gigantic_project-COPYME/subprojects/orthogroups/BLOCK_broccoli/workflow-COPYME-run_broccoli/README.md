# Broccoli Workflow

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 February 28 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK: [`../AI_GUIDE.md`](../AI_GUIDE.md) — BLOCK_broccoli concepts
- Parent subproject: [`../../README.md`](../../README.md) — orthogroups overview
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Reads from: `../../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs to: `../../output_to_input/BLOCK_broccoli/`

---

Runs Broccoli orthogroup detection with phylogenetic analysis and network-based label propagation.

## Prerequisites

- genomesDB proteomes available
- `aiG-orthogroups-broccoli` conda environment (auto-created on first run from `ai/conda_environment.yml` per §28)

**Note:** `RUN-workflow.sh` automatically activates and deactivates the conda environment.

## Usage

```bash
vi START_HERE-user_config.yaml
bash RUN-workflow.sh
# Or: sbatch RUN-workflow.sh
```

## Pipeline

6 steps: validate proteomes, convert headers to short IDs, run Broccoli, restore GIGANTIC identifiers, summary statistics, per-species QC.

See `ai/AI_GUIDE.md` for detailed execution guide.
