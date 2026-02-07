<p align="center">
  <img src="assets/branding/logo-wordmark-black.png" alt="GIGANTIC" width="100%">
</p>

<p align="center">
  <strong>GIGANTIC: Genome Integration and Gene Analysis across Numerous Topology-Interrogated Clades</strong>
</p>

<p align="center">
  A modular phylogenomics platform for comparative genomics and evolutionary analysis.
</p>

<p align="center">
  <em>AI-native phylogenomics - for experts and everyone!</em>
</p>

---

GIGANTIC provides a template-based framework of NextFlow workflows and Python pipelines for large-scale comparative genomics. Each subproject handles a distinct analysis stage - from proteome database curation to phylogenetic tree construction to evolutionary origin-conservation-loss analysis - connected through standardized data sharing conventions.

---

## Key Features

- **Exhaustive topology analysis**: Generate and analyze all mathematically possible species tree topologies for your focal clades, ensuring findings are robust to phylogenetic uncertainty
- **Origin-Conservation-Loss (OCL) framework**: Track gene family evolutionary dynamics across every possible tree topology
- **Modular subprojects**: Use individual pipelines independently or as an integrated framework
- **Manifest-driven workflows**: Reproducible NextFlow pipelines configured through simple TSV manifests
- **Standardized phylogenetic naming**: The GIGANTIC phyloname system provides consistent, hierarchical species identifiers across all analyses
- **Self-documenting outputs**: Table headers embed calculation methods and data descriptions

## Architecture

GIGANTIC is organized as a series of subprojects that build on each other:

```
[1] genomesDB                Proteome database curation and BLAST setup
       |
[2] phylonames               Phylogenetic naming system (genus_species <-> full taxonomy)
       |
       +---------------------------+--------------------------+
       |                           |                          |
[3] annotations_hmms      [4] orthogroups          [6] trees_gene_families
    Functional annotation      Ortholog group             Gene family
    (InterProScan, DeepLoc,    identification             phylogenetics
     SignalP, tmbed,           (OrthoHMM,                 (BLAST, MAFFT,
     MetaPredict)               OrthoFinder)               FastTree, IQ-TREE)
       |                           |
       |                    [5] trees_species
       |                        All possible species
       |                        tree topologies
       |                           |
       |                    [7] orthogroups_X_ocl
       |                        Gene origin, conservation,
       |                        and loss analysis (OCL)
       |                           |
       +---------------------------+
                       |
              [8] annotations_X_ocl
                  Integration of functional
                  annotations with evolutionary
                  dynamics
```

Each subproject is self-contained with its own NextFlow workflows, Python scripts, documentation, and standardized input/output directories.

## Subprojects

| # | Subproject | Description | Type |
|---|-----------|-------------|------|
| 1 | `genomesDB` | Proteome database curation, BLAST database construction | Setup |
| 2 | `phylonames` | GIGANTIC phylogenetic naming system and species mapping | Setup |
| 3 | `annotations_hmms` | Multi-tool protein functional annotation pipeline | NextFlow |
| 4 | `orthogroups` | Ortholog group identification (OrthoHMM + OrthoFinder) | NextFlow |
| 5 | `trees_species` | Exhaustive species tree topology generation | NextFlow |
| 6 | `trees_gene_families` | Gene family phylogenetic analysis | NextFlow |
| 7 | `orthogroups_X_ocl` | Evolutionary dynamics across all tree topologies | NextFlow |
| 8 | `annotations_X_ocl` | Functional annotation integrated with OCL analysis | NextFlow |
| 9 | `synteny` | Gene order conservation analysis across species | NextFlow |
| 10 | `dark_proteome` | Uncharacterized/unknown function protein analysis | NextFlow |
| 11 | `hot_spots` | Evolutionary hotspots and rapid change regions | NextFlow |
| 12 | `rnaseq_integration` | RNA-seq expression data integration | NextFlow |
| 13 | `hgnc_automation` | Automated reference gene family gene set generation | NextFlow |
| 14 | `gene_names` | Comprehensive gene naming system | NextFlow |
| 15 | `one_direction_homologs` | One-way BLAST homolog identification | NextFlow |

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/000specific/GIGANTIC.git
```

### 2. Copy the project template to your working location

```bash
cp -r GIGANTIC/gigantic_project-COPYME ~/my_projects/gigantic_project-cephalopod_evolution/
cd ~/my_projects/gigantic_project-cephalopod_evolution/
```

**Project naming convention**: `gigantic_project-your_project_name`

Examples:
- `gigantic_project-cephalopod_evolution`
- `gigantic_project-early_animal_phylogenomics`
- `gigantic_project-mollusc_neural_genes`

### 3. Work within your copied project

Your copied project is completely self-contained. Read `AI_GUIDE-project.md` to get started - we recommend working with an AI assistant (Claude, ChatGPT, etc.) who can read this guide and help you through the workflows.

```
gigantic_project-your_project_name/
├── AI_GUIDE-project.md                # Start here - high-level project guidance
├── research_notebook/                 # Your research documentation
│   ├── research_user/                 # Your personal workspace (notes, literature, drafts)
│   └── research_ai/                   # AI session documentation (logs, validation)
└── subprojects/                       # GIGANTIC analysis modules
    ├── phylonames/                    # [1] Start here - species naming system
    ├── genomesDB/                     # [2] Proteome database setup
    └── ...                            # Additional subprojects
```

### 4. Run the demo (optional)

```bash
cd GIGANTIC/demo
bash run_demo.sh
```

The demo uses a small 3-species dataset (*Homo sapiens*, *Aplysia californica*, *Octopus bimaculoides*) to walk through the complete GIGANTIC pipeline.

## Subproject Workspace Structure

Each subproject follows a standard GIGANTIC workspace layout:

```
subproject/
├── user_research/                     # Personal workspace for notes and exploration
├── nf_workflow-TEMPLATE_01/           # NextFlow workflow template
│   ├── RUN_workflow.sh                # Local execution: bash RUN_workflow.sh
│   ├── RUN_workflow.sbatch            # SLURM execution: sbatch RUN_workflow.sbatch
│   ├── config.yaml                    # User configuration (edit this)
│   ├── main.nf                        # NextFlow pipeline (don't edit)
│   ├── nextflow.config                # NextFlow settings (don't edit)
│   ├── ai_scripts/                    # Python/Bash pipeline scripts
│   ├── INPUT_user/                    # User-provided inputs
│   └── OUTPUT_pipeline/               # Workflow outputs
├── output_to_input/                   # Outputs shared to downstream subprojects
└── upload_to_server/                  # Curated outputs for external access
```

## The Phyloname System

GIGANTIC uses hierarchical phylogenetic names for consistent species identification:

```
Kingdom_Phylum_Class_Order_Family_Genus_species
```

Example:
```
Metazoa_Mollusca_Cephalopoda_Octopoda_Octopodidae_Octopus_bimaculoides
```

This enables programmatic extraction of any taxonomic level and ensures consistent naming across all subprojects and analyses.

---

## AI-Native Development

**GIGANTIC is developed using AI pair programming and is designed to be run with AI assistance.**

### Development

GIGANTIC represents an ongoing transformation from **GIGANTIC_0** (a decade of human-written "crayon code" - functional but scattered, undocumented scripts) to **GIGANTIC_1** (modernized, documented, reproducible pipelines).

This transformation is being done through AI pair programming using:
- **Claude Code** within **Cursor IDE**
- **Claude Opus 4.5** (as of February 2026)
- Human collaborator: **Eric Edsinger**

Every script includes an AI attribution header documenting the model, date, and purpose.

### Usage

**We recommend using an AI assistant (Claude, ChatGPT, or similar) to help run GIGANTIC workflows.**

Each subproject and workflow template includes an `AI_GUIDE-[name].md` file specifically written to help AI assistants:
- Understand what the workflow does
- Guide users through configuration
- Troubleshoot common errors
- Interpret outputs

### Why AI + Local HPC?

This approach offers three transformative advantages:

1. **Democratized access**: You don't need to be a bioinformatics expert to run complex phylogenomics pipelines. An AI assistant can guide you through configuration, troubleshoot errors, and interpret results.

2. **Genome-scale throughput**: Unlike web-based phylogenetic tools, GIGANTIC runs on your local computing cluster (HPC), enabling analysis of **tens to hundreds of species** with full proteomes. Web services simply cannot provide this scale of comparative genomics analysis.

3. **Modular flexibility**: Different projects have different targets and develop in different sequences as new insights and questions emerge. GIGANTIC's modular subproject architecture lets you run analyses in the order that makes sense for your research, not a fixed pipeline order.

Together, AI assistance + local HPC computing + modular design makes sophisticated phylogenomics accessible to researchers who have cluster access but lack deep bioinformatics expertise.

### Design Philosophy

GIGANTIC explores what research software looks like when AI assistance is assumed rather than optional. This shapes several design choices:

- **AI_GUIDE files**: Each subproject and workflow includes documentation written specifically for AI assistants to read - structured to help them help you
- **Research notebook separation**: `research_user/` (your notes, your way) vs `research_ai/` (structured AI session records) - because AI-assisted work is research too
- **Context-aware naming**: Files like `AI_GUIDE-phylonames.md` let you direct your AI assistant to exactly the right documentation
- **Per-subproject environments**: Each subproject contains its own `conda_environment-[subproject].yml` file - everything you need is right there in the subproject. The AI immediately sees it when examining the directory. No hunting through centralized folders.

**Why this differs from traditional software design**: Traditional CS would centralize environments to avoid duplication. But that creates a disconnect between "where I'm working" and "what I need to work." For AI-assisted workflows, **discoverability > avoiding minor duplication**. Each subproject is an autonomous modular unit containing everything needed to run it.

This is new territory. Users are not CS experts, and AI-user research workflows are inventing conventions as they go. We're learning what works. If you find patterns that work well (or don't), we'd love to hear about it.

### Running Workflows

Every workflow template has two RUN files - the file extension tells you how to run it:

```
nf_workflow-TEMPLATE_01/
├── RUN_phylonames.sh      ← bash RUN_phylonames.sh      (local machine)
├── RUN_phylonames.sbatch  ← sbatch RUN_phylonames.sbatch (SLURM cluster)
└── ...
```

| File | Command | Where it runs |
|------|---------|---------------|
| `RUN_*.sh` | `bash RUN_*.sh` | Your local machine |
| `RUN_*.sbatch` | `sbatch RUN_*.sbatch` | SLURM cluster |

**That's it.** Scan the directory, see two RUN files, pick the one for your environment.

### NextFlow Execution Patterns (Internal Detail)

Internally, workflows use one of two patterns based on computational needs:

**Pattern A: Sequential** - All processes run in one job (e.g., `phylonames` ~15 mins)
**Pattern B: Parallel** - NextFlow submits separate SLURM jobs (e.g., `annotations_hmms` with many proteomes)

You don't need to know which pattern a workflow uses - just run `RUN_*.sh` or `RUN_*.sbatch`.

### Configuration Files for Reproducibility

Every workflow has a human-readable `config.yaml` that users edit:

```yaml
project:
  name: "my_project"
  species_list: "INPUT_user/species_list.txt"
```

**Users edit `config.yaml`, NOT NextFlow files.** This ensures:
- **Reproducibility**: Config stays with the workflow - exact record of how things ran
- **Transparency**: Human-readable YAML with detailed comments
- **Accessibility**: Non-CS users can understand and modify settings

---

## Requirements

- **NextFlow** >= 21.04
- **Python** >= 3.8
- **Conda/Mamba** for environment management
- **SLURM** (optional, for HPC execution)

Key bioinformatics tools (installed via conda environments):
- BLAST+ (sequence similarity search)
- MAFFT (multiple sequence alignment)
- FastTree / IQ-TREE (phylogenetic inference)
- ClipKit (alignment trimming)
- InterProScan (functional annotation)
- OrthoFinder / OrthoHMM (ortholog identification)

## Documentation

- [Getting Started](docs/getting_started.md) - Full setup walkthrough
- [Installation Guide](docs/installation.md) - Software dependencies and environments
- [Architecture Overview](docs/overview.md) - How subprojects connect
- [Phyloname System](docs/phylonames_system.md) - The GIGANTIC naming convention
- [Conventions](docs/conventions.md) - Coding style and file format standards
- [Tutorials](docs/tutorials/) - Step-by-step guides for each subproject

## Citation

If you use GIGANTIC in your research, please cite:

> Edsinger, E. (2026). GIGANTIC: Genome Integration and Gene Analysis across Numerous Topology-Interrogated Clades. GitHub repository: https://github.com/000specific/GIGANTIC

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome. Please see our [contribution guidelines](docs/contributing.md) for details.
