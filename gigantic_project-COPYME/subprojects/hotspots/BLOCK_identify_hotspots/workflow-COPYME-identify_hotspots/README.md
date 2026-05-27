# workflow-COPYME-identify_hotspots

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 04 (workflow scripts)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (initial docs)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK: [`../AI_GUIDE.md`](../AI_GUIDE.md) — BLOCK_identify_hotspots (hotspot calling)
- Parent (subproject): [`../../README.md`](../../README.md) — hotspots overview + method
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Reads from:
  - `../../output_to_input/BLOCK_self_blast/self_blast_reports/` (upstream BLOCK output)
  - `../../../../research_notebook/research_user/subproject-hotspots/gene_coordinates/` (user-prepared)
  - `../../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs to: `../../output_to_input/BLOCK_identify_hotspots/`
- 5 scripts (validate / filter_by_evalue / identify_hotspots / summarize / `write_run_log` per §45)
- Conda env: `aiG-hotspots`

---

## Purpose

Workflow template for BLOCK_identify_hotspots. One run processes all
project species: filters self-BLAST hits by stringent e-value, identifies
paralog clusters within chromosomal windows, and emits per-species
hotspot tables + a cross-species summary.

## Prerequisites

1. **BLOCK_self_blast complete** — `../../output_to_input/BLOCK_self_blast/self_blast_reports/` populated
2. **Per-species gene_coordinates TSVs** in
   `../../../../research_notebook/research_user/subproject-hotspots/gene_coordinates/`
   (user produces from species-specific GFF/GTF; same TSV schema as
   gene_sizes Tier 2 — see gene_sizes README for column spec)
3. **genomesDB** complete (for proteome → Source_Gene_ID mapping)

## Usage

```bash
cp -r workflow-COPYME-identify_hotspots workflow-RUN_1-identify_hotspots
cd workflow-RUN_1-identify_hotspots

# Edit execution_mode + (optionally) e-value + window
vi START_HERE-user_config.yaml

# Run (auto-creates conda env aiG-hotspots on first run)
bash RUN-workflow.sh
```

## Inputs

`START_HERE-user_config.yaml`:
- `self_blast_reports_dir` (default points at upstream BLOCK_self_blast output)
- `gene_coordinates_dir` (default points at project-root sandbox per §1)
- `proteomes_dir` (default points at genomesDB STEP_4 species70)
- `evalue_threshold` (default 1e-60, per Edsinger 2024)
- `window_size_genes` (default 20, per Edsinger 2024)

## Outputs

- `OUTPUT_pipeline/1-output/` — input-pairing manifest (per-species processability)
- `OUTPUT_pipeline/2-output/` — evalue-filtered self-BLAST hits
- `OUTPUT_pipeline/3-output/` — per-species hotspot tables
- `OUTPUT_pipeline/4-output/` — cross-species hotspot summary
- `OUTPUT_pipeline/5-output/` — run log

Symlinked into `../../output_to_input/BLOCK_identify_hotspots/`.

## See Also

- [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md) — workflow execution + parameter tuning
- [`../AI_GUIDE.md`](../AI_GUIDE.md) — BLOCK concepts + §1/§17 deviation note
