# workflow-COPYME-self_blast

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 04 (workflow scripts)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (initial docs)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK: [`../AI_GUIDE.md`](../AI_GUIDE.md) — BLOCK_self_blast (chunked self-blastp)
- Parent (subproject): [`../../README.md`](../../README.md) — hotspots overview
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Reads from: `../../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs to: `../../output_to_input/BLOCK_self_blast/self_blast_reports/` (symlinks from `OUTPUT_pipeline/`)
- Downstream BLOCK: `../../BLOCK_identify_hotspots/workflow-COPYME-identify_hotspots/`
- 5 scripts (validate / chunk / blastp_chunk / concatenate / `write_run_log` per §45)
- Conda env: `aiG-hotspots`

---

## Purpose

Workflow template for BLOCK_self_blast. One workflow run processes all
project species: chunks each proteome (~50 chunks × 70 species = ~3,500
fan-out tasks) and runs per-chunk blastp on burst QOS.

## Usage

```bash
cp -r workflow-COPYME-self_blast workflow-RUN_1-self_blast
cd workflow-RUN_1-self_blast

# Edit execution_mode + SLURM resources (slurm_burst recommended for
# species70 — chunk count is large)
vi START_HERE-user_config.yaml

# Run (auto-creates conda env aiG-hotspots on first run; self-submits to
# SLURM per execution_mode)
bash RUN-workflow.sh
```

## Inputs

- `START_HERE-user_config.yaml`:
  - `proteomes_dir` (default: genomesDB STEP_4 species70 path)
  - `chunk_size` (default 600 sequences per chunk)
  - `execution_mode` (local / slurm / slurm_burst)
  - blast parameters (evalue, threads, etc.)

## Outputs

- `OUTPUT_pipeline/1-output/` — validated proteome list
- `OUTPUT_pipeline/2-output/` — chunked query FASTAs
- `OUTPUT_pipeline/3-output/` — per-chunk blastp tab reports
- `OUTPUT_pipeline/4-output/` — concatenated per-species reports
- `OUTPUT_pipeline/5-output/` — run log

Symlinked into `../../output_to_input/BLOCK_self_blast/self_blast_reports/`.

## Cluster Notes

The per-chunk fan-out is subject to the HiPerGator drain-node race (see
annotations_hmms AI_GUIDE for full diagnosis + canonical handling pattern
of `errorStrategy='ignore'` + gap-detection). This workflow doesn't yet
implement the gap-detection step; if you hit 1-3% chunk losses, port the
pattern from annotations_hmms/BLOCK_interproscan.

## See Also

- [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md) — workflow execution
- [`../AI_GUIDE.md`](../AI_GUIDE.md) — BLOCK concepts
