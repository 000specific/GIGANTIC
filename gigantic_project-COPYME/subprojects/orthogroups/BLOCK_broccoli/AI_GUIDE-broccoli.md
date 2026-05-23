# AI_GUIDE-broccoli.md (Level 2: Tool Project Guide)

**For AI Assistants**: Read `../AI_GUIDE-orthogroups.md` first for subproject overview and tool comparison. This guide covers Broccoli-specific concepts and was deep-revised in Apr 2026 after a research pass on Broccoli's actual algorithm and CLI (vs. earlier placeholder scaffolding).

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../AI_GUIDE-project.md` |
| Orthogroups overview, tool comparison | `../AI_GUIDE-orthogroups.md` |
| Broccoli concepts (this file) | This file |
| Running the workflow | `workflow-COPYME-run_broccoli/ai/AI_GUIDE-broccoli_workflow.md` |

## Broccoli Overview

Broccoli (Derelle 2020, MBE) identifies orthogroups by combining phylogenetic and network analyses. Per the paper, Broccoli builds **as many trees as the number of input sequences** — i.e., one phylogeny per protein — then uses a community-detection algorithm on a network derived from those trees to assign orthogroups. The paper claims ~13 % faster than OrthoFinder2 on 8–64 fungal proteomes.

**Distinctive output**: detects **chimeric proteins** (gene fusions) — proteins that appear to be fusions of two or more ancestral genes, identified as bridging edges in the network.

**Header requirement**: Broccoli works with short FASTA headers (similar to OrthoHMM). The pipeline handles header conversion (script 002) and restoration (script 004).

## Broccoli's 4 Internal Steps (canonical)

Broccoli writes per-step output directories `dir_step1/` through `dir_step4/` in the current working directory. The `-steps` CLI flag controls which run (default `1,2,3,4`; must be consecutive integers).

| # | Step | What it does | Heavy? |
|---|---|---|---|
| 1 | **kmer clustering** | Initial fast grouping by k-mer composition | Light |
| 2 | **phylomes** (DIAMOND + per-protein FastTree) | All-vs-all DIAMOND + build one tree per query sequence | **Dominant cost** |
| 3 | **network analysis** | Build orthology network from phylomes; community detection → orthogroups; chimeric detection | Light |
| 4 | **pairwise ortholog extraction** | Pull ortholog pairs from network | Light |

### Step 2 internals (per April 2026 deep-dive of `broccoli_step2.py`)

The "per-protein tree" framing in the paper is misleading at the implementation level. What actually happens:
- **DIAMOND**: subprocess call (`subprocess.check_output`), one species-worker per process running a serial inner loop over all N databases. Output format: `--outfmt 6 qseqid sseqid qstart qend sstart cigar` — note **CIGAR is required** (broccoli reconstructs HSP alignments in-process from CIGAR strings, no MAFFT). Peak parallelism without modification: N (one per species).
- **FastTree**: subprocess call, **one FastTree process per species** in batch mode (`-n nb_alis` against a concatenated PHYLIP file). The per-species `alis_*.phy` is built in memory and deleted immediately after FastTree (lines 423 of step2.py). Per-protein FastTree fan-out is therefore not a config flip — it would require source patches to persist alignments and run separate FastTree calls.
- **In-process work**: `extract_HSP` (CIGAR → alignment) iterates over every hit in pure Python. On 1.4M proteins this is non-trivial wall time too — worth profiling before assuming DIAMOND or FastTree dominates.

## Canonical Broccoli CLI Flags (verified against `broccoli.py` source)

| Flag | Default | Purpose | Notes |
|---|---|---|---|
| `-dir <path>` | required | proteome input directory | |
| `-ext <str>` | `.fasta` | proteome file extension | **GIGANTIC override: `-ext .aa`** to match script 002 output |
| `-threads <N>` | 1 | thread count | Use as many as available — broccoli internally parallelizes step 2 |
| `-phylogenies nj|me|ml` | `nj` | tree-construction method | **NOT `-tree_method`** — earlier placeholder scaffold had wrong flag name |
| `-steps "1,2,3,4"` | all 4 | comma-separated step list | Must be consecutive. `-steps "3,4"` can resume from cached `dir_step1/dir_step2`, but `dir_step2/` must contain not just trees but also the pickles step 3 reads (`dict_output/`, `dict_similarity_ortho/`, `dict_trees/`, `prot_str_2_species.pic`, `prot_int_2_species.pic`) — see step 2 internals below |
| `-e_value <f>` | 0.001 | DIAMOND e-value | |
| `-kmer_size <N>` | 100 | kmer length for step 1 | |
| `-nb_hits <N>` | 6 | max hits per species per query (step 2) | |
| `-max_gap <f>` | 0.7 | max gap fraction in alignment (step 2) | |
| `-sp_overlap <f>` | 0.5 | max ratio of overlapping species (step 3) | |
| `-min_weight <f>` | 0.1 | min orthology network edge weight (step 3) | |
| `-chimeric_shared <f>` | 0.5 | chimeric protein detection threshold | |
| `-chimeric_nb_sp <N>` | 3 | min species count for chimeric call | |

## Output Filenames (verified from broccoli source)

Broccoli's raw outputs in its working directory:

`dir_step3/` (main user-facing outputs):
- `orthologous_groups.txt` — main orthogroup assignments
- `chimeric_proteins.txt` — gene-fusion candidates
- `unclassified_proteins.txt` — unassigned proteins
- `statistics_per_OG.txt` — per-OG metrics
- `table_OGs_protein_counts.txt` — count matrix (OG × species)
- `table_OGs_protein_names.txt` — name matrix
- `statistics_per_species.txt` — per-species summary
- `statistics_nb_OGs_VS_nb_species.txt` — distribution

`dir_step4/`:
- `orthologous_pairs.txt` — pairwise ortholog relationships

**Earlier placeholder scaffold incorrectly assumed step 4 was the main output**; actual main outputs are in step 3. Fixed in the revised script 003.

### GIGANTIC pipeline naming convention

Script 003 copies all 9 files above into `OUTPUT_pipeline/3-output/` with the GIGANTIC `3_ai-` prefix preserving broccoli's stems (e.g., `3_ai-orthologous_groups.txt`, `3_ai-table_OGs_protein_counts.txt`, `3_ai-orthologous_pairs.txt`). This makes pipeline files trace cleanly back to broccoli's documented filenames. Script 004 then translates only `3_ai-orthologous_groups.txt` → `4_ai-orthologous_groups-gigantic_ids.tsv` (full GIGANTIC headers). The count and name matrices need no translation — they reference species names, not protein IDs.

## Architecture Decision: NO `_array` variant (current)

Unlike `BLOCK_orthohmm_GIGANTIC` and `BLOCK_orthofinder_array`, Broccoli does **not** get a SLURM-array fan-out variant in the current monolithic block. Reasoning:

- **Granularity mismatch (originally believed)**: Broccoli's heavy step (Step 2) was thought to build per-protein trees. The April 2026 deep-dive found it actually runs **one FastTree process per species in batch mode** — natural granularity is N (species count), not the protein count. Still, fan-out at that granularity isn't a config flip; it requires source patches to persist alignments.
- **No native escape hatch**: unlike OrthoHMM's `--stop prepare` / OrthoFinder's `-op`, Broccoli has no flag that emits per-DIAMOND-pair commands for external execution. The `-steps` flag splits at step boundaries, not within a step.
- **Internal threading**: Broccoli parallelizes Step 2 via `-threads N`, but the parallelism is capped at N species. With species70, peak useful concurrency is 70 processes — wasting most of HiPerGator's burst pool of ~2,250 cpus.

A future `BLOCK_broccoli_array` could be built using a "DIAMOND shim" approach (intercept broccoli's DIAMOND subprocess calls via `-path_diamond` and serve pre-computed pair results from a SLURM array cache) — see "Parallel architecture analysis" below. The current block intentionally stays monolithic for simplicity and portability (e.g., users without SLURM).

## Parallel architecture analysis (April 2026 deep-dive findings)

We considered several approaches for an `_array` variant. Key findings from reading broccoli's source plus OrthoFinder's:

**Option D — share OrthoFinder's DIAMOND output: NOT FEASIBLE.** Broccoli requires `--outfmt 6 qseqid sseqid qstart qend sstart cigar` (CIGAR-bearing). OrthoFinder uses default `outfmt 6` (12 columns, no CIGAR). Without CIGAR, broccoli can't reconstruct alignments. Even if you're already running orthofinder on the same proteomes, the BLAST tables can't be reused for broccoli.

**Option E — DIAMOND shim (recommended if pursued):** Wrap `diamond` via broccoli's `-path_diamond` flag with a shell shim that returns cached results from a SLURM array cache or runs DIAMOND if missing. Pre-populate the cache with N² (~4,900) pair-DIAMOND tasks on the burst array. Saturates burst trivially; FastTree stays internal at N-wide. Zero patches to broccoli (only a shim + array driver). This is the cleanest non-trivial speedup if broccoli's monolithic runtime becomes infeasible.

**Per-protein FastTree fan-out: not feasible without source patches.** Broccoli's `alis_*.phy` is built in memory and deleted immediately after FastTree (step2.py line 423). Externalization would require persisting alignments and refactoring the inner loop of `process_file` into discrete passes.

These notes are recorded here so a future developer doesn't re-walk the same ground. See `workflow-COPYME-run_broccoli/ai/AI_GUIDE-broccoli_workflow.md` for current execution guidance.

## Pipeline Scripts

| # | Script | Status (April 2026) |
|---|---|---|
| 001 | `001_ai-python-validate_proteomes.py` | audited clean — fail-fast throughout |
| 002 | `002_ai-python-convert_headers_to_short_ids.py` | audited clean — fail-fast throughout |
| 003 | `003_ai-bash-run_broccoli.sh` | **rewritten** — correct CLI flags (`-phylogenies`, `-ext .aa`, `-steps`); copies from `dir_step3/` and `dir_step4/`; **fail-fast** on any required broccoli output missing; copies with `3_ai-` prefix preserving broccoli stems |
| 004 | `004_ai-python-restore_gigantic_identifiers.py` | **rewritten** — single-file input (`--orthogroups-file`), drops gene-count handling (count matrix has no protein IDs and is preserved as-is in 3-output/), **fail-fast** on any unmapped short_id (impossible by construction; if it happens, real bug) |
| 005 | `005_ai-python-generate_summary_statistics.py` | **patched** — removed defensive zero-defaults; fail-fast on empty inputs |
| 006 | `006_ai-python-qc_analysis_per_species.py` | audited clean — already fail-fast (strict `-n_` parser) |
| 007 | `007_ai-python-write_run_log.py` | audited clean — log writer only |

## Configuration (yaml schema)

Edit `workflow-COPYME-run_broccoli/START_HERE-user_config.yaml`:
- `inputs.proteomes_dir` — points at genomesDB STEP_4 output
- `broccoli.tree_method` — `nj | me | ml` (passed to broccoli's `-phylogenies`)
- `resources.run_broccoli.{cpus, memory_gb, time_hours}` — single big SLURM job; **species70 COPYME default: 110 cpu / 700 GB / 504h (3 weeks)**. Memory ceiling per HiPerGator rule is 7.5 × cpus, so 110 × 7.5 = 825 GB max; 700 GB leaves headroom. Driver `slurm_time_hours` is 552 (23 days), must outlast `run_broccoli`. First species70 run should be monitored (MaxRSS + Elapsed) to right-size these for future runs.
- `execution_mode` — `slurm` or `local` (top-level switch threaded through nextflow.config)
- `slurm_account / slurm_qos` — driver job; broccoli runs via this same QOS

## Testing & Open Items

- **Not yet tested end-to-end on real data** (as of April 29, 2026). All scripts have been audited and fail-fast hardened, but no broccoli run has executed against species70 yet.
- **Recommended first test**: 5-species subset, default `-steps 1,2,3,4`, verify output files appear in `OUTPUT_pipeline/3-output/` and `4-output/` and validate `4_ai-orthologous_groups-gigantic_ids.tsv` content has correct GIGANTIC IDs.
- **Profile step 2 wall-time breakdown** on the first real run to know whether DIAMOND, FastTree, or in-process CIGAR/alignment work dominates — informs whether the future Option E (DIAMOND shim) is worth building.
- **Resource defaults are still guesses** (educated, but unverified at 70-species scale). Right-size after first run.

## Sources Used in This Audit

- Derelle 2020, MBE: https://academic.oup.com/mbe/article/37/11/3389/5865275
- Broccoli GitHub source: https://github.com/rderelle/Broccoli — read `broccoli.py` and all four step scripts (`scripts/broccoli_step{1,2,3,4}.py`) for the April 2026 deep-dive
- OrthoFinder source: https://github.com/davidemms/OrthoFinder — read `scripts_of/{__main__.py, files.py, config.json}` to assess whether OrthoFinder's DIAMOND outputs could be reused as broccoli inputs (verdict: not without re-running DIAMOND with a different outfmt, see "Parallel architecture analysis" above)
