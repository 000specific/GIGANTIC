# Cross-Method Comparison Workflow

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 February 28 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK: [`../AI_GUIDE.md`](../AI_GUIDE.md) — BLOCK_comparison concepts
- Parent subproject: [`../../README.md`](../../README.md) — orthogroups overview
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Reads from: `../../output_to_input/BLOCK_*/` (standardized orthogroup tables from any tool BLOCK that has run)
- Outputs to: `../../output_to_input/BLOCK_comparison/` (cross-method comparison tables + visualizations)

---

Compares orthogroup detection results from any tool BLOCKs that have run (OrthoFinder, OrthoFinder_array, OrthoHMM, OrthoHMM_GIGANTIC, Broccoli).

## Prerequisites

- At least 2 of 3 tool projects must have completed pipelines
- Subproject-root `output_to_input/BLOCK_*/` directories must be populated
- `aiG-orthogroups-comparison` conda environment (auto-created on first run from `ai/conda_environment.yml` per §28)

**Note:** `RUN-workflow.sh` automatically activates and deactivates the conda environment.

## Usage

```bash
bash RUN-workflow.sh
# Or: sbatch RUN-workflow.sh
```

## Pipeline

2 steps: load standardized results from tool projects, compare methods (overlap, statistics, size distributions).

See `ai/AI_GUIDE.md` for detailed execution guide.
