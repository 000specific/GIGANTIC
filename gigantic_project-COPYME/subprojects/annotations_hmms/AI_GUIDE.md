# AI_GUIDE-annotations_hmms.md (Level 2: Subproject Guide)

**For AI Assistants**: Read `../../AI_GUIDE-project.md` first for GIGANTIC overview, directory structure, and general patterns. This guide covers annotations_hmms-specific concepts and structure.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../AI_GUIDE-project.md` |
| Annotations subproject concepts | This file |
| InterProScan details | `BLOCK_interproscan/AI_GUIDE-interproscan.md` |
| DeepLoc details | `BLOCK_deeploc/AI_GUIDE-deeploc.md` |
| SignalP details | `BLOCK_signalp/AI_GUIDE-signalp.md` |
| MetaPredict details | `BLOCK_metapredict/AI_GUIDE-metapredict.md` |
| Database builder details | `BLOCK_build_annotation_database/AI_GUIDE-build_annotation_database.md` |
| Running a specific workflow | `BLOCK_{tool}/workflow-COPYME-run_{tool}/ai/AI_GUIDE-{tool}_workflow.md` |

---

## Purpose

The annotations_hmms subproject runs four independent annotation tools on species proteomes and builds a standardized annotation database from their outputs. This database provides functional characterization of every protein across all species, enabling downstream comparative analyses.

> **Note**: DeepLoc 2 also reports transmembrane / lipid-anchor / peripheral / soluble probabilities, so a dedicated TM-topology tool is not separately included.

## Architecture

Five independent, self-contained projects using the flat BLOCK pattern (same as orthogroups):

```
annotations_hmms/
├── BLOCK_interproscan/              # InterProScan 5 (19 component databases + GO)
├── BLOCK_deeploc/                   # DeepLoc 2.1 (subcellular localization + TM/lipid/peripheral/soluble, GPU)
├── BLOCK_signalp/                   # SignalP 6 (signal peptides)
├── BLOCK_metapredict/               # MetaPredict (intrinsic disorder)
└── BLOCK_build_annotation_database/ # Integration: parse, database, statistics, analyses
```

BLOCKs 1-4 are independent (run in any order or subset). BLOCK 5 depends on outputs from BLOCKs 1-4 and auto-discovers which are available.

**Design principle**: Adding a new annotation tool = create a new BLOCK with validate + run scripts. The database builder auto-discovers new tool outputs without modification.

---

## Tool Comparison

| Feature | InterProScan | DeepLoc | SignalP | MetaPredict |
|---------|-------------|---------|---------|-------------|
| **Predicts** | Domains, families, GO | Subcellular location + membrane topology | Signal peptides | Disorder regions |
| **Method** | 19 HMM/pattern databases | Deep learning | Deep learning | Deep learning |
| **Compute** | CPU-heavy | GPU | CPU | CPU-light |
| **Output per protein** | Multiple domains | One location + TM/peripheral/lipid/soluble probs | Signal/No signal | Disorder regions |
| **Coordinates** | Real domain boundaries | NA (whole-protein) | 1 to cleavage site | IDR boundaries |
| **Database count** | 19 + interproscan + GO | 1 | 1 | 1 |
| **Conda env** | ai_gigantic_interproscan | ai_gigantic_deeploc | ai_gigantic_signalp | ai_gigantic_metapredict |

---

## Standardized Database Format

All tool outputs are parsed into a common 7-column TSV:

```
Phyloname	Sequence_Identifier	Domain_Start	Domain_Stop	Database_Name	Annotation_Identifier	Annotation_Details
```

**Coordinate handling per tool**:
- **InterProScan databases**: Real domain start/stop coordinates
- **MetaPredict**: IDR region start/stop boundaries
- **SignalP**: 1 to cleavage_site_position
- **DeepLoc**: Start=NA, Stop=NA (whole-protein prediction)

**23 database subdirectories**: pfam, gene3d, superfamily, smart, panther, cdd, prints, prositepatterns, prositeprofiles, hamap, sfld, funfam, ncbifam, pirsf, coils, mobidblite, antifam, interproscan, go, deeploc, signalp, metapredict

**File naming**: `gigantic_annotations-database_{database_name}-{phyloname}.tsv`

---

## Data Flow

```
genomesDB/output_to_input/gigantic_proteomes/
              │
    ┌─────────┼───────────┬──────────┐
    ▼         ▼           ▼          ▼
BLOCK_       BLOCK_      BLOCK_     BLOCK_
interpro-    deeploc/    signalp/   meta-
scan/                               predict/
(4 scripts)  (2 scripts) (2 scripts) (2 scripts)
    │            │           │          │
    ▼            ▼           ▼          ▼
output_to_input/  (consolidated at subproject root)
  BLOCK_interproscan/
  BLOCK_deeploc/
  BLOCK_signalp/
  BLOCK_metapredict/
                             │
                             ▼
              BLOCK_build_annotation_database/
              (15 scripts: discover, download GO,
               parse x4, statistics, analyses x8)
                             │
                             ▼
              output_to_input/BLOCK_build_annotation_database/
              → downstream subprojects
```

---

## Prerequisites

1. **genomesDB complete**: `genomesDB/output_to_input/gigantic_proteomes/` populated
2. **Conda environments**: One per tool (created by `RUN-setup_environments.sh`)
3. **Nextflow**: `module load nextflow`
4. **Tool installations**: InterProScan (standalone Java), DeepLoc (DTU license), SignalP (DTU license)

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| No proteome files found | Proteomes directory empty or wrong path | Check genomesDB output_to_input is populated |
| InterProScan out of memory | Proteome too large for single run | Reduce chunk_size in config |
| GPU not available | SLURM partition wrong | Use hpg-turin (L4) or hpg-b200 (B200) partition with --gres=gpu for DeepLoc |
| DeepLoc model not found | Manual installation required | Download from DTU website |
| SignalP license error | Requires academic license | Register at DTU website |
| No tool outputs found | Database builder cannot find sibling BLOCKs | Run at least one tool BLOCK first |
| GO ontology download failed | Network issue or URL changed | Check go_ontology_url in config |
| Nextflow cache stale | Updated scripts not taking effect | Delete `work/` and `.nextflow*`, rerun without `-resume` |
| Burst chunks die in 0-1 sec, ExitCode 0:53, no `.command.log` written | **HiPerGator post-upgrade drain-node race** — SLURM allocates jobs to nodes already entering DRAIN (most often `c0706a-s7,9,10,12`). Not a workflow bug. | Use `errorStrategy = 'ignore'` + gap-detection on chunked processes. See "HiPerGator drain-node race" section below for canonical pattern. |

---

## HiPerGator Drain-Node Race (Post-Upgrade Scheduler Bug)

**Symptom:** Burst-mode chunk jobs die in 0-1 sec with `ExitCode 0:53` (SIGRTMIN+19) and `sacct Reason=ReqNodeNotAvail`. No `.command.log`, no `.command.err`, no stderr — the process is killed before bash sources `.bashrc`.

**Root cause (diagnosed 2026-05-25):** Since the HiPerGator OS/SLURM upgrade in early-to-mid May 2026, the scheduler in SLURM 25.11.5 has a race where it still allocates jobs to nodes that have begun their DRAIN transition. The node then rejects the incoming job. Reproducible: `sbatch -w c0706a-s9 …` while s9 is in state `mixed-` (the trailing dash = draining) → exit 0:53 in ~1 sec. Affects all moroz QOSes (moroz, moroz-b). Observed empirical hit rate: **~1-3% of burst submissions** in the c0706a rack.

**Evidence trail:** sacct shows `c0706a-s{7,9,10,12}` as the recurring nodes; `scontrol show node` confirms `State=MIXED` with the draining indicator at the moment of failure; `sinfo` reports no maintenance reservation covering these nodes. The post-upgrade timing (failures start ~2026-05-22, slurmd restart on these nodes ~2026-05-20) is the smoking gun.

**Canonical handling pattern (reference: BLOCK_interproscan):**

The cluster-side bug is not ours to fix. For chunked workflows that submit hundreds-to-thousands of burst jobs, the pattern is:

1. **In `ai/nextflow.config`**, set `errorStrategy = 'ignore'` for the chunked process. This is an **explicit, documented override of the CLAUDE.md "NEVER use 'ignore'" rule** — justified by the documented external scheduler bug and the practical reality that fail-fast loses 100% of a multi-day run because of a 1-3% transient cluster issue.
2. **Add a `detect_failed_chunks` process (script 006)** that runs after `combine_*` and compares expected chunks (publishDir 2-output) vs successful chunks (publishDir 3-output). Writes a `6_ai-failed_chunks.tsv` manifest listing what to rerun.
3. **User drives a follow-up RUN_N** from that manifest if they want full coverage.

**Also fixed in BLOCK_interproscan** during the same diagnosis (worth porting if you adopt slurm mode in other BLOCKs): the previous `withName: 'run_interproscan'` in slurm (non-burst) mode used `cpus = params.cpus` per chunk, forcing 1 chunk at a time inside a single allocation (defeating the purpose of slurm mode for parallel work). The fix is to use `burst_cpus_per_chunk` for per-chunk sizing in BOTH burst and slurm modes, so multiple chunks run in parallel within a slurm allocation.

**Empirical baseline from interproscan RUN_3 (2026-05-25):**
- 1413 chunks × 5 tools combined × 10 CPU × 75 GB on moroz-b
- ~2.3% chunks died from the drain-node race (~28-32 chunks); pipeline survived via `errorStrategy='ignore'`
- Wall time ~12-15 hours total
- moroz-b utilization: ~410/450 CPU sustained throughout

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `START_HERE-user_config.yaml` | Workflow configuration (includes `execution_mode`, slurm account/qos, resources) | **Yes** - edit before running |
| `RUN-workflow.sh` | Unified entry point — self-submits to SLURM if `execution_mode` is `slurm` or `slurm_burst` | No |
| `RUN-workflow.sbatch` | **Deprecated** — kept for back-compat only. Use `RUN-workflow.sh` with `execution_mode` in YAML. | No |
| `ai/main.nf` | Nextflow pipeline | No |
| `ai/nextflow.config` | Nextflow settings (incl. `errorStrategy` per process) | Rarely - resource adjustments, error semantics |
| `ai/scripts/*.py` | Pipeline scripts | No |

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
