# MetaPredict Workflow

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK: [`../AI_GUIDE.md`](../AI_GUIDE.md) — MetaPredict concepts
- Parent (subproject): [`../../README.md`](../../README.md)
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Reads from: `../../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs to: `../../output_to_input/BLOCK_metapredict/` (symlinks from `OUTPUT_pipeline/`)
- Downstream BLOCK: `../../BLOCK_build_annotation_database/workflow-COPYME-build_annotation_database/`
- 4 scripts; conda env `aiG-annotations_hmms-metapredict`

---

Runs MetaPredict intrinsic disorder prediction across all genomesDB proteomes. MetaPredict predicts per-residue disorder scores, identifying intrinsically disordered regions (IDRs) that lack stable 3D structure and play key roles in signaling, regulation, and protein-protein interactions.

## Prerequisites

- genomesDB proteomes available in `INPUT_user/`
- `ai_metapredict` conda environment created
- No additional downloads required (lightweight, CPU-only tool)

## Usage

```bash
vi START_HERE-user_config.yaml
bash RUN-workflow.sh         # Local
sbatch RUN-workflow.sh   # SLURM
```

## Pipeline

2 steps: validate proteome inputs, run MetaPredict disorder prediction on each species proteome.

## Outputs

- Per-species TSV files with per-residue disorder scores and disordered region boundaries
- Results published to `OUTPUT_pipeline/` and symlinked to `output_to_input/BLOCK_metapredict/`
