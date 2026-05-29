# AI_GUIDE — BLOCK_orthohmm_GIGANTIC (orthogroups; parallel-phmmer variant)

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

**For AI Assistants**: Read `../AI_GUIDE.md` first for subproject overview and tool comparison. This guide covers OrthoHMM-GIGANTIC-specific concepts (parallel-phmmer SLURM array fan-out).

## Where this fits

- Parent subproject: [`../AI_GUIDE.md`](../AI_GUIDE.md) — orthogroups overview + tool comparison
- Parent project: [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- Sibling BLOCK (standard variant): [`../BLOCK_orthohmm/`](../BLOCK_orthohmm/) — simpler, fine for < 20 species
- Workflow to run: [`workflow-COPYME-run_orthohmm_GIGANTIC/README.md`](workflow-COPYME-run_orthohmm_GIGANTIC/README.md)
- Reads from: `../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs to: `../output_to_input/BLOCK_orthohmm_GIGANTIC/` (standardized orthogroups table per §38, §2; bit-identical to BLOCK_orthohmm)

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../AI_GUIDE.md` |
| Orthogroups overview, tool comparison | `../AI_GUIDE.md` |
| Standard (non-arrayed) OrthoHMM | `../BLOCK_orthohmm/AI_GUIDE.md` |
| **Parallel-phmmer (this BLOCK) concepts** | This file |
| Running the parallel workflow | `workflow-COPYME-run_orthohmm_GIGANTIC/ai/AI_GUIDE.md` |

## Why This BLOCK Exists

OrthoHMM's all-vs-all phmmer step is the dominant cost at scale (~95 % of runtime for 70 species). HMMER's own docs note phmmer "scales poorly past tens of processors." A native OrthoHMM run on 70 species at 100 cpus achieved only **5.7 % CPU efficiency** before hitting NextFlow's 48 h per-process timeout in `BLOCK_orthohmm` RUN_4.

**BLOCK_orthohmm_GIGANTIC** sidesteps that bottleneck by parallelizing **across** species pairs rather than within each phmmer call.

## Architecture (Parallel Fan-Out)

```
[001 validate]    [002 short-headers]    [003 extract phmmer cmds via --stop prepare]
                                                           │
                                            (~4,830 (taxa_a, taxa_b) pairs)
                                                           ↓
                            ┌──────────── FAN-OUT (NextFlow SLURM array, burst QOS) ────────────┐
                            │                                                                    │
                            │   [004 run_phmmer_pair × ~4,830 SLURM array tasks, 5 cpu each]   │
                            │                                                                    │
                            └────────────────────────── pool ────────────────────────────────────┘
                                                           ↓
[005 pool & verify phmmer outputs]    [006 OrthoHMM --start search_res (Steps 2-5)]
                                                           ↓
[007 restore IDs]    [008 summary]    [009 QC]    [010 run log]
```

Two new OrthoHMM flags make this clean:

- `orthohmm --stop prepare` → prints all phmmer command lines and exits before running them. **Consistency guarantee:** the parallel tasks invoke phmmer with bit-identical args to what native OrthoHMM would have run.
- `orthohmm --start search_res` → resumes from pre-computed phmmer outputs in `orthohmm_working_res/`, skipping Step 1.

## Key Differences vs `BLOCK_orthohmm`

| | `BLOCK_orthohmm` (standard) | `BLOCK_orthohmm_GIGANTIC` (parallel) |
|---|---|---|
| Phmmer step | One process, monolithic, --cpu N inside one phmmer call | ~4,830 SLURM array tasks via burst QOS |
| `process.array` | n/a | `100` (49 array submissions, scheduler-friendly) |
| Wall time on 70 species | Days, often hits limits | Hours |
| CPU efficiency | ~5 % at high `--cpu` | ~80–100 % per-task (each task is naturally sized for phmmer) |
| Scripts | 7 | 9 (3 new for fan-out architecture) |

## SLURM Resource Profile (defaults in COPYME yaml)

- **Driver job** (orchestrates NextFlow): 4 cpu / 30 GB / 10 d on `moroz` QOS
- **Phmmer pair** (each fan-out task): 5 cpu / 37 GB / 5 h on `moroz-b` (burst)
- **OrthoHMM finalize** (Steps 2-5 inside driver job): 40 cpu / 300 GB / 24 h
- HiPerGator convention: `memory_gb = 7.5 × cpus`. To unlock more memory, increase cpus.

## Etiquette and HiPerGator Policy

- **Total array elements:** ~4,830 pairs. UF policy threshold is 10,000 — under threshold, no prior approval needed.
- `process.array = 100` bundles tasks into ~49 real SLURM job arrays (single `sbatch --array=1-100` per submission). Scheduler-friendly.
- Burst QOS (`moroz-b`): designed for many short jobs; fits this fan-out exactly. 5 h walltime per task is well under the 96 h burst cap.
- Driver QOS (`moroz`): long-running orchestrator (10 d walltime).

## Directory Structure

```
BLOCK_orthohmm_GIGANTIC/
├── AI_GUIDE.md            # THIS FILE
└── workflow-COPYME-run_orthohmm_GIGANTIC/
    ├── README.md                            # User-facing how-to
    ├── START_HERE-user_config.yaml          # User config (resources, paths, mail)
    ├── RUN-workflow.sh                      # Single entry point (self-submits to SLURM)
    └── ai/
        ├── AI_GUIDE.md   # Level 3 workflow guide
        ├── main.nf                          # NextFlow pipeline (10 processes)
        ├── nextflow.config                  # yaml-driven, SLURM executor for fan-out
        └── scripts/
            ├── 001_ai-python-validate_proteomes.py
            ├── 002_ai-python-convert_headers_to_short_ids.py
            ├── 003_ai-python-extract_phmmer_commands.py        ← NEW
            ├── 004_ai-python-pool_and_verify_phmmer_outputs.py ← NEW
            ├── 005_ai-bash-run_orthohmm_from_search_res.sh     ← NEW
            ├── 006_ai-python-restore_gigantic_identifiers.py
            ├── 007_ai-python-generate_summary_statistics.py
            ├── 008_ai-python-qc_analysis_per_species.py
            └── 009_ai-python-write_run_log.py
```

## Outputs (consumed downstream)

`output_to_input/BLOCK_orthohmm_GIGANTIC/`:
- `orthogroups_gigantic_ids.tsv` — orthogroups with GIGANTIC long-form IDs
- `gene_count_gigantic_ids.tsv` — per-species count matrix
- `summary_statistics.tsv`
- `per_species_summary.tsv`

Filenames match `BLOCK_orthohmm` so downstream subprojects (e.g., `ocl_phylogenetic_structures/BLOCK_orthogroups_X_ocl/`, `BLOCK_comparison`) can consume from either.

## Configuration Knobs

Edit `START_HERE-user_config.yaml`:
- `inputs.proteomes_dir` — points at genomesDB STEP_4 output
- `orthohmm.evalue`, `orthohmm.single_copy_threshold`
- `resources.phmmer_pair.{cpus,memory_gb,time_hours}` — per-pair fan-out task
- `resources.orthohmm_finalize.{cpus,memory_gb,time_hours}` — finalize stage
- `slurm_account`, `slurm_qos` (driver) / `slurm_burst_account`, `slurm_burst_qos` (fan-out)
- `slurm_mail_user` — email on END/FAIL

## Troubleshooting

| Error | Cause | Solution |
|---|---|---|
| "input file name collision -- multiple input files for: null" | Manifest TSV header uses GIGANTIC self-documenting style; NextFlow's splitCsv returns null keys | Script 003 manifest must use simple bare headers (`taxa_a\ttaxa_b\toutput_filename`). Already fixed; documented in feedback memory. |
| "Process exceeded running time limit" on phmmer | `time` hardcoded too low in nextflow.config | Confirm `resources.phmmer_pair.time_hours` is wired through; check nextflow.config uses `params.time` not a hardcoded value. |
| Empty / missing pair outputs | A few burst tasks failed transiently | `process.array` retries (`maxRetries = 2`) handle most; if persistent, see slurm_logs and 4_ai-pool_verification_report.tsv |
| 5.7 % CPU efficiency warning | Too many cpus per phmmer call | Per-pair sweet spot is 5–8 cpus; do not exceed |

## When To Use This BLOCK

- ≥ 30 species, where the standard OrthoHMM workflow would take days.
- HiPerGator (or any SLURM cluster with burst QOS).
- When phmmer-based sensitivity for divergent sequences matters and DIAMOND-based methods (OrthoFinder) are insufficient.

For smaller species sets (< 20), standard `BLOCK_orthohmm` is simpler and may complete fast enough.
