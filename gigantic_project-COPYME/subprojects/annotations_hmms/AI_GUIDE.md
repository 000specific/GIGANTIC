# AI_GUIDE.md (Level 2: Subproject Guide) — annotations_hmms

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (project): [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — GIGANTIC overview + general patterns
- Subproject README: [`README.md`](README.md)
- Reads FROM:
  - `../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/` — proteomes
- Outputs TO (`output_to_input/`):
  - `BLOCK_interproscan/` — InterProScan
  - `BLOCK_deeploc/` — DeepLoc
  - `BLOCK_signalp/` — SignalP
  - `BLOCK_metapredict/` — MetaPredict
  - `BLOCK_tmbed/` — TMBed
  - `BLOCK_build_annotation_database/` — integrated 7-column DB
- Downstream consumers:
  - `ocl_phylogenetic_structures/BLOCK_annotations_X_ocl/` — annotation × species-tree-structure evolutionary inference
  - `secretome/` — SignalP + TMBed evidence
  - `dark_proteomes/` — no-annotation classification
  - `upload_to_server/` — curated subset
- In-flight context: [`HANDOFF-2026may25-tmbed_long_protein_gap.md`](HANDOFF-2026may25-tmbed_long_protein_gap.md) — EvidentialGene long-header filtering work-in-progress (see memory `feedback_evigene_multilocus_id_filename_limit`)

---

**For AI Assistants**: Read `../../AI_GUIDE.md` first for GIGANTIC overview, directory structure, and general patterns. This guide covers annotations_hmms-specific concepts and structure.

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../AI_GUIDE.md` |
| Annotations subproject concepts | this file |
| Subproject README | `README.md` |
| InterProScan details | `BLOCK_interproscan/AI_GUIDE.md` |
| DeepLoc details | `BLOCK_deeploc/AI_GUIDE.md` |
| SignalP details | `BLOCK_signalp/AI_GUIDE.md` |
| MetaPredict details | `BLOCK_metapredict/AI_GUIDE.md` |
| TMBed details | `BLOCK_tmbed/AI_GUIDE.md` |
| Database builder details | `BLOCK_build_annotation_database/AI_GUIDE.md` |
| Running a specific workflow | `BLOCK_<tool>/workflow-COPYME-run_<tool>/ai/AI_GUIDE.md` |

---

## Purpose

The annotations_hmms subproject runs five independent annotation tools on
species proteomes and builds a standardized 7-column annotation database
from their outputs. This database provides functional characterization of
every protein across all species, enabling downstream comparative analyses.

## Architecture

Six BLOCKs — five tool BLOCKs + one integrator — using the flat BLOCK
pattern (same as orthogroups):

```
annotations_hmms/
├── BLOCK_interproscan/              # InterProScan 5 (19 component databases + GO)
├── BLOCK_deeploc/                   # DeepLoc 2.1 (subcellular localization, GPU)
├── BLOCK_signalp/                   # SignalP 6 (signal peptides)
├── BLOCK_metapredict/               # MetaPredict (intrinsic disorder)
├── BLOCK_tmbed/                     # TMBed (transmembrane topology, per-residue)
└── BLOCK_build_annotation_database/ # Integration: parse, database, statistics
```

Tool BLOCKs (interproscan / deeploc / signalp / metapredict / tmbed) are
independent — run in any order, any subset. `build_annotation_database`
depends on outputs from the tool BLOCKs and auto-discovers which are
available.

**Design principle**: adding a new annotation tool = create a new BLOCK
with validate + run + write_run_log scripts. The database builder
auto-discovers new tool outputs without modification.

---

## Tool Comparison

| Feature | InterProScan | DeepLoc | SignalP | MetaPredict | TMBed |
|---------|--------------|---------|---------|-------------|-------|
| **Predicts** | Domains, families, GO | Subcellular location | Signal peptides | Disorder regions | Transmembrane topology |
| **Method** | 19 HMM/pattern databases | Deep learning | Deep learning | Deep learning | Deep learning (T5-based) |
| **Compute** | CPU-heavy | GPU | CPU | CPU-light | CPU |
| **Output per protein** | Multiple domains | One location | Signal/No signal | Disorder regions | Per-residue I/M/O classification |
| **Coordinates** | Real domain boundaries | NA (whole-protein) | 1 to cleavage site | IDR boundaries | TM segment start/stop |
| **Database count** | 19 + interproscan + GO | 1 | 1 | 1 | 1 |
| **Conda env (§28)** | `aiG-annotations_hmms-interproscan` | `aiG-annotations_hmms-deeploc` | `aiG-annotations_hmms-signalp` | `aiG-annotations_hmms-metapredict` | `aiG-annotations_hmms-tmbed` |

---

## Standardized Database Format

All tool outputs are parsed into a common 7-column TSV:

```
Phyloname	Sequence_Identifier	Domain_Start	Domain_Stop	Database_Name	Annotation_Identifier	Annotation_Details
```

**Coordinate handling per tool**:
- **InterProScan databases**: real domain start/stop coordinates
- **MetaPredict**: IDR region start/stop boundaries
- **SignalP**: 1 to cleavage_site_position
- **DeepLoc**: Start=NA, Stop=NA (whole-protein prediction)
- **TMBed**: TM segment start/stop coordinates

**Database subdirectories** (24+ at last count): pfam, gene3d, superfamily,
smart, panther, cdd, prints, prositepatterns, prositeprofiles, hamap, sfld,
funfam, ncbifam, pirsf, coils, mobidblite, antifam, interproscan, go,
deeploc, signalp, metapredict, tmbed (+ tool-specific subviews).

**File naming**: `gigantic_annotations-database_{database_name}-{phyloname}.tsv`

---

## Data Flow

```
../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/
                            │
        ┌──────────┬─────────┼──────────┬──────────┐
        ▼          ▼         ▼          ▼          ▼
   BLOCK_      BLOCK_     BLOCK_     BLOCK_     BLOCK_
   interpro    deeploc/   signalp/   meta-      tmbed/
   scan/       (3 scripts)(5 scripts)predict/   (5 scripts)
   (6 scripts)                       (4 scripts)
        │          │         │          │          │
        ▼          ▼         ▼          ▼          ▼
            output_to_input/  (consolidated, one subdir per tool BLOCK)
                            │
                            ▼
              BLOCK_build_annotation_database/
              (18 scripts: discover, download GO, parse x5,
               statistics, analyses)
                            │
                            ▼
              output_to_input/BLOCK_build_annotation_database/
                            │
                            ▼
              → downstream subprojects (ocl_phylogenetic_structures/BLOCK_annotations_X_ocl,
                secretome, dark_proteomes, server)
```

Each tool BLOCK's pipeline ends with `*_ai-python-write_run_log.py` per §45.

---

## Prerequisites

1. **genomesDB complete**: `../genomesDB/output_to_input/STEP_4-create_final_species_set/` populated
2. **Conda envs**: auto-created per-BLOCK on first run from each workflow's `ai/conda_environment.yml` (per §28)
3. **Nextflow**: `module load nextflow` (NF version pin: see workflow `ai/nextflow.config`)
4. **Tool installations**:
   - InterProScan — standalone Java, manual install in `BLOCK_interproscan/software/`
   - DeepLoc — DTU license, manual install in `BLOCK_deeploc/software/`
   - SignalP — DTU license, manual install in `BLOCK_signalp/software/`
   - MetaPredict + TMBed — pip-installed via their conda envs (auto)

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| No proteome files found | Proteomes directory empty or wrong path | Check genomesDB output_to_input is populated |
| InterProScan out of memory | Proteome too large for single run | Reduce chunk_size in config |
| GPU not available | SLURM partition wrong | Use hpg-turin (L4) or hpg-b200 (B200) with `--gres=gpu` for DeepLoc |
| DeepLoc model not found | Manual installation required | Download from DTU website |
| SignalP license error | Requires academic license | Register at DTU website |
| No tool outputs found | Database builder cannot find sibling BLOCKs | Run at least one tool BLOCK first |
| GO ontology download failed | Network issue or URL changed | Check go_ontology_url in config |
| Nextflow cache stale | Updated scripts not taking effect | Delete `work/` and `.nextflow*`, rerun without `-resume` |
| TMBed fails on long protein IDs | EvidentialGene multi-locus IDs exceed 253-char filename limit | Per-BLOCK filter; see BLOCK_signalp/scripts/000_ai-python-filter_proteome_long_headers.py + memory `feedback_evigene_multilocus_id_filename_limit` |
| TMBed `T5Tokenizer.batch_encode_plus` missing | transformers v5+ in conda env | Pin `transformers<5` per memory `project_tmbed_transformers_pinning_needed` |
| Burst chunks die in 0-1 sec, ExitCode 0:53, no `.command.log` | **HiPerGator post-upgrade drain-node race** — see section below | Use `errorStrategy = 'ignore'` + gap-detection on chunked processes |

---

## HiPerGator Drain-Node Race (Post-Upgrade Scheduler Bug)

**Symptom:** Burst-mode chunk jobs die in 0-1 sec with `ExitCode 0:53`
(SIGRTMIN+19) and `sacct Reason=ReqNodeNotAvail`. No `.command.log`, no
`.command.err`, no stderr — the process is killed before bash sources
`.bashrc`.

**Root cause (diagnosed 2026-05-25):** Since the HiPerGator OS/SLURM
upgrade in early-to-mid May 2026, the scheduler in SLURM 25.11.5 has a
race where it still allocates jobs to nodes that have begun their DRAIN
transition. The node then rejects the incoming job. Reproducible:
`sbatch -w c0706a-s9 …` while s9 is in state `mixed-` (the trailing dash
= draining) → exit 0:53 in ~1 sec. Affects all moroz QOSes (moroz,
moroz-b). Observed empirical hit rate: **~1-3% of burst submissions** in
the c0706a rack.

**Evidence trail:** sacct shows `c0706a-s{7,9,10,12}` as the recurring
nodes; `scontrol show node` confirms `State=MIXED` with the draining
indicator at the moment of failure; `sinfo` reports no maintenance
reservation covering these nodes. The post-upgrade timing (failures start
~2026-05-22, slurmd restart on these nodes ~2026-05-20) is the smoking gun.

**Canonical handling pattern (reference: BLOCK_interproscan):**

The cluster-side bug is not ours to fix. For chunked workflows that submit
hundreds-to-thousands of burst jobs, the pattern is:

1. **In `ai/nextflow.config`**, set `errorStrategy = 'ignore'` for the
   chunked process. This is an **explicit, documented override of the
   CLAUDE.md "NEVER use 'ignore'" rule** — justified by the documented
   external scheduler bug and the practical reality that fail-fast loses
   100% of a multi-day run because of a 1-3% transient cluster issue.
2. **Add a `detect_failed_chunks` process (script 006)** that runs after
   `combine_*` and compares expected chunks (publishDir 2-output) vs
   successful chunks (publishDir 3-output). Writes a
   `6_ai-failed_chunks.tsv` manifest listing what to rerun.
3. **User drives a follow-up RUN_N** from that manifest if they want full
   coverage.

**Also fixed in BLOCK_interproscan** during the same diagnosis (worth
porting if you adopt slurm mode in other BLOCKs): the previous
`withName: 'run_interproscan'` in slurm (non-burst) mode used
`cpus = params.cpus` per chunk, forcing 1 chunk at a time inside a single
allocation (defeating the purpose of slurm mode for parallel work). The
fix is to use `burst_cpus_per_chunk` for per-chunk sizing in BOTH burst
and slurm modes, so multiple chunks run in parallel within a slurm
allocation.

**Empirical baseline from interproscan RUN_3 (2026-05-25):**
- 1413 chunks × 5 tools combined × 10 CPU × 75 GB on moroz-b
- ~2.3% chunks died from the drain-node race (~28-32 chunks); pipeline survived via `errorStrategy='ignore'`
- Wall time ~12-15 hours total
- moroz-b utilization: ~410/450 CPU sustained throughout

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `BLOCK_<tool>/workflow-COPYME-*/START_HERE-user_config.yaml` | Workflow config (execution_mode, slurm account/qos, resources) | **Yes** |
| `BLOCK_<tool>/workflow-COPYME-*/RUN-workflow.sh` | Single entry point; self-submits to SLURM per `execution_mode` YAML | No |
| `BLOCK_<tool>/workflow-COPYME-*/ai/main.nf` | NextFlow pipeline | No |
| `BLOCK_<tool>/workflow-COPYME-*/ai/nextflow.config` | NextFlow settings, errorStrategy per process | Rarely |
| `BLOCK_<tool>/workflow-COPYME-*/ai/conda_environment.yml` | Per-BLOCK conda env spec | No |
| `BLOCK_<tool>/workflow-COPYME-*/ai/scripts/*` | Pipeline scripts (final per §45 is always write_run_log) | No |
| `RUN-update_upload_to_server.sh` (subproject root) | Publisher (one per subproject per §38) | Rarely |

---

## Questions to Ask User

| Situation | Ask |
|-----------|-----|
| First run | "Which proteomes directory should I use?" |
| Resource errors | "What SLURM account and QOS should I use?" |
| Tool selection | "Which annotation tools should we run?" |
| Database build timing | "Have all desired tool BLOCKs completed?" |
| Species set | "Which species set are you analyzing?" |
| InterProScan install | "Where is InterProScan installed on your system?" |
| GPU availability | "Does your cluster have GPU nodes for DeepLoc?" |
| TMBed env issues | "Has the `transformers<5` pin been applied to `aiG-annotations_hmms-tmbed`?" |

---

## Session hygiene (per §61)

For productive project work:
- **Root every chat session at this named `gigantic_project-*/` directory**.
  Not at `GIGANTIC/` (framework root, reserved for framework dev per §16),
  not at `subprojects/<X>/`, not at a `workflow-COPYME-*/` dir, not at
  any directory deeper than the named project root.
- **One chat session per subproject** you're actively working in — keeps
  context focused and prevents cross-subproject confusion.
- **Continue the same session over many compactions** (lossless per §9)
  until it becomes muddled or slow; then start fresh in a new session,
  same root, same subproject focus.
- **Keep a separate "small questions" session** for one-off questions
  so subproject sessions stay focused.

See `ai/ai_FYIs/gigantic_conventions.md` §61 for the full rationale.
