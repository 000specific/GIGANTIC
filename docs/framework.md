# The GIGANTIC Framework

A comprehensive guide to GIGANTIC's architecture, design patterns, and data flow conventions.

---

## What GIGANTIC Is

**GIGANTIC** (Genome Integration and Gene Analysis across Numerous Topology-Interrogated Clades) is a modular phylogenomics platform for comparative genomics and evolutionary analysis. It provides interconnected Nextflow workflows and Python pipelines spanning the complete comparative genomics workflow: from proteome database curation and phylogenetic naming through ortholog identification, gene family tree construction, and evolutionary dynamics analysis.

### Template-Based Design

GIGANTIC is a template you copy and customize:

```bash
# Clone the repository
git clone https://github.com/000specific/GIGANTIC.git

# Copy the template for your project
cp -r GIGANTIC/gigantic_project-COPYME ~/gigantic_project-cephalopod_evolution/

# Everything you need is inside
cd ~/gigantic_project-cephalopod_evolution/
```

Each copied project is completely self-contained: all workflows, configuration, documentation, and data sharing infrastructure. Multiple independent projects can be created from the same template, each targeting different species sets or research questions.

### AI-Native Design

GIGANTIC is developed through human-AI pair programming and is designed to be operated with AI assistance. The framework includes structured documentation (AI_GUIDE files) written specifically for AI assistants at every level of the project hierarchy. This enables researchers to configure, execute, troubleshoot, and interpret complex phylogenomic workflows through natural language interaction with an AI assistant on their local computing infrastructure.

You don't need to be a bioinformatics expert to run GIGANTIC. An AI assistant reading the AI_GUIDE files can walk you through everything.

---

## The Phyloname System

A central design principle: the full taxonomic lineage of every organism is encoded directly into every sequence identifier, file name, and results table through the GIGANTIC phyloname system.

```
Kingdom_Phylum_Class_Order_Family_Genus_species
```

**Example:**
```
Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens
```

This means that when you open any FASTA file, BLAST result, phylogenetic tree, or summary table, you can immediately recognize the kingdom, phylum, class, order, family, genus, and species of every sequence - without consulting external databases or lookup tables. When you visually inspect a gene family tree or scan a table of ortholog group members, the taxonomic context of every entry is self-evident, enabling rapid biological interpretation.

Computationally, phylonames enable straightforward parsing, filtering, and grouping of all data by any taxonomic level using simple string operations:

```python
# Extract genus_species from any phyloname
parts = phyloname.split('_')
genus_species = parts[5] + '_' + '_'.join(parts[6:])

# Group sequences by phylum
phylum = phyloname.split('_')[1]  # e.g., "Chordata", "Arthropoda"
```

See [The Phyloname System](phylonames_system.md) for full details.

---

## Framework Architecture

### Modular Subproject System

GIGANTIC organizes analyses into independent subprojects, each handling a distinct stage of the comparative genomics workflow. Subprojects are connected through standardized data sharing conventions but can also be used independently.

**Core subproject dependency chain:**

```
phylonames                    Species identifier generation (NCBI taxonomy)
    |                         MUST RUN FIRST
    v
genomesDB                     Proteome database curation and BLAST setup
    |                         MUST RUN SECOND
    |
    +--- orthogroups          Ortholog group identification
    |                         (OrthoFinder, OrthoHMM, Broccoli)
    |
    +--- trees_gene_families  Gene family homolog discovery and phylogenetics
    |                         (BLAST, MAFFT, FastTree, IQ-TREE)
    |
    +--- trees_gene_groups    Orthogroup-based phylogenetic analysis
    |
    +--- one_direction_homologs   One-direction DIAMOND homolog identification
    |                             (searches against NCBI nr)
    |
    +--- [additional subprojects connect here as they are developed]
```

The phylonames and genomesDB subprojects are prerequisites for everything else. Beyond those two, analytical subprojects can be executed in any order - you choose what to run based on your research questions.

### STEP and BLOCK Patterns

Within each subproject, workflows are organized using one of two patterns:

#### STEP Pattern (Sequential)

Used when analyses form a linear pipeline where each stage depends on the previous stage's output. Steps are numbered and must run in order.

```
genomesDB/
├── STEP_1-sources/               # Ingest user-provided data
│   └── workflow-COPYME-.../
├── STEP_2-standardize_evaluate/  # Rename, validate, quality-check
│   └── workflow-COPYME-.../
├── STEP_3-databases/             # Build BLAST databases
│   └── workflow-COPYME-.../
└── STEP_4-create_final_species/  # Curate final species set
    └── workflow-COPYME-.../
```

**STEP_1 output feeds STEP_2, which feeds STEP_3, which feeds STEP_4.**

Subprojects using STEPs: **genomesDB** (4 steps), **trees_gene_families** (3 steps), **trees_gene_groups** (3 steps)

#### BLOCK Pattern (Standalone, Parallel)

Used when multiple independent analyses operate on the same input and can run in any order or in parallel.

```
orthogroups/
├── BLOCK_orthofinder/            # OrthoFinder analysis
│   └── workflow-COPYME-.../
├── BLOCK_orthohmm/               # OrthoHMM analysis
│   └── workflow-COPYME-.../
├── BLOCK_broccoli/               # Broccoli analysis
│   └── workflow-COPYME-.../
└── BLOCK_comparison/             # Compare all three methods
    └── workflow-COPYME-.../
```

**Each BLOCK runs independently. BLOCK_comparison runs after the tool blocks are done.**

Subprojects using BLOCKs: **orthogroups** (4 blocks), **one_direction_homologs** (1 block)

#### Consistent Internal Structure

Both STEPs and BLOCKs share the same internal layout:

```
STEP_N-name/ (or BLOCK_name/)
├── AI_GUIDE-name.md              # AI documentation for this step/block
├── RUN-clean_and_record_subproject.sh
├── output_to_input/              # Outputs for downstream consumption
└── workflow-COPYME-name/         # The workflow template
    ├── RUN-workflow.sh           # bash RUN-workflow.sh
    ├── RUN-workflow.sbatch       # sbatch RUN-workflow.sbatch
    ├── name_config.yaml          # User configuration
    ├── INPUT_user/               # Workflow inputs
    ├── OUTPUT_pipeline/          # Workflow results
    └── ai/                       # Internal (scripts, Nextflow pipeline)
```

You learn this structure once and can navigate any subproject.

---

## Data Flow

### Project-Wide Inputs: `INPUT_gigantic/`

```
INPUT_gigantic/species_list.txt     # Edit HERE - single source of truth
        |
        v (copied by RUN script at runtime)
workflow-*/INPUT_user/species_list.txt  # Archived copy for this specific run
```

**Why:** One place to edit your species list, but each workflow run gets its own archived copy. You can update the master list without affecting previously completed runs.

### Inter-Subproject Sharing: `output_to_input/`

```
genomesDB/output_to_input/
├── proteomes/                    # Standardized proteome files
└── blast_databases/              # Per-species BLAST databases
        |
        v (downstream subprojects read from here)
orthogroups/BLOCK_orthofinder/workflow-COPYME-.../INPUT_user/
```

Each subproject (and each STEP/BLOCK) publishes its outputs as symlinks in `output_to_input/`. Downstream subprojects reference these directories as input. This creates an explicit, traceable dependency chain.

### Server Sharing: `upload_to_server/`

```
upload_to_server/
├── upload_manifest.tsv           # User controls what gets shared
└── [symlinks]                    # Created by RUN-update_upload_to_server.sh
```

For curated data intended for a centralized GIGANTIC server or collaborator access.

### Workflow Template System: COPYME/RUN

```
workflow-COPYME-generate_phylonames/    # Template (keep clean, never run in here)
workflow-RUN_01-generate_phylonames/    # First run (copy of template)
workflow-RUN_02-generate_phylonames/    # Second run (another copy)
```

**To create a new run:**
```bash
cp -r workflow-COPYME-generate_phylonames workflow-RUN_01-generate_phylonames
cd workflow-RUN_01-generate_phylonames
# Edit config, add inputs, then run
bash RUN-workflow.sh
```

Each RUN directory preserves its own inputs, outputs, and configuration as a complete record.

---

## Workflow Execution

### Running Workflows

Every workflow has exactly two execution scripts:

| File | Command | When to Use |
|------|---------|-------------|
| `RUN-workflow.sh` | `bash RUN-workflow.sh` | Local machine or workstation |
| `RUN-workflow.sbatch` | `sbatch RUN-workflow.sbatch` | SLURM HPC cluster |

The SBATCH file is a thin wrapper (~40 lines) containing only SLURM resource directives that calls `RUN-workflow.sh`. This keeps cluster-specific settings separate from workflow logic.

### Configuration

Each workflow has a single human-readable YAML config file:

```yaml
# phylonames_config.yaml
project:
  name: "my_cephalopod_project"       # Your project name
  species_list: "INPUT_user/species_list.txt"

phylonames:
  mark_unofficial: true                # Mark user-provided clades as UNOFFICIAL
```

**Edit this file, not the Nextflow pipeline.** The config is preserved alongside your results for complete reproducibility.

### Environment Management

All conda environments are defined centrally and set up once:

```bash
# One-time setup (creates all environments)
bash RUN-setup_environments.sh
```

Environment files: `conda_environments/ai_gigantic_[subproject].yml`

RUN scripts activate the correct environment automatically - you don't need to manage this manually.

### Error Handling: Fail Fast

GIGANTIC uses strict fail-fast error handling:

- **Nextflow level:** `errorStrategy = 'terminate'`, `maxErrors = 0` - pipeline stops on first failure
- **Script level:** Every Python script validates inputs and exits with detailed error messages if data is missing

**Philosophy:** In scientific pipelines, completing with invalid data is worse than failing. Errors are caught immediately, not discovered hours later in downstream results.

---

## AI_GUIDE Documentation Hierarchy

GIGANTIC includes a three-level documentation system written for AI assistants:

| Level | File | Scope | When to Read |
|-------|------|-------|-------------|
| **1. Project** | `AI_GUIDE-project.md` | Entire project | First time working with GIGANTIC |
| **2. Subproject** | `AI_GUIDE-[name].md` | One subproject | Working in a specific subproject |
| **3. Workflow** | `ai/AI_GUIDE-*_workflow.md` | One workflow | Executing or troubleshooting a workflow |

Each level references the level above to avoid duplication. Lower levels provide increasingly specific guidance:

- **Level 1:** "Here's how GIGANTIC works, here's the subproject dependency chain"
- **Level 2:** "Here's what orthogroups does, here's a troubleshooting table for common errors"
- **Level 3:** "Here's how to run this specific workflow step by step"

**To get AI help:** Point your AI assistant to the appropriate AI_GUIDE file. It contains everything the AI needs to help you.

---

## AI Attribution and Transparency

Every AI-generated script includes an attribution header:

```python
# AI: Claude Code | Opus 4.6 | 2026 March 01 | Purpose: Validate proteome files and manifest
# Human: Eric Edsinger
```

Script filenames include an `ai` prefix to clearly identify AI-generated code:

```
001_ai-python-validate_proteomes.py
002_ai-python-split_proteomes_for_diamond.py
003_ai-bash-run_diamond_search.sh
```

---

## Session Provenance Recording

GIGANTIC treats AI development sessions as research artifacts. Automated scripts extract AI coding session histories into human-readable markdown:

```bash
# Record all sessions (project + all subprojects)
bash RUN-record_project.sh

# Subproject cleanup with session recording
bash RUN-clean_and_record_subproject.sh --all
```

**Output:**
```
research_notebook/research_ai/
├── project/sessions/
│   ├── session_2026february12_abc123.md
│   └── SESSION_EXTRACTION_LOG.md
└── subproject-phylonames/sessions/
    └── ...
```

**Why this matters:**
- **Reproducibility:** Others can understand how AI contributed to the work
- **Transparency:** AI assistance is documented, not hidden
- **Lab notebook culture:** Treats AI sessions like traditional research records
- **Compliance:** Meets emerging journal and funding agency AI disclosure requirements

---

## Research Notebook

Each project includes a research notebook with two sections:

```
research_notebook/
├── research_user/     # YOUR space - organize however you want
│   ├── notes/         #   Personal documentation
│   ├── literature/    #   Papers and references
│   └── [anything]     #   Complete freedom
│
└── research_ai/       # AI documentation - structured
    ├── project/sessions/           # AI session records
    └── subproject-[name]/sessions/ # Per-subproject AI docs
```

Your personal workspace has no rules. AI documentation is systematically recorded.

---

## Output Conventions

### Self-Documenting Table Headers

All output tables use headers that explain themselves:

```
Orthogroup_ID (orthogroup identifier)    Species_Count (number of species in orthogroup)    Gene_Count (total genes across all species)
OG0000001    45    312
OG0000002    67    67
```

The parenthetical descriptions embed calculation methods and data formats directly in the column name, so every table is interpretable without external documentation.

### Delimiter Convention

- **Between columns:** Tabs (`\t`)
- **Within columns (multiple values):** Commas (`,`)

```
Species_List (comma delimited list)
Homo_sapiens,Mus_musculus,Drosophila_melanogaster
```

---

## Implementation Summary

| Component | Technology |
|-----------|-----------|
| Pipeline orchestration | Nextflow DSL2 |
| Processing scripts | Python 3 (standard library), Bash |
| Environment management | Conda/Mamba |
| HPC support | SLURM (thin SBATCH wrappers) |
| Configuration | YAML |
| Data format | TSV with self-documenting headers |

**Python scripts use only standard library dependencies** except where bioinformatics tools are required (BLAST+, MAFFT, DIAMOND, etc.). All tool dependencies are managed through conda environments with pinned versions.

---

## Quick Reference

| Question | Answer |
|----------|--------|
| Where do I start? | `subprojects/phylonames/` - run this first |
| Where's my species list? | `INPUT_gigantic/species_list.txt` |
| How do I run a workflow? | `bash RUN-workflow.sh` (local) or `sbatch RUN-workflow.sbatch` (SLURM) |
| Where are my results? | `OUTPUT_pipeline/` in the workflow directory |
| How do subprojects share data? | Via `output_to_input/` symlinks |
| How do I create a new run? | `cp -r workflow-COPYME-name workflow-RUN_01-name` |
| Where's the AI documentation? | `AI_GUIDE-*.md` files at each level |
| How do I record AI sessions? | `bash RUN-record_project.sh` |
