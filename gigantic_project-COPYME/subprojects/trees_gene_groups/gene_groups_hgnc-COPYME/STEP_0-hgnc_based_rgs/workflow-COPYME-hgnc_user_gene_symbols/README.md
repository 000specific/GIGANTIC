# HGNC User Gene Symbols Workflow (MODE 2)

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
  - [`../workflow-COPYME-hgnc_user_gene_group_names/`](../workflow-COPYME-hgnc_user_gene_group_names/) — MODE 3 (user-supplied HGNC group names/IDs)
- Reads from: `../../INPUT_user/user_gene_set.tsv` + HGNC complete-set + UniProt REST
- Outputs to: `../../output_to_input/<INSTANCE_NAME>/STEP_0-hgnc_based_rgs/`

---

Takes a **user-supplied list of human gene symbols** organized into one or more named groups and emits per-group RGS FASTAs. Each sequence is fetched from UniProt REST (the canonical Swiss-Prot record), keyed via HGNC's `uniprot_ids` cross-reference. Use when your group **isn't** a clean HGNC group — the canonical case is the SNAP family (SNAP23/25/29/47), since SNAP47 isn't in any HGNC group.

## Prerequisites

- Curated user-gene-set TSV at instance-level `../../INPUT_user/user_gene_set.tsv` (start from `user_gene_set_EXAMPLE.tsv`)
- `aiG-trees_gene_groups-hgnc_based_rgs` conda environment (auto-created on first run from `ai/conda_environment.yml` per §28)
- Network access to genenames.org + rest.uniprot.org

**Note:** `RUN-workflow.sh` automatically activates and deactivates the conda environment.

## Usage

```bash
# Stage your user_gene_set.tsv at the instance level first
$EDITOR ../../INPUT_user/user_gene_set.tsv

vi START_HERE-user_config.yaml
bash RUN-workflow.sh
# Lightweight: local execution recommended; SLURM supported but adds queue latency.
```

## Pipeline

3 scripts: download `hgnc_complete_set.txt`; resolve each user symbol → HGNC canonical symbol → UniProt accession (with alias and previous-symbol fallbacks; fail-fast on `NOT_FOUND` / `NO_UNIPROT`); fetch each UniProt FASTA and emit per-group RGS files.

See [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md) for the detailed execution guide.
