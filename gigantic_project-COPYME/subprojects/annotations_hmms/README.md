# annotations_hmms - Proteome Functional Annotation Database

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March 03 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent: [`../../README.md`](../../README.md) — gigantic_project-COPYME overview
- Subproject AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)
- Reads from:
  - `../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/` — proteomes (one FASTA per species)
- Outputs to (`output_to_input/`):
  - `BLOCK_interproscan/` — InterProScan results (symlinks)
  - `BLOCK_deeploc/` — DeepLoc results (symlinks)
  - `BLOCK_signalp/` — SignalP results (symlinks)
  - `BLOCK_metapredict/` — MetaPredict results (symlinks)
  - `BLOCK_tmbed/` — TMBed transmembrane topology results (symlinks)
  - `BLOCK_build_annotation_database/` — integrated 7-column annotation database (symlinks)
- Downstream consumers:
  - `ocl_phylogenetic_structures/BLOCK_annotations_X_ocl/` — annotation × species-tree-structure evolutionary inference
  - `secretome/` — uses SignalP + TMBed evidence
  - `dark_proteomes/` — uses unannotated (no domain) classification
  - `upload_to_server/` (subproject root) — curated subset for the GIGANTIC server

---

## Purpose

Build a comprehensive functional annotation database for all species proteomes
using five independent annotation tools. Each tool predicts different
functional properties (protein domains/families, subcellular localization,
signal peptides, transmembrane topology, intrinsic disorder), and their
results are parsed into a standardized 7-column database format for
downstream analyses.

---

## Architecture

Six BLOCKs — five run a tool, one integrates:

| Project | Tool | What It Predicts |
|---------|------|------------------|
| `BLOCK_interproscan/` | InterProScan 5 | Protein domains, families, GO terms (19 component databases) |
| `BLOCK_deeploc/` | DeepLoc 2.1 | Subcellular localization (GPU) |
| `BLOCK_signalp/` | SignalP 6 | Signal peptides and cleavage sites |
| `BLOCK_metapredict/` | MetaPredict | Intrinsic disorder regions |
| `BLOCK_tmbed/` | TMBed | Transmembrane topology (per-residue inside/membrane/outside) |
| `BLOCK_build_annotation_database/` | Integration | Parses tool outputs into standardized DB, statistics, analyses |

Tool BLOCKs (interproscan, deeploc, signalp, metapredict, tmbed) are
independent — run in any order, any subset. `build_annotation_database`
auto-discovers which tool outputs are available and builds the integrated
database from whatever is present.

---

## Prerequisites

1. **genomesDB complete**: proteomes in `../genomesDB/output_to_input/STEP_4-create_final_species_set/`
2. **Conda envs**: auto-created per-BLOCK on first run from each workflow's `ai/conda_environment.yml` (per §28)
3. **Nextflow**: `module load nextflow` (NF version pin: see workflow `ai/nextflow.config`)
4. **Tool installations** (manual, DTU-licensed binaries):
   - InterProScan standalone — `BLOCK_interproscan/software/`
   - DeepLoc 2.1 — `BLOCK_deeploc/software/`
   - SignalP 6 — `BLOCK_signalp/software/`
   - TMBed — installed via `aiG-annotations_hmms-tmbed` conda env (pip)
   - MetaPredict — installed via `aiG-annotations_hmms-metapredict` conda env (pip)

---

## Per-BLOCK Conda Envs (§28)

| BLOCK | Conda env name | Notes |
|-------|----------------|-------|
| BLOCK_interproscan | `aiG-annotations_hmms-interproscan` | Java + Python |
| BLOCK_deeploc | `aiG-annotations_hmms-deeploc` | GPU; PyTorch |
| BLOCK_signalp | `aiG-annotations_hmms-signalp` | Python |
| BLOCK_metapredict | `aiG-annotations_hmms-metapredict` | Python + pip metapredict |
| BLOCK_tmbed | `aiG-annotations_hmms-tmbed` | Python + pip TMBed; **transformers<5 required** (see project memory `project_tmbed_transformers_pinning_needed`) |
| BLOCK_build_annotation_database | `aiG-annotations_hmms-build_annotation_database` | Python (parsers, integrators) |

---

## Quick Start

```bash
# For each tool BLOCK:
# 1. Copy template
cp -r BLOCK_interproscan/workflow-COPYME-run_interproscan BLOCK_interproscan/workflow-RUN_01-run_interproscan
cd BLOCK_interproscan/workflow-RUN_01-run_interproscan/

# 2. Edit configuration (set execution_mode, proteome paths, SLURM resources)
vi START_HERE-user_config.yaml

# 3. Run (single entry point; self-submits to SLURM per execution_mode)
bash RUN-workflow.sh
```

Same pattern for all 6 BLOCKs. Run tool BLOCKs first, then BLOCK_build_annotation_database.

`RUN-workflow.sh` activates/deactivates its own conda env. `execution_mode`
(local / slurm / slurm_burst) is read from YAML; no `RUN-workflow.sbatch`
needed (deprecated per §29).

---

## Standardized Database Format

All tool outputs are parsed into a common 7-column TSV format:

| Column | Description |
|--------|-------------|
| `Phyloname` | GIGANTIC phylogenetic name |
| `Sequence_Identifier` | Protein sequence identifier |
| `Domain_Start` | Start coordinate (NA for whole-protein predictions) |
| `Domain_Stop` | Stop coordinate (NA for whole-protein predictions) |
| `Database_Name` | Source database (e.g., pfam, deeploc, signalp, tmbed) |
| `Annotation_Identifier` | Annotation ID (e.g., PF00001, SP, TM) |
| `Annotation_Details` | Human-readable description |

24+ database subdirectories produced: pfam, gene3d, superfamily, smart,
panther, cdd, prints, prositepatterns, prositeprofiles, hamap, sfld,
funfam, ncbifam, pirsf, coils, mobidblite, antifam, interproscan, go,
deeploc, signalp, metapredict, tmbed (+ tool-specific subviews).

---

## Directory Structure

```
annotations_hmms/
├── README.md                                  # this file
├── AI_GUIDE.md                                # AI assistant guide (Level 2)
├── HANDOFF-2026may25-tmbed_long_protein_gap.md  # in-flight handoff
├── RUN-update_upload_to_server.sh             # publisher (one per subproject per §38)
├── upload_to_server/
├── output_to_input/                           # consolidated outputs for downstream (per-BLOCK)
│
├── BLOCK_interproscan/                        # InterProScan 5 (6 scripts incl. write_run_log)
│   ├── AI_GUIDE.md
│   └── workflow-COPYME-run_interproscan/
│       ├── ai/ (main.nf, nextflow.config, scripts/, conda_environment.yml)
│       ├── RUN-workflow.sh
│       └── START_HERE-user_config.yaml
│
├── BLOCK_deeploc/                             # DeepLoc 2.1 (3 scripts incl. write_run_log)
│   ├── AI_GUIDE.md
│   └── workflow-COPYME-run_deeploc/
│       └── (same layout)
│
├── BLOCK_signalp/                             # SignalP 6 (5 scripts incl. write_run_log)
│   ├── AI_GUIDE.md
│   └── workflow-COPYME-run_signalp/
│
├── BLOCK_metapredict/                         # MetaPredict (4 scripts incl. write_run_log)
│   ├── AI_GUIDE.md
│   └── workflow-COPYME-run_metapredict/
│
├── BLOCK_tmbed/                               # TMBed (5 scripts incl. write_run_log)
│   ├── AI_GUIDE.md
│   └── workflow-COPYME-run_tmbed/
│
└── BLOCK_build_annotation_database/           # database builder (18 scripts incl. write_run_log)
    ├── AI_GUIDE.md
    └── workflow-COPYME-build_annotation_database/
```

(No per-subproject `research_notebook/` — per §1 consolidation, sandbox
content lives at `../../research_notebook/research_user/subproject-annotations_hmms/`.)

---

## Cluster-Side Failure Pattern: Drain-Node Race (HiPerGator post-upgrade)

Since the HiPerGator OS/SLURM upgrade (~May 2026), a small fraction of
burst-submitted chunk jobs die in 0-1 sec with `ExitCode 0:53`
(SIGRTMIN+19) and `Reason=ReqNodeNotAvail` — the SLURM scheduler
allocates jobs to nodes that have already begun their DRAIN transition
(most commonly observed on `c0706a-s7`, `c0706a-s9`, `c0706a-s10`,
`c0706a-s12`). The chunk has no `.command.log` because bash never started.

This is **not a workflow bug** — it is a cluster-side scheduler bug. The
empirical hit rate on high-volume burst runs is roughly 1-3% of submissions.

**Canonical handling pattern** (implemented in BLOCK_interproscan, reference
for other chunked workflows):

1. `errorStrategy = 'ignore'` on the chunked process — failed chunks are
   silently dropped instead of killing the pipeline. This is an **explicit,
   documented override** of the project CLAUDE.md default ("NEVER use 'ignore'"),
   justified by this known cluster-side failure mode.
2. A gap-detection step (`detect_failed_chunks`, script 006) compares
   expected chunks (publishDir 2-output) against successful chunks
   (publishDir 3-output) and writes `6_ai-failed_chunks.tsv` listing what
   to rerun.
3. User drives a follow-up RUN_N targeting just the failed chunks.

See [BLOCK_interproscan/AI_GUIDE.md](BLOCK_interproscan/AI_GUIDE.md) for full details.

---

## See Also

- [`AI_GUIDE.md`](AI_GUIDE.md) — AI assistant guidance for this subproject
- `BLOCK_<tool>/AI_GUIDE.md` — per-BLOCK AI guides (one per BLOCK)
- [`HANDOFF-2026may25-tmbed_long_protein_gap.md`](HANDOFF-2026may25-tmbed_long_protein_gap.md) — current in-flight HANDOFF about EvidentialGene multi-locus IDs filtering for TMBed (see memory `feedback_evigene_multilocus_id_filename_limit`)

---

## Session hygiene (per §61 in `ai/ai_FYIs/gigantic_conventions.md`)

GIGANTIC's chat-as-research-notebook convention (§9) works best with
disciplined session hygiene. Two recommendations.

### Always root at the named gigantic_project-COPYME

Every chat session for project work should be initiated rooted at the
user's renamed copy of `gigantic_project-COPYME/` — e.g.,
`gigantic_project-cephalopod_evolution/`.

**Not** at:
- `GIGANTIC/` (the framework root, reserved for framework-development
  sessions per §16)
- `subprojects/<X>/` (a subproject directory)
- `subprojects/<X>/<BLOCK_or_STEP>/workflow-COPYME-*/` (a workflow directory)
- Any other directory deeper than the named project root

Why: the renamed project copy is the canonical session root. All
project conventions, INPUT_user paths, research_notebook captures,
and AI guidance are scoped to that directory. Rooting deeper than
that scopes the AI's view too narrowly and loses cross-subproject
context (and the AI guides at lower levels assume the session was
rooted above them). Rooting at `GIGANTIC/` is reserved for
framework-development sessions per §16.

### One chat session per subproject + a side channel for small questions

For productive project work:

- **One session per subproject** you're actively working in. A session
  focused on `phylonames/` is different from one focused on
  `genomesDB/` is different from one focused on `trees_species/` —
  each maintains its own context, convention reminders, and recent
  state.
- **Continue the same session over many compactions** until it
  becomes overly reactive, muddled, or slow. Compactions are
  lossless (per §9 the full transcript is captured), so a long
  session isn't a problem until it starts feeling like one.
- **When a session goes muddled, start a fresh one** at the same
  named `gigantic_project-*/` root, focused on the same subproject,
  and bring it back up to speed (read the relevant AI_GUIDEs, recent
  commits, etc.).
- **Keep a separate "small questions" session** for random or
  cross-cutting questions (e.g., "what does this convention mean?"
  or "is this NCBI accession a GCF or GCA?"). This keeps the
  subproject sessions focused on their actual work and prevents
  context pollution.

### What this prevents

- Sessions that try to hold every subproject's state in context and
  end up confused about which one they're operating on.
- Sessions that get derailed by one-off questions and lose their
  thread on the subproject work.
- Session captures (per §9) that mix multiple unrelated subprojects
  into a single transcript, making the lab-notebook record harder
  to grep later.
