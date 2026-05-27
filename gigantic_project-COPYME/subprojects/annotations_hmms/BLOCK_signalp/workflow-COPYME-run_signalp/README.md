# SignalP Workflow

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK: [`../AI_GUIDE.md`](../AI_GUIDE.md) — SignalP 6 concepts
- Parent (subproject): [`../../README.md`](../../README.md)
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Reads from: `../../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs to: `../../output_to_input/BLOCK_signalp/` (symlinks from `OUTPUT_pipeline/`)
- Downstream BLOCK: `../../BLOCK_build_annotation_database/workflow-COPYME-build_annotation_database/`
- 5 scripts; conda env `aiG-annotations_hmms-signalp`

---

Runs SignalP signal peptide prediction across all genomesDB proteomes. SignalP predicts the presence and location of signal peptide cleavage sites, identifying proteins targeted to the secretory pathway.

## Prerequisites

- genomesDB proteomes available in `INPUT_user/`
- `ai_signalp` conda environment created
- SignalP 6.0 manually downloaded from DTU Health Tech (academic license required)

## Usage

```bash
vi START_HERE-user_config.yaml
bash RUN-workflow.sh         # Local
sbatch RUN-workflow.sh   # SLURM
```

## Pipeline

2 steps: validate proteome inputs, run SignalP prediction on each species proteome.

## Outputs

- Per-species TSV files with signal peptide predictions, cleavage positions, and type classifications (Sec/SPI, Sec/SPII, Tat/SPI)
- Results published to `OUTPUT_pipeline/` and symlinked to `output_to_input/BLOCK_signalp/`
