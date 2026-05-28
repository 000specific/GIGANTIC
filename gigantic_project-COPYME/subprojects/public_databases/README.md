# public_databases - Public Reference Database Downloads and Construction

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March 01 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent: [`../../README.md`](../../README.md) — gigantic_project-COPYME overview
- Subproject AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)
- Reads from: NCBI nr FTP (network download by script 001)
- Outputs to: `output_to_input/BLOCK_{ncbi_nr_blastp,ncbi_nr_diamond}/` — prepared databases
- Downstream consumers:
-   - `one_direction_homologs/` — uses the DIAMOND db (axis_a in dark_proteomes pipeline)
-   - Any subproject doing vs-nr search
- Two BLOCKs, both download the same NCBI nr FASTA and build a tool-specific database (blastp / diamond)
- Single shared conda env: `aiG-public_databases` (per §53 — both BLOCKs use the same blast/diamond toolset)

---

## Purpose

The public_databases subproject downloads, builds, and maintains public reference databases used by other GIGANTIC subprojects. Each database type is organized as a separate BLOCK, providing self-contained download and construction workflows.

**This subproject provides external reference databases** — all other GIGANTIC subprojects that search against public databases (e.g., NCBI nr) depend on public_databases for their pre-built, indexed databases.

---

## Current Blocks

### BLOCK_ncbi_nr_diamond

Downloads the NCBI non-redundant (nr) protein database and builds a DIAMOND-formatted database for high-throughput homology searches. DIAMOND provides ~1000x faster searching than BLAST with comparable sensitivity, making it ideal for large-scale proteome-level searches.

**Used by**: `one_direction_homologs/BLOCK_diamond_ncbi_nr` (species proteomes vs. NCBI nr)

### BLOCK_ncbi_nr_blastp

Downloads the NCBI non-redundant (nr) protein database and builds a BLAST-formatted protein database for high-quality homology searches. BLAST provides the gold-standard sensitivity for protein homology detection, ideal for targeted or publication-quality analyses.

**Used by**: `one_direction_homologs/BLOCK_blastp_ncbi_nr` (species proteomes vs. NCBI nr)

---

## NCBI Non-Redundant (nr) Protein Database

### What Is NCBI nr?

The NCBI non-redundant protein sequence database is a comprehensive collection of protein sequences from GenBank, RefSeq, PDB, SwissProt, PIR, and PRF. It contains hundreds of millions of protein sequences from across the tree of life.

### Key Characteristics

| Property | Value |
|----------|-------|
| Source | NCBI FTP (`ftp.ncbi.nlm.nih.gov/blast/db/FASTA/nr.gz`) |
| Size (compressed) | ~100 GB |
| Size (uncompressed FASTA) | ~300+ GB |
| DIAMOND database | ~150 GB |
| BLAST database | ~100+ GB |
| Update frequency | Weekly by NCBI |

### Why Version?

NCBI nr is updated weekly. Each download creates a versioned directory with the download date, ensuring:
- **Reproducibility**: Know exactly which database version produced your results
- **Comparison**: Multiple versions can coexist for comparison studies
- **Provenance**: Complete record of when databases were obtained

---

## Directory Structure

```
public_databases/
├── README.md                           # This file
├── AI_GUIDE.md        # AI assistant guidance (subproject level)
├── TODO.md                             # Outstanding tasks
├── user_research/                      # Personal workspace
├── upload_to_server/                   # Files to share via GIGANTIC server
│
├── output_to_input/                    # Outputs for downstream subprojects
│   ├── BLOCK_ncbi_nr_diamond/         # DIAMOND nr database location
│   └── BLOCK_ncbi_nr_blastp/          # BLAST nr database location
│
├── BLOCK_ncbi_nr_diamond/
│   ├── AI_GUIDE.md    # BLOCK-level AI guide
│   │
│   └── workflow-COPYME-download_build_ncbi_nr_diamond/
│       ├── README.md                   # Quick start guide
│       ├── RUN-workflow.sh             # bash RUN-workflow.sh (local)
│       ├── RUN-workflow.sh         # sbatch RUN-workflow.sh (SLURM)
│       ├── START_HERE-user_config.yaml # Edit this for your project
│       ├── INPUT_user/                 # No user inputs needed
│       ├── OUTPUT_pipeline/            # Downloaded and built database
│       └── ai/                         # Internal (don't touch)
│           ├── AI_GUIDE.md
│           ├── main.nf
│           ├── nextflow.config
│           └── scripts/
│               ├── 001_ai-bash-download_ncbi_nr.sh
│               ├── 002_ai-bash-build_diamond_database.sh
│               ├── 003_ai-python-validate_database.py
│               └── 004_ai-python-write_run_log.py
│
└── BLOCK_ncbi_nr_blastp/
    ├── AI_GUIDE.md      # BLOCK-level AI guide
    │
    └── workflow-COPYME-download_build_ncbi_nr_blastp/
        ├── README.md                   # Quick start guide
        ├── RUN-workflow.sh             # bash RUN-workflow.sh (local)
        ├── RUN-workflow.sh         # sbatch RUN-workflow.sh (SLURM)
        ├── START_HERE-user_config.yaml # Edit this for your project
        ├── INPUT_user/                 # No user inputs needed
        ├── OUTPUT_pipeline/            # Downloaded and built database
        └── ai/                         # Internal (don't touch)
            ├── AI_GUIDE.md
            ├── main.nf
            ├── nextflow.config
            └── scripts/
                ├── 001_ai-bash-download_ncbi_nr.sh
                ├── 002_ai-bash-build_blastp_database.sh
                ├── 003_ai-python-validate_database.py
                └── 004_ai-python-write_run_log.py
```

**AI Documentation**: Each workflow run creates a timestamped log in its own `ai/logs/` directory:
```
workflow-*/ai/logs/
```

This serves as an **AI lab notebook** — documenting what the workflow did, when, with what parameters, and what it produced.

---

## Quick Start

### DIAMOND Database (for high-throughput searches)

```bash
cd BLOCK_ncbi_nr_diamond/workflow-COPYME-download_build_ncbi_nr_diamond

# Edit configuration (download path, etc.)
nano START_HERE-user_config.yaml

# Edit SLURM account/qos in sbatch file
nano RUN-workflow.sh

# Run (SLURM recommended — downloads are large)
sbatch RUN-workflow.sh
```

### BLAST Database (for high-quality searches)

```bash
cd BLOCK_ncbi_nr_blastp/workflow-COPYME-download_build_ncbi_nr_blastp

# Edit configuration (download path, etc.)
nano START_HERE-user_config.yaml

# Edit SLURM account/qos in sbatch file
nano RUN-workflow.sh

# Run (SLURM recommended — downloads are large)
sbatch RUN-workflow.sh
```

---

## Disk Space Requirements

**IMPORTANT**: Building public databases requires substantial disk space.

| Database | Download | Uncompressed | Built Database | Total Needed |
|----------|----------|--------------|----------------|--------------|
| DIAMOND nr | ~100 GB | ~300 GB | ~150 GB | ~550 GB |
| BLAST nr | ~100 GB | ~300 GB | ~100 GB | ~500 GB |

The workflow cleans up intermediate files (uncompressed FASTA) after database construction to save space. Final disk usage is approximately:
- DIAMOND: ~250 GB (compressed download + built database)
- BLAST: ~200 GB (compressed download + built database)

---

## Outputs Shared Downstream (`output_to_input/`)

Other GIGANTIC subprojects reference these databases via `output_to_input/`:

```
public_databases/output_to_input/BLOCK_ncbi_nr_diamond/    # DIAMOND nr database
public_databases/output_to_input/BLOCK_ncbi_nr_blastp/     # BLAST nr database
```

**Dependent subprojects**:
- **one_direction_homologs** — Uses DIAMOND nr for proteome-level homolog searches
- **one_direction_homologs** — Uses BLAST nr for high-quality proteome-level homolog searches

---

## Adding New Public Databases

To add a new public database (e.g., UniProt, Pfam, InterPro):

1. Create a new BLOCK directory: `BLOCK_[database_name]/`
2. Model the workflow after existing BLOCKs
3. Add an entry to `output_to_input/` for downstream access
4. Update this README with the new BLOCK description
5. Write methods text in `ai_text_for_paper/public_databases/`

---

## Dependencies

All dependencies are provided by the `ai_gigantic_public_databases` conda environment:

```bash
# Set up (from project root — run once)
bash RUN-setup_environments.sh
```

**Note:** `RUN-workflow.sh` automatically activates and deactivates the conda environment — no manual activation required.

**Environment provides:**
- Python 3.9+
- NextFlow 23.0+
- DIAMOND (for BLOCK_ncbi_nr_diamond)
- BLAST+ (for BLOCK_ncbi_nr_blastp)
- wget/curl (for downloads)

---

## Notes

- NCBI nr downloads can take several hours depending on network speed
- Database construction (especially DIAMOND) is CPU and memory intensive
- SLURM execution is strongly recommended for both download and build steps
- Each BLOCK is fully independent — you can build DIAMOND, BLAST, or both
- The `.gitignore` in each BLOCK excludes the large database files from version control

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
