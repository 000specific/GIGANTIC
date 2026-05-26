# InterProScan Workflow

Runs InterProScan domain and function annotation across all genomesDB proteomes. InterProScan integrates 19 component databases (Pfam, PANTHER, CDD, Gene3D, SUPERFAMILY, etc.) and assigns GO terms, providing comprehensive protein domain and function annotation.

## Prerequisites

- genomesDB proteomes available in `INPUT_user/proteome_manifest.tsv`
- `aiG-annotations_hmms-interproscan` conda environment (auto-created by `RUN-workflow.sh` from `ai/conda_environment.yml`)
- InterProScan standalone installation (download once via `BLOCK_interproscan/DOWNLOAD_SOFTWARE-interproscan.sh`; path goes in `START_HERE-user_config.yaml`)
- Java 11+ provided by the conda env
- Sufficient disk space for InterProScan databases (~80 GB)

## Usage

```bash
vi START_HERE-user_config.yaml      # set applications, execution_mode, resources, slurm account/qos
bash RUN-workflow.sh                # unified entry — self-submits to SLURM if execution_mode is slurm or slurm_burst
```

The legacy `RUN-workflow.sbatch` is deprecated; use `RUN-workflow.sh` with `execution_mode` in YAML.

## Pipeline (6 steps)

1. **validate_proteome_manifest** — check all proteome paths resolve.
2. **chunk_proteomes** — split each proteome into N-sequence chunks (`chunk_size` in YAML).
3. **run_interproscan** — one InterProScan invocation per chunk (all configured `applications` in one call). Uses `errorStrategy = 'ignore'` so individual chunk failures do not kill the pipeline (see "Failure semantics" below).
4. **combine_interproscan_results** — merge chunk TSVs back into one TSV per species.
5. **detect_failed_chunks** — diff expected vs successful chunks, write `6_ai-failed_chunks.tsv` listing any chunks that did not produce output.
6. **write_run_log** — final log entry.

## Outputs

- `OUTPUT_pipeline/1-output/` — validated manifest + log
- `OUTPUT_pipeline/2-output/` — `<phyloname>_chunk_NNN.fasta` files (expected chunks; the truth set for gap detection)
- `OUTPUT_pipeline/3-output/` — `<phyloname>_chunk_NNN_interproscan.tsv` files (one per successful chunk)
- `OUTPUT_pipeline/4-output/` — `<phyloname>_interproscan_results.tsv` (one per species, merged)
- `OUTPUT_pipeline/6-output/6_ai-failed_chunks.tsv` — gap-detection manifest (header + one row per chunk that died, empty body if no failures)
- Symlinks to `output_to_input/BLOCK_interproscan/` (created by RUN-workflow.sh after pipeline completes)

## Failure semantics (explicit `errorStrategy = 'ignore'` override)

This workflow runs `errorStrategy = 'ignore'` on the `run_interproscan` process — overriding the project CLAUDE.md default of "NEVER use 'ignore'" with explicit documented intent. Rationale:

- Burst mode submits hundreds-to-thousands of independent chunk jobs.
- A documented post-HiPerGator-upgrade scheduler bug allocates a small fraction (~1-3%) of jobs to draining nodes. The job dies in 0-1 sec with `ExitCode 0:53` (SIGRTMIN+19), no `.command.log`. This is a cluster-side bug, not a workflow bug. See `../AI_GUIDE-interproscan.md` and `../../AI_GUIDE-annotations_hmms.md` (section "HiPerGator Drain-Node Race") for the full diagnosis.
- With fail-fast (`'terminate'`), one drain-node hit kills a multi-day run after potentially hours of work. With `'ignore'`, only the dead chunks are lost; the other ~98% completes normally.
- Step 5 (`detect_failed_chunks`) makes the dropped chunks visible so the user can drive a follow-up RUN_N from the manifest.

## Recovery from failed chunks

After the run finishes:

```bash
# How many chunks failed?
wc -l OUTPUT_pipeline/6-output/6_ai-failed_chunks.tsv   # header + N rows

# Which species and chunks?
column -t -s$'\t' OUTPUT_pipeline/6-output/6_ai-failed_chunks.tsv | head
```

To rerun just the failed chunks: build a new proteome manifest pointing at the FASTA paths from column 3 of `6_ai-failed_chunks.tsv` and launch a new RUN_N. (A helper to do this automatically may be added later.)

## In-allocation parallelism (slurm mode)

The `withName: 'run_interproscan'` process uses `burst_cpus_per_chunk` / `burst_memory_gb_per_chunk` for per-chunk resources in **both** `slurm` and `slurm_burst` modes. In slurm mode the outer SLURM allocation is sized by `cpus` / `memory_gb` (the YAML knobs at the top of the resource block), and N chunks run in parallel within that allocation up to `cpus / burst_cpus_per_chunk` concurrency. Previously slurm mode used `params.cpus` per chunk — meaning each chunk consumed the entire allocation and chunks ran sequentially. The current behavior actually parallelizes within the allocation.
