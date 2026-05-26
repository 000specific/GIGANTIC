# AI_GUIDE — BLOCK_orthofinder_array (orthogroups; parallel-DIAMOND variant)

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

**For AI Assistants**: Read `../AI_GUIDE.md` first for subproject overview and tool comparison. This guide covers OrthoFinder-array-specific concepts (parallel-DIAMOND SLURM array fan-out).

## Where this fits

- Parent subproject: [`../AI_GUIDE.md`](../AI_GUIDE.md) — orthogroups overview + tool comparison
- Parent project: [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- Sibling BLOCK (standard variant): [`../BLOCK_orthofinder/`](../BLOCK_orthofinder/) — simpler, fine for < 20 species
- Workflow to run: [`workflow-COPYME-run_orthofinder_array/README.md`](workflow-COPYME-run_orthofinder_array/README.md)
- Reads from: `../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs to: `../output_to_input/BLOCK_orthofinder_array/` (standardized orthogroups table per §38, §2; bit-identical to BLOCK_orthofinder)

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../AI_GUIDE.md` |
| Orthogroups overview, tool comparison | `../AI_GUIDE.md` |
| Standard (non-arrayed) OrthoFinder | `../BLOCK_orthofinder/AI_GUIDE.md` |
| **Parallel-DIAMOND (this BLOCK) concepts** | This file |
| Running the parallel workflow | `workflow-COPYME-run_orthofinder_array/ai/AI_GUIDE.md` |

## Why This BLOCK Exists

For 70 species, OrthoFinder's all-vs-all DIAMOND step is the dominant cost
(N² = 4,900 pairwise alignments) and standard OrthoFinder takes days. Even
though DIAMOND is much faster than phmmer per call, the wall time
accumulates. **BLOCK_orthofinder_array** parallelizes the DIAMOND step
across SLURM burst-mode job arrays, mirroring the architecture of
`BLOCK_orthohmm_GIGANTIC`.

## Architecture (Parallel Fan-Out)

```
[001 validate]    [002 prepare proteomes]    [003 extract DIAMOND cmds via -op]
                                                           │
                                            (~4,830 (taxa_a, taxa_b) pairs)
                                                           ↓
                            ┌──────── FAN-OUT (NextFlow SLURM array, burst QOS) ────────┐
                            │                                                            │
                            │   [004 run_diamond_pair × ~4,830 SLURM array tasks,       │
                            │    2 cpu / 15 GB / 2 h each, on moroz-b]                  │
                            │                                                            │
                            └────────────────────────── pool ──────────────────────────────┘
                                                           ↓
[005 pool & verify DIAMOND outputs]    [006 OrthoFinder -b (clustering + trees + recon)]
                                                           ↓
[007 standardize]    [008 summary]    [009 QC]    [010 run log]
```

Two OrthoFinder flags make this clean:

- `orthofinder -op` → prepares files, runs makeblastdb (or diamond makedb),
  prints all DIAMOND/BLAST command lines, and exits before running any
  searches. **Consistency guarantee:** the parallel tasks invoke DIAMOND
  with bit-identical args to what native OrthoFinder would have run.
- `orthofinder -b <dir>` → resumes from pre-computed search results,
  skipping the search step. Runs orthogroup clustering + gene-tree
  inference + species-tree + duplication/loss reconciliation.

## Key Differences vs `BLOCK_orthofinder`

| | `BLOCK_orthofinder` (standard) | `BLOCK_orthofinder_array` (parallel) |
|---|---|---|
| DIAMOND step | One process; OrthoFinder runs all pairs sequentially or with `-t N` threading | ~4,830 SLURM array tasks via burst QOS |
| `process.array` | n/a | `100` (49 array submissions, scheduler-friendly) |
| Wall time on 70 species | Days (per user experience) | Hours |
| Tree inference | Same — runs in finalize stage | Same — runs in process 6 (`orthofinder -b`) |
| Scripts | 7 | 9 (3 new for fan-out architecture) |

## SLURM Resource Profile (defaults in COPYME yaml)

- **Driver job** (orchestrates NextFlow): 4 cpu / 30 GB / 10 d on `moroz` QOS
- **DIAMOND pair** (each fan-out task): 2 cpu / 15 GB / 2 h on `moroz-b` (burst)
- **OrthoFinder finalize** (`-b` resume; clustering + trees + reconciliation): 48 cpu / 360 GB / 96 h
- HiPerGator convention: `memory_gb = 7.5 × cpus`. To unlock more memory, increase cpus.

**Why DIAMOND pair resources are smaller than phmmer pair:** DIAMOND is much
faster per call than phmmer and doesn't have phmmer's poor multi-thread
scaling issue, so 2 cpu / 15 GB / 2 h covers the average case with margin.

**Why finalize is bigger than orthohmm's:** OrthoFinder's `-b` resume runs
gene-tree inference (one tree per orthogroup) which dominates the
post-search wall time and benefits from many cores.

## Etiquette and HiPerGator Policy

Same as `BLOCK_orthohmm_GIGANTIC`:
- ~4,830 array elements, under UF's 10,000 prior-approval threshold
- `process.array = 100` bundles into ~49 real SLURM array submissions
- Burst QOS for fan-out, regular QOS for the long-running driver

## Directory Structure

```
BLOCK_orthofinder_array/
├── AI_GUIDE.md            # THIS FILE
└── workflow-COPYME-run_orthofinder_array/
    ├── README.md                            # User-facing how-to
    ├── START_HERE-user_config.yaml          # User config
    ├── RUN-workflow.sh                      # Single entry point (self-submits to SLURM)
    └── ai/
        ├── AI_GUIDE.md   # Level 3 workflow guide
        ├── main.nf                          # NextFlow pipeline (10 processes)
        ├── nextflow.config                  # yaml-driven, SLURM executor for fan-out
        └── scripts/
            ├── 001_ai-python-validate_proteomes.py
            ├── 002_ai-python-prepare_proteomes.py
            ├── 003_ai-python-extract_orthofinder_search_commands.py  ← NEW
            ├── 005_ai-python-pool_and_verify_diamond_outputs.py      ← NEW
            ├── 006_ai-bash-run_orthofinder_from_blast.sh             ← NEW
            ├── 007_ai-python-standardize_output.py
            ├── 008_ai-python-generate_summary_statistics.py
            ├── 009_ai-python-qc_analysis_per_species.py
            └── 010_ai-python-write_run_log.py
```

(Note: there is no separate script `004` — the DIAMOND pair fan-out runs
inline as a NextFlow process script that just executes the captured
command line. No wrapper script needed.)

## Outputs (consumed downstream)

`output_to_input/BLOCK_orthofinder_array/`:
- `orthogroups_gigantic_ids.tsv`
- `gene_count_gigantic_ids.tsv`
- `summary_statistics.tsv`
- `per_species_summary.tsv`

Filenames match `BLOCK_orthofinder` and `BLOCK_orthohmm_GIGANTIC` so
downstream subprojects (e.g., `BLOCK_comparison`) can consume from any.

## Configuration Knobs

Edit `START_HERE-user_config.yaml`:
- `inputs.proteomes_dir` — points at genomesDB STEP_4 output
- `orthofinder.search_method` — `diamond` (default) or `blast`
- `orthofinder.mcl_inflation` — MCL `-I` parameter (default `1.5`)
- `resources.diamond_pair.{cpus,memory_gb,time_hours}` — per-pair fan-out task
- `resources.orthofinder_finalize.{cpus,memory_gb,time_hours}` — finalize stage
- `slurm_account`, `slurm_qos` (driver) / `slurm_burst_account`, `slurm_burst_qos` (fan-out)
- `slurm_mail_user` — email on END/FAIL

## Troubleshooting

| Error | Cause | Solution |
|---|---|---|
| "input file name collision -- multiple input files for: null" | Manifest TSV header uses GIGANTIC self-documenting style; NextFlow's splitCsv returns null keys | Already fixed in script 003 (simple bare headers). See feedback memory. |
| OrthoFinder `-op` fails | Tool not in conda env or args wrong | Check conda env `aiG-orthogroups-orthofinder` is activated; check 3_ai-orthofinder_op_stdout.txt |
| Empty pair outputs flagged | Some species pairs have no detectable similarity | Biologically valid for distant pairs; review 5_ai-pool_verification_report.tsv |
| Missing pair outputs | Burst tasks failed transiently | `process.array` retries (`maxRetries = 2`) handle most; if persistent, see slurm_logs |
| Tree inference slow | Many orthogroups | Increase `resources.orthofinder_finalize.cpus` (helps `-t` parallelization in finalize) |

## When To Use This BLOCK

- ≥ 30 species, where standard OrthoFinder would take days.
- HiPerGator (or any SLURM cluster with burst QOS).
- When you want OrthoFinder's full pipeline output (orthogroups + trees +
  reconciliation), not just orthogroups.

For smaller species sets, standard `BLOCK_orthofinder` is simpler and may
complete fast enough.
