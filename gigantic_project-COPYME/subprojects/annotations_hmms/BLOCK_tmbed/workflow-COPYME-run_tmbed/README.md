# tmbed Workflow

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK: [`../AI_GUIDE.md`](../AI_GUIDE.md) — TMBed concepts
- Parent (subproject): [`../../README.md`](../../README.md)
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Reads from: `../../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs to: `../../output_to_input/BLOCK_tmbed/` (symlinks from `OUTPUT_pipeline/`)
- Downstream BLOCK: `../../BLOCK_build_annotation_database/workflow-COPYME-build_annotation_database/`
- 5 scripts; conda env `aiG-annotations_hmms-tmbed`

---

Runs tmbed transmembrane topology prediction across all genomesDB proteomes. tmbed uses protein language model embeddings to predict transmembrane helices, signal peptides, and inside/outside topology with high accuracy.

## Prerequisites

- genomesDB proteomes available in `INPUT_user/`
- `ai_tmbed` conda environment created
- GPU recommended for reasonable runtime (CPU mode supported but slow)

## Usage

```bash
vi START_HERE-user_config.yaml
bash RUN-workflow.sh         # Local
sbatch RUN-workflow.sh   # SLURM
```

## Pipeline

2 steps: validate proteome inputs, run tmbed prediction on each species proteome.

## Outputs

- Per-species 3-line format files with topology predictions (inside/outside/transmembrane per residue)
- Results published to `OUTPUT_pipeline/` and symlinked to `output_to_input/BLOCK_tmbed/`
