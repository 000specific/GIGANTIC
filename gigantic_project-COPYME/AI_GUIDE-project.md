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
├── RUN-setup_environments.sh        # ONE-TIME: Creates all conda environments
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
├── INPUT_gigantic/                  # PROJECT-WIDE INPUTS
│   │                                # Users edit files here ONCE
│   │                                # RUN scripts copy to workflow INPUT_user/ for archival
│   ├── species_list.txt             # Canonical species list for the project
│   └── README.md
│
├── research_notebook/               # RESEARCH DOCUMENTATION
│   ├── research_user/               # User's personal workspace (no structure required)
│   │                                # Notes, literature, drafts - organize however you want
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
        │
        ├── README.md                    # Human documentation
        ├── AI_GUIDE-[name].md           # AI guidance (references this project guide)
        ├── RUN-clean_and_record_subproject.sh  # Cleanup + session recording
        ├── RUN-update_upload_to_server.sh      # Updates server sharing symlinks
        │
        ├── user_research/               # Subproject-specific personal workspace
        │                                # Alternative to research_notebook/research_user/
        │
        ├── output_to_input/             # OUTPUTS FOR OTHER SUBPROJECTS
        │   │                            # Contains symlinks to workflow outputs
        │   │                            # Other subprojects read from here
        │   └── maps/                    # (phylonames example)
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
        │   │   │                            # Copied from INPUT_gigantic/ at runtime
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

### INPUT_gigantic → INPUT_user Flow

```
INPUT_gigantic/species_list.txt     # User edits HERE (single source of truth)
        ↓ (copied by RUN script)
workflow-*/INPUT_user/species_list.txt  # Archived copy for this run
```

**Why**: One place to edit, but each workflow run has its own archived copy.

### output_to_input Pattern

```
workflow-*/OUTPUT_pipeline/3-output/map.tsv  # ACTUAL FILE
        ↓ (symlinked)
output_to_input/maps/map.tsv                  # SYMLINK (downstream subprojects read here)
```

**Why**: Single source of truth, no duplication, clear provenance.

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
genomesDB ──► gene_sizes             # Protein/gene size analysis
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
| orthogroups | genomesDB | Ortholog group identification | Functional |
| trees_gene_families | genomesDB | Gene family homolog discovery and phylogenetics | Functional |
| trees_gene_groups | genomesDB | Orthogroup-based phylogenetics | Structural |
| trees_species | phylonames | All possible species tree topologies | Planned |
| annotations_hmms | genomesDB | Functional protein annotation | Planned |
| orthogroups_X_ocl | orthogroups + trees_species | Origin-Conservation-Loss analysis | Planned |
| annotations_X_ocl | annotations_hmms + orthogroups_X_ocl | Annotation-OCL integration | Planned |
| gene_sizes | genomesDB | Protein/gene size analysis | Planned |
| synteny | genomesDB | Gene order conservation analysis | Planned |
| dark_proteome | genomesDB | Uncharacterized protein analysis | Planned |
| hot_spots | genomesDB | Evolutionary hotspot analysis | Planned |
| one_direction_homologs | genomesDB | One-way BLAST homolog identification | Planned |
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
- `INPUT_gigantic/species_list.txt` - do they have species listed?
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
→ `INPUT_gigantic/species_list.txt` (project root)

**"How do I run a workflow?"**
→ `bash RUN-*.sh` (local) or `sbatch RUN-*.sbatch` (SLURM)

**"Where are my results?"**
→ `OUTPUT_pipeline/` in the workflow directory

**"How do other subprojects get my results?"**
→ Via `output_to_input/` symlinks

**"Something failed, what now?"**
→ Check error message, read the workflow's AI_GUIDE, check log files

---

## Conda Environments

GIGANTIC uses centralized conda environment management:

```bash
# ONE-TIME SETUP (run once after copying project):
bash RUN-setup_environments.sh

# Environments are then activated automatically by RUN scripts
```

**Environment files location**: `conda_environments/ai_gigantic_[subproject].yml`

**Naming convention**: All environments begin with `ai_gigantic_` (e.g., `ai_gigantic_phylonames`)

**Why centralized**:
- Single setup command creates all environments
- Consistent naming across subprojects
- RUN scripts handle activation automatically

---

## For AI Assistants: Honesty About Mistakes

**Do not whitewash mistakes.**

When you make an error:
- Say "I was **incorrect**" or "I was **wrong**" - not "that was confusing"
- Acknowledge the actual mistake clearly
- Correct it without minimizing language

This builds trust with users who rely on accurate information.
