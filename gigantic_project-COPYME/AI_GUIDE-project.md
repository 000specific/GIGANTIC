# AI Guide: GIGANTIC Project Template

**Purpose**: This document helps AI assistants understand GIGANTIC and guide users through their projects.

**For AI Assistants**: Read this file when helping a user with any GIGANTIC project.

---

## About GIGANTIC

**GIGANTIC** = Genome Integration and Gene Analysis across Numerous Topology-Interrogated Clades

A modular phylogenomics platform for comparative genomics, developed through AI pair programming (Claude Code, Opus 4.5) with human collaborator Eric Edsinger.

**Key philosophy**: AI assistants are the expected way for users to run GIGANTIC workflows.

---

## How Users Start a Project

1. Clone the GIGANTIC repository from GitHub
2. Copy `gigantic_project-COPYME/` to their working location
3. Rename it for their project using the pattern: `gigantic_project-your_project_name`
4. Work within their copied project - it's completely self-contained

```bash
git clone https://github.com/000specific/GIGANTIC.git
cp -r GIGANTIC/gigantic_project-COPYME ~/my_projects/gigantic_project-cephalopod_evolution/
cd ~/my_projects/gigantic_project-cephalopod_evolution/
```

### Project Naming Convention

Projects follow the pattern: `gigantic_project-user_provided_project_name`

Examples:
- `gigantic_project-cephalopod_evolution`
- `gigantic_project-early_animal_phylogenomics`
- `gigantic_project-mollusc_neural_genes`

---

## Project Structure

```
gigantic_project-COPYME/               # Copy and rename for your project
├── AI_GUIDE-project.md                # This file - high-level GIGANTIC guidance
├── research_notebook/                 # Documentation and research records
│   ├── research_user/                 # User's personal workspace
│   └── research_ai/                   # AI session documentation
└── subprojects/                       # GIGANTIC analysis modules
    ├── phylonames/                    # [1] Phylogenetic naming system
    ├── genomesDB/                     # [2] Proteome database setup
    ├── annotations_hmms/              # [3] Functional annotation
    ├── orthogroups/                   # [4] Ortholog identification
    ├── trees_species/                 # [5] Species tree topologies
    ├── trees_gene_families/           # [6] Gene family phylogenetics
    ├── orthogroups_X_ocl/             # [7] Origin-Conservation-Loss analysis
    └── annotations_X_ocl/             # [8] Annotation-OCL integration
```

---

## The Research Notebook Philosophy

### Why `research_notebook/`?

**AI sessions ARE research.** Working with an AI assistant on computational biology is equivalent to working at the bench - it produces results, insights, and decisions that need to be documented.

Just as wet-lab scientists maintain lab notebooks to record experiments, computational researchers using GIGANTIC should maintain a research notebook of their AI-assisted work.

### `research_user/` - Your Personal Workspace

This is **your playground**. Use it for:
- Personal notes and documentation
- Literature references
- Draft manuscripts and figures
- Meeting notes
- Exploratory analyses
- Anything related to your project

**No structure requirements** - organize it however works for you.

### `research_ai/` - Consolidated AI Documentation

This is where **all AI-generated documentation** lives - organized like sections of a lab notebook:
- Session transcripts and summaries
- Validation scripts and their outputs
- Log files from pipeline runs
- Debugging notes
- Decision records from AI conversations

**Structured by subproject**:
```
research_ai/
├── project/                       # Project-level sessions
│   ├── sessions/
│   ├── validation/
│   ├── logs/
│   └── debugging/
├── subproject-phylonames/         # Phylonames AI documentation
│   ├── sessions/
│   ├── validation/
│   ├── logs/
│   └── debugging/
├── subproject-genomesDB/          # GenomesDB AI documentation
├── subproject-annotations_hmms/   # ...and so on for each subproject
└── ...
```

**AI assistants**: Save documentation to the appropriate `subproject-[name]/` folder.

### The Separation Matters

Keeping `research_user/` and `research_ai/` separate ensures:
- User's personal organization isn't constrained by AI conventions
- AI-generated content is clearly identified
- Both are preserved for scientific record
- Easy to find what you're looking for

---

## Subproject Overview

| # | Subproject | What It Does | Run First? |
|---|-----------|--------------|------------|
| 1 | `phylonames` | Generate species name mappings from NCBI taxonomy | **YES - Run first** |
| 2 | `genomesDB` | Set up proteome databases and BLAST | After phylonames |
| 3 | `annotations_hmms` | Functional protein annotation | After genomesDB |
| 4 | `orthogroups` | Identify ortholog groups | After genomesDB + trees_species |
| 5 | `trees_species` | Generate all possible species tree topologies | After phylonames |
| 6 | `trees_gene_families` | Build gene family phylogenies | After genomesDB |
| 7 | `orthogroups_X_ocl` | Analyze evolutionary dynamics | After orthogroups + trees_species |
| 8 | `annotations_X_ocl` | Integrate annotations with evolution | After annotations + OCL |

**Each subproject has its own `AI_GUIDE-[subproject].md`** with specific instructions.

---

## Key Concepts

### Phylonames

GIGANTIC uses standardized species identifiers:
- **`phyloname`**: `Kingdom_Phylum_Class_Order_Family_Genus_species`
- **`phyloname_taxonid`**: Same but with `___taxonID` appended

### Workflow Templates

Each subproject contains workflow templates (`nf_workflow-TEMPLATE_*/`):
1. Copy the template to create a run
2. Edit configuration files
3. Run with `bash RUN_*.sh`

### Manifest Files

User inputs are specified in TSV manifest files in `INPUT_user/` directories.

---

## Common User Questions

### "Where do I start?"

Start with `subprojects/phylonames/`. This generates the species mappings that all other subprojects need.

### "What order do I run things?"

Depends on your research question. The dependency chain is:
```
phylonames → genomesDB → trees_species → orthogroups → OCL
                      ↘ annotations_hmms ↗
```

But you can run subprojects in different orders based on your needs.

### "Something failed - what do I do?"

1. Check the log files in `research_notebook/research_ai/subproject-[name]/logs/`
2. Read the error message carefully
3. Consult the subproject's `AI_GUIDE-[subproject].md` troubleshooting section
4. Ask your AI assistant for help - that's what they're for!

---

## Three Advantages of GIGANTIC

1. **Democratized access**: AI assistants guide non-experts through complex pipelines

2. **Genome-scale throughput**: Local HPC enables analysis of tens to hundreds of species - beyond what web services can provide

3. **Modular flexibility**: Run analyses in the order that makes sense for your evolving research questions

---

## For AI Assistants: How to Help

When a user asks for help:

1. **Identify which subproject** they're working on
2. **Read that subproject's AI_GUIDE-[subproject].md** for specific guidance
3. **Check their configuration** (manifests, YAML files)
4. **Look at log files** if something failed
5. **Guide them step by step** - don't assume expertise

Remember: Users may not be bioinformatics experts. Explain clearly, suggest specific commands, and help them understand what's happening.
