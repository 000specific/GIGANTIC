# AI_GUIDE.md (Level 3: Workflow Execution Guide)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — InterProScan 5 concepts
- Parent (subproject AI guide): [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- Workflow README: [`../README.md`](../README.md)
- Reads from: `../../../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs to: `../../../output_to_input/BLOCK_interproscan/`
- 6 scripts in `scripts/` (final = `write_run_log` per §45)
- Conda env: `aiG-annotations_hmms-interproscan`
- Note: Chunked + burst-friendly; see HiPerGator drain-node race note in subproject AI_GUIDE.

---

**For AI Assistants**: Read the BLOCK guide (`../AI_GUIDE.md`) first. This guide focuses on running the workflow.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../AI_GUIDE.md` |
| Annotations overview | `../../../AI_GUIDE.md` |
| InterProScan concepts | `../../AI_GUIDE.md` |
| Running the workflow | This file |

## Quick Start

```bash
vi START_HERE-user_config.yaml
bash RUN-workflow.sh
```

## Pipeline Steps

1. **Validate inputs** - Check proteome files exist and are valid FASTA format
2. **Chunk proteomes** - Split large proteomes into smaller batches for parallel InterProScan execution
3. **Run InterProScan** - Execute InterProScan on each chunk (configurable applications list)
4. **Combine results** - Merge per-chunk outputs into per-species annotation files
5. **Detect failed chunks** - Gap detection: writes `6_ai-failed_chunks.tsv` listing any chunks that did not produce results (see "Failure semantics" below)
6. **Write run log** - Final logging step

## Key Configuration

- `START_HERE-user_config.yaml` - Set InterProScan install path, database path, chunk size, and species list
- `INPUT_user/` - Proteome FASTA files or manifest pointing to genomesDB proteomes

## Verification Commands

```bash
# Check output files exist (one per species)
ls OUTPUT_pipeline/4-output/*.tsv | wc -l

# Check file sizes are reasonable (not empty)
wc -l OUTPUT_pipeline/4-output/*.tsv

# Check output headers
head -1 OUTPUT_pipeline/4-output/*.tsv

# Verify all species were processed
ls OUTPUT_pipeline/4-output/*.tsv | wc -l
ls INPUT_user/*.aa | wc -l
```

## Common Errors

| Error | Solution |
|-------|----------|
| `interproscan.sh: not found` | Set correct InterProScan install path in config YAML |
| `java.lang.OutOfMemoryError: Java heap space` | Increase Java heap in InterProScan config or reduce chunk size |
| `Out of memory` (system) | Reduce chunk size or request more memory in SLURM sbatch |
| `No input files found` | Check INPUT_user/ contains proteome files and config points to correct directory |
| Stale cached results after script update | Delete `work/` and `.nextflow*`, re-run without `-resume` |
| Chunk job dies with exit `0:53` in 1-2 sec, no log | Post-upgrade HiPerGator scheduler race allocating jobs to draining `c0706a-s*` nodes. NOT a pipeline bug — surfaces via `6_ai-failed_chunks.tsv` for follow-up. |

## Failure semantics (BLOCK-specific override)

This workflow uses `errorStrategy = 'ignore'` for the `run_interproscan` process — an **explicit, documented override** of the project CLAUDE.md default ("NEVER use 'ignore'"). Rationale:

- Burst mode submits 1000+ independent chunk jobs.
- A documented post-upgrade HiPerGator scheduler bug allocates a small percentage of jobs to draining nodes (exit code 0:53). With fail-fast, this kills the whole pipeline.
- With `'ignore'`, failed chunks produce no output but the other 1000+ chunks complete normally.
- Step 5 (`detect_failed_chunks`) emits `OUTPUT_pipeline/6-output/6_ai-failed_chunks.tsv` listing every chunk that did not produce a result.

### Recovering from failed chunks

After a run completes, inspect the manifest:

```bash
wc -l OUTPUT_pipeline/6-output/6_ai-failed_chunks.tsv   # header + N rows
cat OUTPUT_pipeline/6-output/6_ai-failed_chunks.tsv
```

To rerun just the failed chunks, build a new proteome manifest from the FASTA paths in column 3 and launch a follow-up RUN_N. (A helper to do this automatically may be added later.)

### Slurm-mode in-allocation parallelism (fix vs prior behavior)

The `withName: 'run_interproscan'` block uses `burst_cpus_per_chunk` / `burst_memory_gb_per_chunk` for per-chunk resources in BOTH `slurm` and `slurm_burst` modes. Previously slurm-mode used `params.cpus` per chunk — which meant each chunk consumed the entire allocation, forcing chunks to run **sequentially** within the single SLURM job (defeating the purpose of the allocation). With the corrected sizing, multiple chunks run in parallel within the slurm-mode allocation up to `allocation_cpus / burst_cpus_per_chunk` concurrency.
