# one_direction_homologs - One-Way DIAMOND Homolog Search Against NCBI nr

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March 01 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent: [`../../README.md`](../../README.md) — gigantic_project-COPYME overview
- Subproject AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)
- Reads from:
-   - `../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
-   - User-provided NCBI nr DIAMOND database (path set in `START_HERE-user_config.yaml`)
- Outputs to: `output_to_input/BLOCK_diamond_ncbi_nr/` — top NCBI nr hits per protein per species
- Downstream consumers:
-   - `dark_proteomes` (axis_a — reference BLAST hit signal)
-   - `upload_to_server/` — curated subset
- Single BLOCK; 7-script pipeline ending in `write_run_log` per §45

---

## Purpose

The one_direction_homologs subproject searches each species proteome against the NCBI non-redundant (nr) protein database using DIAMOND to identify one-directional (non-reciprocal) homologs. For each protein in each species, it identifies the top NCBI hits and distinguishes "self-hits" (identical sequences in nr) from "non-self-hits" (true homologs with different sequences).

**Key outputs**:
- Top 10 NCBI nr hits per protein (with full NCBI headers and sequences)
- Top non-self hit and top self-hit identification
- Per-species and cross-species summary statistics

**Use cases**:
- Proteome quality assessment (self-hit rates indicate nr representation)
- Annotation quality metrics
- Species representation in NCBI databases
- Input for downstream analyses (annotations, orthogroup validation)

---

## Prerequisites

- **genomesDB** completed and `output_to_input/` populated with species proteomes
- **NCBI nr DIAMOND database** created (see Configuration below)
- **phylonames** completed (for species identification)

---

## Quick Start

### Step 0: Set Up Environment (One-Time)

```bash
cd ../../  # Go to gigantic_project-[name] root
bash RUN-setup_environments.sh
```

This creates the `ai_gigantic_one_direction_homologs` conda environment.

### Step 1: Create DIAMOND Database (One-Time)

Download the NCBI nr FASTA and create a DIAMOND database:

```bash
# Download nr FASTA from NCBI (large file, ~100GB compressed)
wget https://ftp.ncbi.nlm.nih.gov/blast/db/FASTA/nr.gz

# Create DIAMOND database
diamond makedb --in nr.gz --db nr.dmnd
```

Update the database path in `START_HERE-user_config.yaml`.

### Step 2: Edit Configuration

Edit `BLOCK_diamond_ncbi_nr/workflow-COPYME-diamond_ncbi_nr/START_HERE-user_config.yaml`:

```yaml
project:
  name: "my_project"

diamond:
  database: "/path/to/nr.dmnd"    # <-- Set this
```

### Step 3: Run the Pipeline

```bash
cd BLOCK_diamond_ncbi_nr/workflow-COPYME-diamond_ncbi_nr

# Local machine:
bash RUN-workflow.sh

# SLURM cluster (edit account/qos first):
sbatch RUN-workflow.sh
```

---

## Pipeline Overview

| Step | Script | Purpose | Output |
|------|--------|---------|--------|
| 1 | `001_ai-python-validate_proteomes.py` | Validate input proteomes and manifest | `OUTPUT_pipeline/1-output/` |
| 2 | `002_ai-python-split_proteomes_for_diamond.py` | Split proteomes into N parts for parallelization | `OUTPUT_pipeline/2-output/` |
| 3 | `003_ai-bash-run_diamond_search.sh` | Run DIAMOND blastp per split (parallel) | `OUTPUT_pipeline/3-output/` |
| 4 | `004_ai-python-combine_diamond_results.py` | Combine split results per species | `OUTPUT_pipeline/4-output/` |
| 5 | `005_ai-python-identify_top_hits.py` | Identify top self/non-self hits per protein | `OUTPUT_pipeline/5-output/` |
| 6 | `006_ai-python-compile_statistics.py` | Compile all species into master summary | `OUTPUT_pipeline/6-output/` |

---

## Directory Structure

```
one_direction_homologs/
├── README.md                                   # This file
├── AI_GUIDE.md          # AI assistant guidance
├── TODO.md                                     # Project tracking
├── user_research/                              # Personal workspace
├── upload_to_server/                           # Files for GIGANTIC server
│   └── upload_manifest.tsv
│
├── output_to_input/                            # Outputs for downstream subprojects
│   └── BLOCK_diamond_ncbi_nr/
│       └── ncbi_nr_top_hits/                   # Per-species top hits + statistics
│
└── BLOCK_diamond_ncbi_nr/
    ├── AI_GUIDE.md             # BLOCK-level AI guidance
    ├── RUN-update_upload_to_server.sh          # Update server sharing symlinks
    │
    └── workflow-COPYME-diamond_ncbi_nr/
        ├── README.md                           # Quick start guide
        ├── RUN-workflow.sh                     # bash RUN-workflow.sh (local)
        ├── RUN-workflow.sh                 # sbatch RUN-workflow.sh (SLURM)
        ├── START_HERE-user_config.yaml         # Edit this for your project
        ├── INPUT_user/                         # Workflow inputs
        │   └── proteome_manifest_example.tsv   # Example manifest
        ├── OUTPUT_pipeline/                    # Generated results
        └── ai/                                 # Internal (don't touch)
            ├── AI_GUIDE.md
            ├── main.nf
            ├── nextflow.config
            └── scripts/                        # Pipeline scripts
```

---

## Output Files

### Per-Species Top Hits

**Location**: `OUTPUT_pipeline/5-output/`

| File | Description |
|------|-------------|
| `{species}_top_hits.tsv` | Top hits per protein with NCBI headers and sequences |
| `{species}_statistics.tsv` | Per-species hit statistics |

### Master Summary

**Location**: `OUTPUT_pipeline/6-output/`

| File | Description |
|------|-------------|
| `6_ai-all_species_statistics.tsv` | Combined statistics for all species |

### Shared Downstream

**Location**: `output_to_input/BLOCK_diamond_ncbi_nr/ncbi_nr_top_hits/`

| File | Description |
|------|-------------|
| `{species}_top_hits.tsv` | Per-protein top hit analysis for each species |
| `{species}_statistics.tsv` | Per-species hit statistics |
| `all_species_statistics.tsv` | Master summary across all species |

---

## DIAMOND Search Details

- **Tool**: DIAMOND blastp (fast alternative to BLASTP, ~1000x faster)
- **Database**: NCBI nr (non-redundant protein sequences)
- **E-value**: 1e-5 (configurable)
- **Max targets**: 10 per query (configurable)
- **Output format**: 15-column tabular (includes stitle for full NCBI headers, full_qseq/full_sseq for sequences)
- **Parallelization**: Each proteome split into N parts (default: 40), enabling thousands of concurrent SLURM jobs

---

## Self-Hit vs. Non-Self-Hit

**Self-hit**: A DIAMOND hit where the query sequence and subject sequence are identical. This indicates the query protein exists in NCBI nr (directly or as an identical copy).

**Non-self-hit**: A DIAMOND hit where the query and subject sequences differ. This is a true homolog from another organism or a paralog.

**Why it matters**:
- High self-hit rates indicate the species is well-represented in NCBI databases
- Non-self hits provide the closest evolutionary relatives for each protein
- Proteins with no non-self hits may be taxonomically restricted or novel

---

## Dependencies

All dependencies are provided by the `ai_gigantic_one_direction_homologs` conda environment:

```bash
# Set up (from project root - run once)
bash RUN-setup_environments.sh
```

**Note:** `RUN-workflow.sh` automatically activates and deactivates the conda environment - no manual activation required.

**Environment provides:**
- Python 3.9+
- NextFlow 23.0+
- DIAMOND 2.0+

---

## Notes

- The NCBI nr DIAMOND database is ~100-150 GB
- DIAMOND searches are I/O intensive; use local scratch if available
- Each DIAMOND job uses 1 CPU and ~21 GB memory (configurable)
- With 40 splits per species and 67 species, this creates 2,680 parallel jobs
- Total pipeline runtime depends on cluster availability (~4-24 hours)

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
