# DeepLoc Workflow

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK: [`../AI_GUIDE.md`](../AI_GUIDE.md) — DeepLoc 2.1 concepts
- Parent (subproject): [`../../README.md`](../../README.md)
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Reads from: `../../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs to: `../../output_to_input/BLOCK_deeploc/` (symlinks from `OUTPUT_pipeline/`)
- Downstream BLOCK: `../../BLOCK_build_annotation_database/workflow-COPYME-build_annotation_database/`
- 3 scripts; conda env `aiG-annotations_hmms-deeploc`

---

Runs DeepLoc subcellular localization prediction across all genomesDB proteomes. DeepLoc uses deep learning to predict protein localization to 10 subcellular compartments (nucleus, cytoplasm, extracellular, membrane, mitochondrion, etc.).

## Prerequisites

- genomesDB proteomes available in `INPUT_user/`
- `ai_deeploc` conda environment created
- DeepLoc manually downloaded from DTU Health Tech (academic license required)
- GPU recommended for reasonable runtime (CPU mode is very slow)

## Usage

```bash
vi START_HERE-user_config.yaml
bash RUN-workflow.sh         # Local
sbatch RUN-workflow.sh   # SLURM
```

## Pipeline

2 steps: validate proteome inputs, run DeepLoc prediction on each species proteome.

## Outputs

- Per-species TSV files with localization predictions and confidence scores
- Results published to `OUTPUT_pipeline/` and symlinked to `output_to_input/BLOCK_deeploc/`
