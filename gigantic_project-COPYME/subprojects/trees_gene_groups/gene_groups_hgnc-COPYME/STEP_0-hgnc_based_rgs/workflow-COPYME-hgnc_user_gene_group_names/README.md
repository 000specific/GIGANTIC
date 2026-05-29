# HGNC User Gene Group Names Workflow (MODE 3)

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 29
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent STEP guide: [`../AI_GUIDE.md`](../AI_GUIDE.md) — STEP_0 (hgnc_based_rgs) overview of all three modes
- Parent template: [`../../README.md`](../../README.md) — gene_groups_hgnc-COPYME
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Sibling modes:
  - [`../workflow-COPYME-hgnc_database/`](../workflow-COPYME-hgnc_database/) — MODE 1 (all ~2060 HGNC groups)
  - [`../workflow-COPYME-hgnc_user_gene_symbols/`](../workflow-COPYME-hgnc_user_gene_symbols/) — MODE 2 (user-supplied gene symbols)
- Reads from: `../../INPUT_user/user_gene_group_names.tsv` + HGNC public database + local GIGANTIC human T1 proteome
- Outputs to: `../../output_to_input/<INSTANCE_NAME>/STEP_0-hgnc_based_rgs/`

---

Takes a **user-supplied list of HGNC gene group names** (e.g. `Collagens`) or **`gg`-prefixed HGNC group IDs** (e.g. `gg483`) and emits per-group RGS FASTAs filtered to ONLY those groups, sourced from the local GIGANTIC human T1 proteome. Use when you already know which HGNC groups you want by name/ID — e.g. collagens, which span 7 HGNC groups in HGNC's taxonomy. Also emits a side-car `gene_symbol → hgnc_group_id → hgnc_group_name` annotation map for downstream tree-tip subgroup coloring.

## Prerequisites

- User-supplied group-names TSV at instance-level `../../INPUT_user/user_gene_group_names.tsv` (start from `user_gene_group_names_EXAMPLE.tsv`)
- A GIGANTIC human T1 proteome `.aa` file from a sibling `genomesDB` subproject (set its path in `START_HERE-user_config.yaml`)
- `aiG-trees_gene_groups-hgnc_based_rgs` conda environment (auto-created on first run from `ai/conda_environment.yml` per §28)
- Network access to genenames.org / storage.googleapis.com

**Note:** `RUN-workflow.sh` automatically activates and deactivates the conda environment.

## Usage

```bash
# Stage your user_gene_group_names.tsv at the instance level first
$EDITOR ../../INPUT_user/user_gene_group_names.tsv

vi START_HERE-user_config.yaml
bash RUN-workflow.sh
# Or: set execution_mode: "slurm" in START_HERE and run the same command to self-submit.
```

## Pipeline

4 scripts: download `hgnc_complete_set.txt`; download HGNC gene-group tables; resolve each user-supplied group name/ID against `family.csv` (case-insensitive; fail-fast with "did you mean…" suggestions on unknown), filter aggregated gene sets to those groups (with pseudogene-drop default; flags to keep); extract sequences from the human proteome and emit per-group RGS FASTAs + the gene_symbol → hgnc_group side-car map.

See [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md) for the detailed execution guide, input schema, resolution semantics, locus-type filter policy, and the side-car annotation map format.
