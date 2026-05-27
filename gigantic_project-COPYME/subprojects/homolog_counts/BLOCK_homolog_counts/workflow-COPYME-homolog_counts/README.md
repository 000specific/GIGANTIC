# workflow-COPYME-homolog_counts

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 22 (initial scripts; in commit 8486969 sweep)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (initial README)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK: [`../`](../) — BLOCK_homolog_counts (the only BLOCK in this subproject)
- Parent (subproject): [`../../README.md`](../../README.md) — homolog_counts overview
- Parent (subproject AI guide): [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — Level 2 concepts + output schema
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Reads from:
  - `../../../orthogroups/output_to_input/BLOCK_orthohmm/`
  - `../../../trees_gene_groups/output_to_input/gene_groups-hugo_hgnc/`
  - `../../../trees_gene_families/output_to_input/`
  - species70 phyloname map in `INPUT_user/`
- Outputs to: `../../output_to_input/BLOCK_homolog_counts/` (symlinks from `OUTPUT_pipeline/`)
- 6 scripts (001 validate / 002-004 count three sources / 005 `write_run_log` per §45 / 006 rewrite column headers)
- Conda env: `aiG-homolog_counts-homolog_counts`

---

## Purpose

Single-template workflow for the homolog_counts BLOCK. Reads three upstream
subprojects, produces three wide TSVs (one per source) keyed on the
source-specific Feature_ID and one column per species70 species.

## Usage

```bash
# 1. Copy this template
cp -r workflow-COPYME-homolog_counts workflow-RUN_1-homolog_counts
cd workflow-RUN_1-homolog_counts

# 2. Edit config — set execution_mode (local / slurm) and verify the four
#    upstream paths (3 subprojects + species70 phyloname map)
vi START_HERE-user_config.yaml

# 3. Run (single entry point per §29; auto-creates conda env on first run)
bash RUN-workflow.sh
```

## Inputs

- `START_HERE-user_config.yaml` — `inputs:` block specifies relative paths to:
  - `orthogroups/output_to_input/BLOCK_orthohmm/`
  - `trees_gene_groups/output_to_input/gene_groups-hugo_hgnc/`
  - `trees_gene_families/output_to_input/`
  - species70 phyloname map (`species70_map-genus_species_X_phylonames.tsv`)

## Outputs

In `OUTPUT_pipeline/`:
- `1-output/` — validated species70 alphabetical phyloname order (used by all 3 counters)
- `2-output/` — orthohmm orthogroup counts wide TSV
- `3-output/` — HGNC gene group counts wide TSV
- `4-output/` — curated gene family counts wide TSV
- `5-output/` — run log
- `6-output/` — column-header-normalized TSVs (post-pipeline pass)

Symlinked into `../../output_to_input/BLOCK_homolog_counts/`.

## See Also

- [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md) — workflow execution guide (step-by-step)
- [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — subproject concepts + output schema
