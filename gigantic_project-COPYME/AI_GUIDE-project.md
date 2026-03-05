# AI Guide: GIGANTIC Project

**For AI Assistants**: This is the master guide for GIGANTIC. Read this first when helping any user with a GIGANTIC project. Subproject and workflow guides reference this document - don't repeat information that's here.

---

## ⚠️ CRITICAL: Surface Discrepancies - No Silent Changes

**The user is managing this project - you must surface discrepancies so the user can make decisions. Silent changes undermine project management.**

- ❌ **NEVER** silently do something different than requested
- ❌ **NEVER** assume you know better and proceed without asking
- ✅ **ALWAYS** stop and explain the discrepancy
- ✅ **ALWAYS** ask for clarification before proceeding

**Example**: If user says "put this in script 3" but script 3 handles genomes not proteomes, you must say: "Script 003 handles genomes, not proteomes - did you mean script 002, or should I create a new script?"

---

## Quick Reference

| If user needs... | Go to... |
|------------------|----------|
| Project overview, directory structure | This file |
| Subproject-specific help | `subprojects/[name]/AI_GUIDE-[name].md` |
| Workflow execution help | `subprojects/[name]/workflow-*/ai/AI_GUIDE-*_workflow.md` |

---

## What GIGANTIC Is

**GIGANTIC** = Genome Integration and Gene Analysis across Numerous Topology-Interrogated Clades

A modular phylogenomics platform for comparative genomics. Key facts:
- **AI-native**: AI assistants are the expected way users run GIGANTIC
- **Developed through**: AI pair programming (Claude Code, Opus 4.5) with Eric Edsinger
- Users copy `gigantic_project-COPYME/` and rename it for their project

---

## Complete Directory Structure

All paths are relative to `gigantic_project-[project_name]/` (the copied project root).

```
gigantic_project-[project_name]/
│
├── AI_GUIDE-project.md              # THIS FILE - project-level AI guidance
├── RUN-setup_environments.sh        # OPTIONAL: Pre-creates all conda environments (on-demand by default)
├── RUN-record_project.sh            # Extract Claude sessions for entire project
│
├── ai/                              # AI TOOLS
│   └── tools/                       # Extraction and utility scripts
│       └── 001_ai-python-extract_claude_sessions.py
│
├── conda_environments/              # CONDA ENVIRONMENT DEFINITIONS
│   ├── README.md                    # Environment documentation
│   └── ai_gigantic_[subproject].yml # One file per subproject
│
├── INPUT_user/                      # USER-PROVIDED GENOMIC RESOURCES
│   │                                # RUN scripts copy relevant files to workflow INPUT_user/ for archival
│   ├── README.md                    # "Start Here" - formatting instructions
│   ├── species_set/
│   │   └── species_list.txt         # Canonical species list for the project
│   └── genomic_resources/
│       ├── genomes/                 # Genome assembly .fasta files
│       ├── proteomes/               # Proteome amino acid .aa files
│       ├── annotations/             # GFF3/GTF annotation files
│       └── maps/                    # Identifier mapping .tsv files
│
├── research_notebook/               # RESEARCH DOCUMENTATION
│   ├── research_user/               # User's open sandbox (no structure, no rules)
│   │                                # Use for anything - notes, literature, drafts, analyses
│   └── research_ai/                 # AI-generated documentation
│       ├── project/                 # Project-level AI sessions
│       │   ├── sessions/            # Conversation logs and summaries
│       │   ├── validation/          # QC scripts
│       │   ├── logs/                # Script execution logs
│       │   └── debugging/           # Troubleshooting scripts
│       └── subproject-[name]/       # Per-subproject AI documentation
│           └── [same structure]
│
└── subprojects/                     # ANALYSIS MODULES
    │
    └── [subproject_name]/           # Each subproject follows this pattern:
        │                            # May contain STEP_N-name/ (sequential) or
        │                            # BLOCK_name/ (standalone) subdirectories
        │
        ├── README.md                    # Human documentation
        ├── AI_GUIDE-[name].md           # AI guidance (references this project guide)
        ├── RUN-clean_and_record_subproject.sh  # Cleanup + session recording
        ├── RUN-update_upload_to_server.sh      # Updates server sharing symlinks
        │
        ├── user_research/               # Subproject-specific personal workspace
        │                                # Alternative to project-level research_notebook/research_user/
        │
        ├── output_to_input/             # OUTPUTS FOR OTHER SUBPROJECTS
        │   │                            # Single canonical location per subproject
        │   │                            # Contains BLOCK_X/ or STEP_X/ subdirectories
        │   │                            # RUN-workflow.sh creates symlinks here
        │   │                            # Other subprojects read from here
        │   ├── BLOCK_X/                 # (orthogroups example - one dir per BLOCK)
        │   ├── STEP_2-standardize/      # (genomesDB example - one dir per STEP)
        │   └── maps/                    # (phylonames example - flat subproject)
        │
        ├── upload_to_server/            # OUTPUTS FOR GIGANTIC SERVER
        │   ├── upload_manifest.tsv      # Controls what gets shared
        │   └── [symlinks]               # Created by RUN-update_upload_to_server.sh
        │
        ├── workflow-COPYME-[name]/          # WORKFLOW TEMPLATE (not numbered)
        │   │                                # Only ONE COPYME per workflow type
        │   │
        │   ├── README.md                    # Quick start guide
        │   ├── RUN-workflow.sh              # Local execution: bash RUN-workflow.sh
        │   ├── RUN-workflow.sbatch          # SLURM execution: sbatch RUN-workflow.sbatch
        │   ├── [workflow]_config.yaml       # User configuration
        │   │
        │   ├── INPUT_user/                  # WORKFLOW INPUTS
        │   │   │                            # Copied from project INPUT_user/ at runtime
        │   │   └── [input files]            # Archived with this workflow run
        │   │
        │   ├── OUTPUT_pipeline/             # WORKFLOW OUTPUTS
        │   │   ├── N-output/                # Script N outputs (numbered for transparency)
        │   │   └── ...
        │   │
        │   └── ai/                          # INTERNAL (users don't touch)
        │       ├── AI_GUIDE-*_workflow.md   # Workflow-level AI guidance
        │       ├── main.nf                  # NextFlow pipeline
        │       ├── nextflow.config          # NextFlow settings
        │       └── scripts/                 # Python/Bash scripts
        │
        └── workflow-RUN_XX-[name]/          # WORKFLOW RUN INSTANCES (numbered)
            │                                # Copy from COPYME, increment XX for each run
            └── [same structure as COPYME]
```

---

## Key Patterns

### Project INPUT_user → Workflow INPUT_user Flow

```
INPUT_user/                              # User places species list + genomic files HERE
├── species_set/
│   └── species_list.txt                 # Project-wide DEFAULT species list
└── genomic_resources/
    ├── genomes/                         # Genome assembly .fasta files
    ├── proteomes/                       # Proteome .aa files
    ├── annotations/                     # GFF3/GTF annotation files
    └── maps/                            # Identifier mapping .tsv files

Species list resolution (by RUN-workflow.sh):
  1. workflow-*/INPUT_user/species_list.txt   ← checked FIRST (user override)
  2. INPUT_user/species_set/species_list.txt  ← used as DEFAULT (copied to workflow)
```

**Why**: One place for all user-provided genomic resources, organized by type. The species list uses an override pattern: the project-level list is the default, but any workflow can override it with its own list. Each workflow run ends up with a copy in its INPUT_user/ for archival. Genomic files are referenced by manifests in workflow-level INPUT_user directories.

### Core Design Principle: Scripts Own the Data, NextFlow Manages Execution

**GIGANTIC is a scientific research platform, not a software application.** This fundamental distinction drives a non-negotiable design principle:

**Every script reads its inputs from `OUTPUT_pipeline/N-output/` and writes its outputs to `OUTPUT_pipeline/N-output/`.** NextFlow orchestrates the execution ORDER of scripts but does NOT silently transfer data between them through internal channels. All intermediate results must be recorded in `OUTPUT_pipeline/N-output/` where they are:

- **Inspectable**: A researcher can examine any step's output directly
- **Verifiable**: Results can be validated independently at each stage
- **Reproducible**: Another researcher (or your future self) can see exactly what happened
- **Debuggable**: When something goes wrong, you can trace the data step by step

**NextFlow's role in GIGANTIC**: NextFlow is an execution manager, not a data broker. It determines WHEN scripts run (dependency ordering, parallelization, retry logic). It does NOT determine WHERE data lives. Scripts handle their own I/O through the transparent `OUTPUT_pipeline/N-output/` directory structure.

**Why this matters**: In scientific computing, "trust me, the intermediate data is somewhere in a hashed work directory" is not acceptable. Every intermediate result is part of the scientific record. Completing a pipeline with invisible intermediate data is worse than failing - it produces results that cannot be independently verified. This principle applies even when transparent data handling costs additional disk space.

**Contrast with application development**: Software applications optimize for efficiency and can use opaque internal data channels because the end product (a working app) is what matters. In research, the process IS the product - understanding how results were derived is as important as the results themselves.

### Pipeline Output Lifecycle: work/ → OUTPUT_pipeline/ → output_to_input/

GIGANTIC workflows follow a three-stage data lifecycle:

```
1. Nextflow runs scripts in work/         # Cryptic hashed directories (for caching)
       ↓ (publishDir)
2. OUTPUT_pipeline/N-output/              # Human-readable, numbered by script
       ↓ (RUN-workflow.sh creates symlinks)
3. output_to_input/                       # Downstream subprojects read from here
```

**Stage 1**: Nextflow executes scripts in `work/` using hashed subdirectory names. Not human-navigable.

**Stage 2**: Each script's outputs are copied via `publishDir` to `OUTPUT_pipeline/N-output/` (where N matches the script number: 001 → `1-output/`). This is where users browse results. **This is the authoritative location for all intermediate and final results.**

**Stage 3**: After the pipeline completes, `RUN-workflow.sh` creates symlinks in the subproject's single `output_to_input/` directory:
- **Subproject root** `output_to_input/BLOCK_X/` or `output_to_input/STEP_X-name/` → downstream subprojects read from here
- Each BLOCK or STEP gets its own subdirectory under `output_to_input/`
- The latest workflow run "wins" the slot (overwrites existing symlinks)

**Disk efficiency**: Data files exist only in `OUTPUT_pipeline/`. Symlinks add zero disk usage. The `RUN-clean_and_record_subproject.sh` script removes `work/`, `.nextflow/`, and `.nextflow.log*` after successful runs to reclaim temporary disk space while preserving all outputs and symlinks.

### output_to_input Pattern

Each subproject has exactly **one** `output_to_input/` directory at its root. Inside are subdirectories for each BLOCK or STEP:

```
# BLOCK-based subproject (e.g., orthogroups):
subprojects/orthogroups/
├── BLOCK_orthofinder/workflow-RUN_01-*/OUTPUT_pipeline/3-output/results.tsv  # ACTUAL FILE
│       ↓ (symlinked by RUN-workflow.sh)
└── output_to_input/BLOCK_orthofinder/results.tsv                             # SYMLINK

# STEP-based subproject (e.g., genomesDB):
subprojects/genomesDB/
├── STEP_2-standardize_and_evaluate/workflow-RUN_01-*/OUTPUT_pipeline/...     # ACTUAL FILE
│       ↓ (symlinked by RUN-workflow.sh)
└── output_to_input/STEP_2-standardize_and_evaluate/speciesN_proteomes/      # SYMLINK

# Flat subproject (e.g., phylonames):
subprojects/phylonames/
├── workflow-RUN_01-*/OUTPUT_pipeline/3-output/map.tsv                        # ACTUAL FILE
│       ↓ (symlinked by RUN-workflow.sh)
└── output_to_input/maps/map.tsv                                              # SYMLINK
```

**Key principles**:
- One `output_to_input/` per subproject (never inside BLOCK or STEP directories)
- BLOCK/STEP subdirectories organize outputs by source
- Latest workflow run overwrites existing symlinks (latest run "wins")
- No archival copies at the workflow level -- provenance is tracked by which RUN directory the symlinks point to
- `.gitignore` files in each BLOCK/STEP subdirectory track empty directories in version control

**Why**: Single source of truth, no data duplication, clear provenance, minimal disk footprint.

### upload_to_server Pattern

```
upload_to_server/upload_manifest.tsv  # User edits to select what to share
        ↓ (RUN-update_upload_to_server.sh)
upload_to_server/[symlinks]           # GIGANTIC server scans these
```

**Why**: User controls sharing; manifest documents decisions.

### RUN File Convention

Every workflow has exactly two runner files with standardized names:

| File | Command | Use When |
|------|---------|----------|
| `RUN-workflow.sh` | `bash RUN-workflow.sh` | Local machine, workstation |
| `RUN-workflow.sbatch` | `sbatch RUN-workflow.sbatch` | SLURM cluster (edit account/qos first) |

The workflow directory name provides context (e.g., `workflow-COPYME-generate_phylonames/RUN-workflow.sh`). The RUN files themselves are always named `RUN-workflow.*` for consistency across all subprojects.

**Conda lifecycle**: All environment activation and deactivation is handled within `RUN-workflow.sh`. The `.sbatch` file is a thin wrapper (~25 lines) containing only SLURM resource directives and `bash RUN-workflow.sh` - it never manages conda.

**SLURM resource allocation**: HiPerGator allocates 7.5 GB RAM per CPU. All `.sbatch` files follow the rule `--mem = --cpus-per-task × 7.5 GB`. Under-allocating resources (e.g., 2 CPUs / 8 GB) can cause NextFlow to hang indefinitely during JVM startup on compute nodes, even though the same workflow runs fine locally. If a SLURM job appears stuck at "Running NextFlow pipeline..." with no processes starting, the most likely cause is insufficient resource allocation. Increase CPUs and memory before investigating other causes. On other HPC systems, check your cluster's RAM-per-CPU ratio and adjust accordingly.

### Long-Running Jobs

Some GIGANTIC workflows run for days or even weeks (e.g., OrthoFinder on large species sets, IQ-TREE phylogenetics). How to handle this depends on how you're running the workflow:

| Execution Method | Duration Safety | What Happens if You Disconnect |
|------------------|----------------|-------------------------------|
| `sbatch RUN-workflow.sbatch` | Safe - SLURM manages the job | Job keeps running. Reconnect anytime. |
| `bash RUN-workflow.sh` via SSH | **Dangerous** - process tied to SSH session | Job is killed when SSH drops |
| `bash RUN-workflow.sh` on local machine | Process tied to terminal | Job is killed if terminal closes |

**For SLURM clusters (recommended for long jobs):**

Use `sbatch` - this is the safest option. Once submitted, the job is managed entirely by the SLURM scheduler. You can close your laptop, disconnect from SSH, or log out. The job continues running. Check on it later with `squeue -u $USER` or `sacct`.

**For non-SLURM remote servers (SSH):**

Use `screen` or `tmux` to create a persistent terminal session that survives SSH disconnections:

```bash
# Start a screen session
screen -S my_workflow

# Run the workflow inside screen
cd workflow-RUN_01-generate_phylonames/
bash RUN-workflow.sh

# Detach from screen (workflow keeps running): Ctrl+A then D
# Reconnect later:
screen -r my_workflow
```

**For local machines:**

Long-running workflows are rare on local machines, but if needed, use `screen` or `tmux` as described above to protect against accidental terminal closure.

**Nextflow's `-resume` as a safety net:**

If a workflow is interrupted for any reason, Nextflow can pick up where it left off:

```bash
cd workflow-RUN_01-generate_phylonames/
# Re-run with -resume flag - completed steps are cached and skipped
nextflow run ai/main.nf -resume
```

This works because Nextflow caches completed process outputs in the `work/` directory. Only incomplete or failed steps are re-executed. Note: this must be run from the workflow directory, not through `RUN-workflow.sh` (which runs fresh by default).

### Workflow Naming Convention (COPYME/RUN)

GIGANTIC uses a **COPYME/RUN naming system** for workflows:

| Type | Naming Pattern | Description |
|------|----------------|-------------|
| **COPYME** (template) | `workflow-COPYME-[name]` | The template workflow. NOT numbered. Only ONE COPYME per workflow type. |
| **RUN** (instance) | `workflow-RUN_XX-[name]` | Numbered copies for actual runs. Each run gets its own directory. |

**Examples:**
```
workflow-COPYME-generate_phylonames    # Template (this is what you copy)
workflow-RUN_01-generate_phylonames    # First run instance
workflow-RUN_02-generate_phylonames    # Second run instance
```

**To create a new run:**
```bash
# From the subproject directory
cp -r workflow-COPYME-[name] workflow-RUN_01-[name]
cd workflow-RUN_01-[name]
# Edit config, add inputs, then run
```

**Key Principles:**
- COPYME stays clean as the template - never run workflows directly in COPYME
- All actual work happens in RUN_XX directories
- Increment the number (RUN_01, RUN_02, ...) for each new run
- Each RUN directory preserves its own inputs and outputs for reproducibility

### Graceful Species Dropping (Data Availability Pattern)

Some subprojects require per-species input data that may not be available for all species
in the GIGANTIC set (e.g., gene annotations, transcriptomes, experimental data). For these
subprojects, GIGANTIC uses a **three-tier species processing status** instead of fail-hard:

| Status | Meaning |
|--------|---------|
| **PROCESSED** | Species has valid input data and was fully processed |
| **SKIPPED_NO_DATA** | No input file provided by user (expected for many species) |
| **SKIPPED_INCOMPLETE** | File exists but data failed validation |

**Why not fail-hard?** Missing per-species data is a **data availability limitation**, not a
pipeline error. Not all species have published gene annotations, transcriptomes, or other
specialized data types. The pipeline processes what it can and clearly reports what was
skipped and why.

**When to use this pattern**:
- Subproject inputs depend on external data availability (not all species have it)
- User provides per-species files and some species genuinely lack source data
- Skipping a species does not invalidate the analysis for other species

**When NOT to use this pattern** (use fail-hard instead):
- Core pipeline data (proteomes, species lists) - these MUST be present
- Intermediate pipeline outputs - if Script 002 fails, Script 003 should not run
- Data that should always exist if upstream subprojects completed successfully

**Implementation pattern**:
1. Script 001 validates all species and classifies each as PROCESSED/SKIPPED_NO_DATA/SKIPPED_INCOMPLETE
2. Produces a `species_processing_status.tsv` documenting every species and its status
3. Downstream scripts only process PROCESSED species
4. Final summary includes the processing status for transparency

**Current subprojects using this pattern**: gene_sizes

### Subproject Internal Organization: STEPs and BLOCKs

Subprojects organize their internal workflow directories using two patterns:

| Pattern | Format | Relationship | Example |
|---------|--------|-------------|---------|
| **STEP** | `STEP_N-name/` | Sequential (N depends on N-1) | `STEP_1-sources/ → STEP_2-standardize/ → STEP_3-databases/` |
| **BLOCK** | `BLOCK_name/` | Standalone (run independently) | `BLOCK_orthofinder/`, `BLOCK_orthohmm/`, `BLOCK_broccoli/` |

**STEPs** are sequential: each step depends on the output of the previous step. Used when there is a linear pipeline (e.g., genomesDB: ingest → standardize → build databases → finalize species set). Each STEP contains its own `workflow-COPYME-*/` workflow.

**BLOCKs** are standalone: each block can run independently and in parallel. Used when multiple equivalent analyses operate on the same input (e.g., orthogroups: three tools all run on the same proteomes). Each BLOCK contains its own `workflow-COPYME-*/` workflow.

Both STEPs and BLOCKs follow the same internal structure: `workflow-COPYME-*/`, `AI_GUIDE-*.md`, `README.md`. Their outputs are shared via the subproject-root `output_to_input/` directory (not within each BLOCK/STEP). See the "output_to_input Pattern" section above.

**Subprojects using STEPs**: genomesDB, trees_gene_families, trees_gene_groups
**Subprojects using BLOCKs**: orthogroups, trees_species, annotations_hmms, gene_sizes

### Session Provenance Recording (AI-Native Feature)

GIGANTIC automatically extracts Claude Code session summaries for research documentation:

```bash
# Project level: Record all sessions (project + subprojects + workflows)
bash RUN-record_project.sh

# Subproject level: Cleanup with optional session recording
bash RUN-clean_and_record_subproject.sh --record-sessions
bash RUN-clean_and_record_subproject.sh --all  # cleanup + recording
```

**Output locations**:
```
research_notebook/research_ai/
├── project/sessions/
│   ├── session_*.md                 # Extracted compaction summaries
│   └── SESSION_EXTRACTION_LOG.md    # Activity log
└── subproject-[name]/sessions/
    └── ...                          # Same structure per subproject
```

**Why This Matters**:
- Scientific research requires complete provenance
- AI sessions are treated as first-class research artifacts
- Enables reproducibility and transparency in AI-assisted research
- Safe to run multiple times (overwrites with complete current state)

---

## Subproject Dependency Chain

### Core Pipeline

```
[1] phylonames                 # MUST RUN FIRST - generates species identifiers
       │
       ▼
[2] genomesDB ─────────────────┐
       │    (uses phylonames   │
       │     for file naming)  │
       ▼                       │
[3] trees_species ─────────────┤
       │                       │
       ├───────────┬───────────┤
       │           │           │
       ▼           ▼           │
[4] orthogroups  [5] annotations_hmms
       │           │           │
       ▼           │           │
[6] orthogroups_X_ocl ◄────────┘
       │
       ▼
[7] annotations_X_ocl
```

### Additional Subprojects

These subprojects connect to the core pipeline at various points:

```
genomesDB ──► trees_gene_families    # Gene family homolog discovery and phylogenetics
genomesDB ──► trees_gene_groups      # Orthogroup-based phylogenetics
genomesDB ──► gene_sizes             # Gene structure metrics and size analysis
gene_sizes + orthogroups ──► gene_sizes_X_integrations  # dN/dS, rank deviation, enrichment
genomesDB ──► synteny                # Gene order conservation analysis
genomesDB ──► dark_proteome          # Uncharacterized protein analysis
genomesDB ──► one_direction_homologs # One-way BLAST homolog identification
genomesDB ──► xenologs_vs_artifacts  # Xenolog detection and artifact filtering
genomesDB ──► transcriptomes         # Transcriptome integration
genomesDB ──► rnaseq_integration     # RNA-seq expression data integration
genomesDB ──► gene_names             # Comprehensive gene naming
genomesDB ──► hgnc_automation        # Automated reference gene set generation
genomesDB ──► hot_spots              # Evolutionary hotspot analysis
```

### Complete Subproject Reference

| Subproject | Prerequisites | Purpose | Status |
|------------|---------------|---------|--------|
| phylonames | None | Species name mappings from NCBI taxonomy | Operational |
| genomesDB | phylonames | Proteome databases and BLAST setup | Operational |
| orthogroups | genomesDB | Ortholog group identification (uses BLOCKs: orthofinder, orthohmm, broccoli, comparison) | Functional |
| trees_gene_families | genomesDB | Gene family homolog discovery and phylogenetics | Functional |
| trees_gene_groups | genomesDB | Orthogroup-based phylogenetics | Structural |
| trees_species | phylonames | Species tree topology permutations and phylogenetic features (uses BLOCKs: permutations_and_features, de_novo_species_tree) | Functional |
| annotations_hmms | genomesDB | Functional protein annotation | Planned |
| orthogroups_X_ocl | orthogroups + trees_species | Origin-Conservation-Loss analysis | Planned |
| annotations_X_ocl | annotations_hmms + orthogroups_X_ocl | Annotation-OCL integration | Planned |
| gene_sizes | genomesDB | Gene structure size analysis (user-provided CDS intervals) | Functional |
| gene_sizes_X_integrations | gene_sizes + orthogroups | dN/dS, rank deviation, functional enrichment by gene size | Planned |
| synteny | genomesDB | Gene order conservation analysis | Planned |
| dark_proteome | genomesDB | Uncharacterized protein analysis | Planned |
| hot_spots | genomesDB | Evolutionary hotspot analysis | Planned |
| one_direction_homologs | genomesDB | One-way DIAMOND homolog identification against NCBI nr | Structural |
| xenologs_vs_artifacts | genomesDB | Xenolog detection and artifact filtering | Planned |
| transcriptomes | genomesDB | Transcriptome integration | Planned |
| rnaseq_integration | genomesDB | RNA-seq expression data integration | Planned |
| gene_names | genomesDB | Comprehensive gene naming | Planned |
| hgnc_automation | genomesDB | Automated reference gene set generation | Planned |

---

## Phyloname Formats (Critical Concept)

GIGANTIC uses standardized species identifiers throughout:

| Format | Structure | Example | Use |
|--------|-----------|---------|-----|
| `phyloname` | `Kingdom_Phylum_Class_Order_Family_Genus_species` | `Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens` | Data tables, analysis |
| `phyloname_taxonid` | Same + `___taxonID` | `..._Homo_sapiens___9606` | File naming (unique) |

**To extract genus_species from phyloname**:
```python
parts = phyloname.split('_')
genus_species = parts[5] + '_' + '_'.join(parts[6:])
```

---

## How to Help Users

### Step 1: Identify Location

Ask: "What subproject are you working on?" or check their current directory:
```bash
pwd
```

### Step 2: Read Appropriate Guide

- **Project-level issues**: This file
- **Subproject issues**: `subprojects/[name]/AI_GUIDE-[name].md`
- **Workflow execution**: `ai/AI_GUIDE-*_workflow.md` inside the workflow

### Step 3: Check Configuration

Look at these files:
- `INPUT_user/species_set/species_list.txt` - do they have species listed?
- `[workflow]_config.yaml` - is project name set?
- `RUN-*.sbatch` - is account/qos configured? (SLURM only)

### Step 4: Check Logs

If something failed:
```bash
# Check workflow logs
ls OUTPUT_pipeline/

# Check SLURM logs
ls slurm_logs/

# Check NextFlow logs
cat .nextflow.log
```

### Step 5: Guide Step by Step

Users may not be bioinformatics experts. Give specific commands, not general advice.

---

## Common User Questions

**"Where do I start?"**
→ `subprojects/phylonames/`. Run this first.

**"Where do I put my species list?"**
→ `INPUT_user/species_set/species_list.txt` (project-wide default). To override for a specific workflow, place a `species_list.txt` in that workflow's `INPUT_user/` directory.

**"How do I run a workflow?"**
→ `bash RUN-*.sh` (local) or `sbatch RUN-*.sbatch` (SLURM)

**"Where are my results?"**
→ `OUTPUT_pipeline/` in the workflow directory

**"How do other subprojects get my results?"**
→ Via `output_to_input/` symlinks

**"Something failed, what now?"**
→ Check error message, read the workflow's AI_GUIDE, check log files

**"My workflow will run for days - how do I keep it running?"**
→ Use `sbatch` on SLURM (safest). For SSH sessions, use `screen` or `tmux`. See "Long-Running Jobs" above.

---

## Conda Environments

GIGANTIC uses **on-demand** conda environment management. Each subproject's `RUN-workflow.sh` automatically creates its conda environment on first run if it doesn't exist yet.

```bash
# ON-DEMAND (automatic): Just run a workflow - its env is created if missing
cd subprojects/phylonames/.../workflow-RUN_1-generate_phylonames/
bash RUN-workflow.sh  # Creates ai_gigantic_phylonames env if needed

# BULK (optional): Pre-create ALL environments at once
bash RUN-setup_environments.sh
```

**Environment files location**: `conda_environments/ai_gigantic_[subproject].yml`

**Naming convention**: All environments begin with `ai_gigantic_` (e.g., `ai_gigantic_phylonames`)

**NextFlow availability**: Each `RUN-workflow.sh` tries NextFlow from the conda env first. If not available there, it falls back to `module load nextflow` (for HPC systems like HiPerGator). On some HPC systems, NextFlow from conda may not install correctly due to Java conflicts - the module fallback handles this transparently.

**Design rationale**:
- On-demand creation means users only install what they need
- No upfront setup step required - just run a workflow
- `RUN-setup_environments.sh` remains available for bulk creation
- Consistent `ai_gigantic_` naming makes GIGANTIC envs easy to identify in `conda env list`

---

## For AI Assistants: Honesty About Mistakes

**Do not whitewash mistakes.**

When you make an error:
- Say "I was **incorrect**" or "I was **wrong**" - not "that was confusing"
- Acknowledge the actual mistake clearly
- Correct it without minimizing language

This builds trust with users who rely on accurate information.
