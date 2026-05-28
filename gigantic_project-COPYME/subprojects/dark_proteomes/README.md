# dark_proteomes — Three-Axis Dark Matter Classification

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 04 (workflow scripts)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (initial docs)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent: [`../../README.md`](../../README.md) — gigantic_project-COPYME overview
- Subproject AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)
- Reads from (per-species inputs combined for the 3-axis classification):
  - `../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/` — proteomes
  - `../one_direction_homologs/output_to_input/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits/` — axis_a (reference BLAST hits)
  - `../orthogroups/output_to_input/BLOCK_orthohmm_GIGANTIC/orthogroups_gigantic_ids.tsv` — axis_b (orthogroup memberships)
  - `../annotations_hmms/output_to_input/BLOCK_interproscan_parsed/` — axis_c (Pfam/PANTHER domain annotations)
- Outputs to (`output_to_input/BLOCK_classify_dark_proteome/`):
  - Per-species dark-gene lists
  - Cross-species dark-proteome summary table
- Downstream consumers:
  - `upload_to_server/` (subproject root) — curated subset for the GIGANTIC server
  - Publication-ready dark-proteome statistics

---

## Purpose

Classify every gene in every project species as **DARK** (genomic dark
matter) or **ANNOTATED**, using the three-axis test from
Edsinger 2024 (*Frontiers in Marine Science*).

A gene is DARK if and only if **all three** independent axes fail:

| Axis | Test | Data source |
|------|------|-------------|
| **a** | No BLAST hit to a reference species | `one_direction_homologs` (diamond vs NCBI nr top hits for reference set) |
| **b** | Not in any orthogroup that contains a reference species gene | `orthogroups` (e.g., orthoHMM GIGANTIC OG table) |
| **c** | No Pfam or PANTHER domain annotation | `annotations_hmms/BLOCK_interproscan_parsed` |

Default reference species: human, *Drosophila*, *C. elegans* (the paper's
three; configurable in `START_HERE-user_config.yaml`).

The intersection ("dark only when all three fail") is the strict definition
— genes too divergent from model organisms to be detected by any standard
annotation method, while still being valid gene predictions in the species's
proteome.

---

## Prerequisites

Upstream subprojects must be complete (any subset of axes can be skipped
by leaving its input dir empty, but a meaningful classification requires
at least one signal — typically all three):

- **genomesDB** — provides proteomes (species set definition)
- **one_direction_homologs** — provides axis_a (reference BLAST hits)
- **orthogroups** — provides axis_b (orthogroup membership; orthoHMM_GIGANTIC or any standardized OG table)
- **annotations_hmms** (BLOCK_interproscan) — provides axis_c (Pfam/PANTHER domain hits)

Plus:
- Conda env auto-created on first run from `BLOCK_classify_dark_proteome/workflow-COPYME-classify_dark_proteome/ai/conda_environment.yml`
- NextFlow

---

## Architecture

Single BLOCK (independent — flat BLOCK pattern, no internal sequencing):

```
dark_proteomes/
├── README.md                                    # this file
├── AI_GUIDE.md                                  # AI assistant guide
├── RUN-update_upload_to_server.sh               # publisher (one per subproject per §38)
├── upload_to_server/                            # curated subset for the GIGANTIC server
├── output_to_input/
│   └── BLOCK_classify_dark_proteome/            # symlinked workflow results
│
└── BLOCK_classify_dark_proteome/                # 5 scripts incl. write_run_log
    └── workflow-COPYME-classify_dark_proteome/
        ├── INPUT_user/
        │   └── gigantic_species_list.txt        # species to process
        ├── START_HERE-user_config.yaml          # reference species + paths to upstream subprojects
        ├── RUN-workflow.sh                      # single entry point (execution_mode YAML)
        └── ai/
            ├── main.nf                          # NextFlow pipeline (5 processes)
            ├── nextflow.config
            ├── conda_environment.yml            # aiG-dark_proteomes
            └── scripts/
                ├── 001_ai-python-validate_inputs.py
                ├── 002_ai-python-build_reference_orthogroup_set.py
                ├── 003_ai-python-classify_per_species.py
                ├── 004_ai-python-summarize_dark_proteome.py
                └── 005_ai-python-write_run_log.py
```

Conda env name on disk: `aiG-dark_proteomes` (single-BLOCK subproject;
not the strict §28 form `aiG-<subproject>-<block>` — a minor deviation
flagged for future consideration but functionally fine since there's only
one BLOCK).

---

## Quick Start

```bash
cd BLOCK_classify_dark_proteome
cp -r workflow-COPYME-classify_dark_proteome workflow-RUN_1-classify_dark_proteome
cd workflow-RUN_1-classify_dark_proteome

# Edit config: reference species, upstream subproject paths, execution_mode
vi START_HERE-user_config.yaml

# Place species list in INPUT_user/
vi INPUT_user/gigantic_species_list.txt

# Run (auto-creates conda env on first run; self-submits to SLURM per execution_mode)
bash RUN-workflow.sh
```

---

## Pipeline (5 processes)

1. **validate_inputs** — pair every species with its 4 inputs (proteome, BLAST hits, OG table, HMM hits); fail-fast if any missing
2. **build_reference_orthogroup_set** — one-time pre-process; the set of OGs that contain at least one reference-species gene (axis_b reference)
3. **classify_per_species** — per-species fan-out; the 3-axis check per gene
4. **summarize_dark_proteome** — cross-species aggregate table (dark counts, percentages, by species/clade)
5. **write_run_log** — timestamped run log per §45

---

## Reference

Edsinger E (2024). *Front. Mar. Sci.* — three-axis dark-proteome
classification methodology.

## See Also

- [`AI_GUIDE.md`](AI_GUIDE.md) — AI assistant guidance
- `BLOCK_classify_dark_proteome/AI_GUIDE.md` — BLOCK-level guide
- `BLOCK_classify_dark_proteome/workflow-COPYME-classify_dark_proteome/ai/AI_GUIDE.md` — workflow execution guide

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
