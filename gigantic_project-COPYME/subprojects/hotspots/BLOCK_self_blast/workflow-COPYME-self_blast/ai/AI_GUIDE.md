# AI Guide: self_blast Workflow

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 04 (workflow scripts)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (initial docs)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — BLOCK_self_blast concepts
- Parent (subproject AI guide): [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md) — hotspots overview
- Parent (project): [`../../../../AI_GUIDE.md`](../../../../AI_GUIDE.md)
- Workflow README: [`../README.md`](../README.md)
- Reads from: `../../../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs to: `../../../output_to_input/BLOCK_self_blast/self_blast_reports/`
- 5 scripts (validate / chunk / blastp_chunk bash / concatenate / `write_run_log`)
- Conda env: `aiG-hotspots`

---

## Pipeline (5 NextFlow processes)

| # | Script | Process Label | Function |
|---|--------|---------------|----------|
| 001 | `validate_inputs.py` | `local_step` | Validate proteomes + species list |
| 002 | `chunk_proteomes.py` | `local_step` | Chunk each proteome into ~50 query chunks |
| 003 | `run_blastp_chunk.sh` | `blastp_chunk` | Per-chunk blastp (SLURM array on burst QOS) |
| 004 | `concatenate_chunk_reports.py` | `local_step` | Concatenate chunks → per-species reports |
| 005 | `write_run_log.py` | `local_step` | Timestamped run log per §45 |

## Process Labels (defined in nextflow.config)

- `local_step` — Lightweight Python steps in the driver (validate, chunk, merge, log)
- `blastp_chunk` — One SLURM job per chunk on burst QOS; retries on transient failures

## execution_mode

Set in `START_HERE-user_config.yaml`:
- `local` — sequential on the head node (impractical for species70)
- `slurm` — single SLURM allocation; chunks run serial within it
- `slurm_burst` — chunks fan out as separate burst-QOS jobs (default + recommended)

## Tuning

Default per-species fan-out math (species70):
- ~30k sequences ÷ 600 per chunk = ~50 chunks per species
- 50 chunks × 70 species = ~3,500 fan-out tasks
- queueSize 200 × 5 cpus_per_task = ~1,000 concurrent CPUs (under burst cap)

For different species sets:
- Smaller (~30 species): keep defaults; finishes faster
- Larger (~150+ species): consider increasing chunk_size to reduce task count
- Per-chunk cpus_per_task is set in nextflow.config; bump if individual chunks run too slow

## Drain-Node Race

See annotations_hmms `AI_GUIDE.md` for the canonical HiPerGator drain-node
race diagnosis (~1-3% of burst chunks die in 0-1 sec with ExitCode 0:53,
no `.command.log`). If you observe this here, port the pattern from
annotations_hmms/BLOCK_interproscan: `errorStrategy='ignore'` on
`blastp_chunk` + a `detect_failed_chunks` script that compares expected
vs successful chunks and emits a rerun manifest.

## See Also

- [`../README.md`](../README.md) — workflow usage
- [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — BLOCK concepts
- annotations_hmms `AI_GUIDE.md` — drain-node race canonical reference
