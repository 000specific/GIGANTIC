# workflow-COPYME-classify_dark_proteome

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 04 (workflow scripts)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (initial docs)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK: [`../AI_GUIDE.md`](../AI_GUIDE.md) — BLOCK_classify_dark_proteome
- Parent (subproject): [`../../README.md`](../../README.md) — dark_proteomes overview + 3-axis methodology
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Reads from (per axis):
  - axis_a: `../../../one_direction_homologs/output_to_input/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits/`
  - axis_b: `../../../orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC/orthogroups_gigantic_ids.tsv`
  - axis_c: `../../../annotations_hmms/output_to_input/BLOCK_interproscan_parsed/`
  - species: `../../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs to: `../../output_to_input/BLOCK_classify_dark_proteome/` (symlinks from `OUTPUT_pipeline/`)

---

## Purpose

Workflow template for the three-axis dark proteome classification
(Edsinger 2024). One workflow run processes all project species.

## Usage

```bash
cp -r workflow-COPYME-classify_dark_proteome workflow-RUN_1-classify_dark_proteome
cd workflow-RUN_1-classify_dark_proteome

# Edit reference species + upstream subproject paths + execution_mode
vi START_HERE-user_config.yaml

# Put species list (one phyloname per line) in INPUT_user/
vi INPUT_user/gigantic_species_list.txt

# Run (auto-creates conda env aiG-dark_proteomes on first run)
bash RUN-workflow.sh
```

`execution_mode` (in YAML) picks dispatch: `local` / `slurm` / `slurm_burst`.

## Inputs

| What | Where (config field) |
|------|----------------------|
| Proteomes | `proteomes_dir` |
| Reference BLAST hits (axis_a) | `reference_blast_dir` |
| Orthogroup table (axis_b) | `orthogroups_file` |
| HMM annotations (axis_c) | `hmm_annotations_dir` |
| Species list | `INPUT_user/gigantic_species_list.txt` |

## Outputs (in `OUTPUT_pipeline/`)

- `1-output/` — input-pairing manifest (per-species processability)
- `2-output/` — reference orthogroup set
- `3-output/` — per-species DARK/ANNOTATED classification tables
- `4-output/` — cross-species summary (dark counts, %, by clade)
- `5-output/` — run log

Symlinked into `../../output_to_input/BLOCK_classify_dark_proteome/`.

## See Also

- [`../AI_GUIDE.md`](../AI_GUIDE.md) — BLOCK-level guide
- [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md) — workflow execution guide
- [`../../README.md`](../../README.md) — subproject overview + Edsinger 2024 reference
