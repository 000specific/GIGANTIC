# AI Guide: GIGANTIC Project

**For AI Assistants**: This is the master guide for GIGANTIC. Read this first when helping any user with a GIGANTIC project. Subproject and workflow guides reference this document - don't repeat information that's here.

---

## Quick Reference

| If user needs... | Go to... |
|------------------|----------|
| Project overview, directory structure | This file |
| Subproject-specific help | `subprojects/[name]/AI_GUIDE-[name].md` |
| Workflow execution help | `subprojects/[name]/nf_workflow-*/ai/AI_GUIDE-*_workflow.md` |

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
        ├── RUN-clean_subproject.sh      # Cleanup script (removes work/, .nextflow*)
        ├── RUN-update_upload_to_server.sh  # Updates server sharing symlinks
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
        └── nf_workflow-COPYME_NN-[description]/  # WORKFLOW TEMPLATE
            │
            ├── README.md                    # Quick start guide
            ├── RUN-[workflow].sh            # Local execution: bash RUN-*.sh
            ├── RUN-[workflow].sbatch        # SLURM execution: sbatch RUN-*.sbatch
            ├── [workflow]_config.yaml       # User configuration
            │
            ├── INPUT_user/                  # WORKFLOW INPUTS
            │   │                            # Copied from INPUT_gigantic/ at runtime
            │   └── [input files]            # Archived with this workflow run
            │
            ├── OUTPUT_pipeline/             # WORKFLOW OUTPUTS
            │   ├── N-output/                # Script N outputs (numbered for transparency)
            │   └── ...
            │
            └── ai/                          # INTERNAL (users don't touch)
                ├── AI_GUIDE-*_workflow.md   # Workflow-level AI guidance
                ├── main.nf                  # NextFlow pipeline
                ├── nextflow.config          # NextFlow settings
                └── scripts/                 # Python/Bash scripts
```

---

## Key Patterns

### INPUT_gigantic → INPUT_user Flow

```
INPUT_gigantic/species_list.txt     # User edits HERE (single source of truth)
        ↓ (copied by RUN script)
nf_workflow-*/INPUT_user/species_list.txt  # Archived copy for this run
```

**Why**: One place to edit, but each workflow run has its own archived copy.

### output_to_input Pattern

```
nf_workflow-*/OUTPUT_pipeline/3-output/map.tsv  # ACTUAL FILE
        ↓ (symlinked)
output_to_input/maps/map.tsv                     # SYMLINK (downstream subprojects read here)
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

| File | Command | Use When |
|------|---------|----------|
| `RUN-*.sh` | `bash RUN-*.sh` | Local machine, workstation |
| `RUN-*.sbatch` | `sbatch RUN-*.sbatch` | SLURM cluster (edit account/qos first) |

---

## Subproject Dependency Chain

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

**Quick reference**:
| Subproject | Prerequisites | Purpose |
|------------|---------------|---------|
| phylonames | None | Species name mappings from NCBI taxonomy |
| genomesDB | phylonames | Proteome databases and BLAST setup |
| trees_species | phylonames | All possible species tree topologies |
| orthogroups | genomesDB + trees_species | Ortholog group identification |
| annotations_hmms | genomesDB | Functional protein annotation |
| orthogroups_X_ocl | orthogroups + trees_species | Origin-Conservation-Loss analysis |
| annotations_X_ocl | annotations_hmms + orthogroups_X_ocl | Annotation-OCL integration |
| trees_gene_families | genomesDB + phylonames | Gene family phylogenies |

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
