# AI Guide: BLOCK_self_blast

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 04 (workflow scripts)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (initial docs)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (subproject AI guide): [`../AI_GUIDE.md`](../AI_GUIDE.md) — two-BLOCK sequential pipeline
- Parent (subproject README): [`../README.md`](../README.md)
- Workflow template: [`workflow-COPYME-self_blast/`](workflow-COPYME-self_blast/)
- This BLOCK's workflow AI guide: [`workflow-COPYME-self_blast/ai/AI_GUIDE.md`](workflow-COPYME-self_blast/ai/AI_GUIDE.md)
- Reads FROM: `../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs TO: `../output_to_input/BLOCK_self_blast/self_blast_reports/`
- Downstream BLOCK: `../BLOCK_identify_hotspots/` (consumes the self_blast_reports)
- 5 scripts (validate / chunk / blastp_chunk / concatenate / `write_run_log` per §45)
- Conda env: `aiG-hotspots` (shared with BLOCK_identify_hotspots per §53)

---

## Purpose

Run blastp of each species' proteome against itself. Produces one tabular
report per species, consumed downstream by BLOCK_identify_hotspots.

The per-species blastp would take many hours if run monolithically. This
workflow chunks each proteome into ~50 query chunks (~600 sequences each)
and fans the chunks out as a SLURM array on the burst QOS, then
concatenates per-species after all chunks complete.

Per-species fan-out math (species70 defaults):
- ~30k sequences ÷ 600 per chunk = ~50 chunks per species
- ~50 chunks × 70 species = ~3,500 fan-out tasks
- queueSize 200 × 5 cpus_per_task = ~1,000 concurrent CPUs (under burst cap)

## Pipeline (5 scripts)

| # | Script | Function |
|---|--------|----------|
| 001 | `validate_inputs.py` | Validate proteomes + species list; fail-fast |
| 002 | `chunk_proteomes.py` | Chunk each proteome into ~50 query chunks |
| 003 | `run_blastp_chunk.sh` | Per-chunk blastp (bash; fans out via SLURM array) |
| 004 | `concatenate_chunk_reports.py` | Concatenate chunks back to per-species reports |
| 005 | `write_run_log.py` | Timestamped run log per §45 |

## Cluster Notes

Burst-mode chunk dispatch is subject to the HiPerGator drain-node race
(see annotations_hmms AI_GUIDE for the canonical explanation + handling).
This BLOCK doesn't yet implement `errorStrategy='ignore'` + gap-detection
— if you hit the drain-node race here, port the pattern from
`annotations_hmms/BLOCK_interproscan`.

## See Also

- [`../AI_GUIDE.md`](../AI_GUIDE.md) — subproject overview
- [`workflow-COPYME-self_blast/ai/AI_GUIDE.md`](workflow-COPYME-self_blast/ai/AI_GUIDE.md) — workflow execution
