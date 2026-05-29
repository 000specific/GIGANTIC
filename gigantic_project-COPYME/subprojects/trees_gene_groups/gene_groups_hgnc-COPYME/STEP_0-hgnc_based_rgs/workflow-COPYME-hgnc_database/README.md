# HGNC Database Workflow (MODE 1)

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 29
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent STEP guide: [`../AI_GUIDE.md`](../AI_GUIDE.md) — STEP_0 (hgnc_based_rgs) overview of all three modes
- Parent template: [`../../README.md`](../../README.md) — gene_groups_hgnc-COPYME
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Sibling modes:
  - [`../workflow-COPYME-hgnc_user_gene_symbols/`](../workflow-COPYME-hgnc_user_gene_symbols/) — MODE 2 (user-supplied gene symbols)
  - [`../workflow-COPYME-hgnc_user_gene_group_names/`](../workflow-COPYME-hgnc_user_gene_group_names/) — MODE 3 (user-supplied HGNC group names/IDs)
- Reads from: HGNC public database (network download) + local GIGANTIC human T1 proteome
- Outputs to: `../../output_to_input/<INSTANCE_NAME>/STEP_0-hgnc_based_rgs/`

---

Batch-processes **all ~2060 HGNC-curated gene groups** and emits one RGS FASTA per group. Sequences come from the local GIGANTIC human T1 proteome. Use when you want comprehensive coverage of HGNC's classification (e.g., the reference universe of every HGNC gene group, then STEP_1 run across all of them).

## Prerequisites

- A GIGANTIC human T1 proteome `.aa` file from a sibling `genomesDB` subproject (set its path in `START_HERE-user_config.yaml`)
- `aiG-trees_gene_groups-hgnc_based_rgs` conda environment (auto-created on first run from `ai/conda_environment.yml` per §28)
- Network access to genenames.org / storage.googleapis.com

**Note:** `RUN-workflow.sh` automatically activates and deactivates the conda environment.

## Usage

```bash
vi START_HERE-user_config.yaml
bash RUN-workflow.sh
# Or: set execution_mode: "slurm" in START_HERE and run the same command to self-submit.
```

## Pipeline

4 scripts: download `hgnc_complete_set.txt`; download HGNC gene-group tables; build aggregated gene sets (per-group symbol roll-ups); extract sequences from the human proteome and emit per-group RGS FASTAs.

See [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md) for the detailed execution guide.
