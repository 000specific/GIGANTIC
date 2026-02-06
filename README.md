<p align="center">
  <img src="assets/branding/logo-wordmark-black.png" alt="GIGANTIC" width="600">
</p>

<p align="center">
  <strong>Genome Integration and Gene Analysis across Numerous Topology-Interrogated Clades</strong>
</p>

<p align="center">
  A modular phylogenomics platform for comparative genomics and evolutionary analysis.
</p>

<p align="center">
  <em>Developed with AI assistance. Designed for AI-assisted usage.</em>
</p>

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

Each subproject and workflow template includes an `AI_GUIDE.md` file specifically written to help AI assistants:
- Understand what the workflow does
- Guide users through configuration
- Troubleshoot common errors
- Interpret outputs

This approach democratizes access to complex phylogenomics pipelines - you don't need to be a bioinformatics expert if you have an AI assistant to help.

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

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/000specific/GIGANTIC.git
cd GIGANTIC
```

### 2. Set up conda environments

```bash
bash environments/install_environments.sh
```

### 3. Run the demo

```bash
cd demo
bash run_demo.sh
```

The demo uses a small 3-species dataset (*Homo sapiens*, *Aplysia californica*, *Octopus bimaculoides*) to walk through the complete GIGANTIC pipeline.

### 4. Start your own project

```bash
bash scripts/setup_gigantic_project.sh my_project_name
```

This creates a new project directory with all subproject templates ready to customize for your species set.

## Subproject Workspace Structure

Each subproject follows a standard GIGANTIC workspace layout:

```
subproject/
├── 000_user/                          # Personal workspace for notes and exploration
├── nf_workflow-TEMPLATE_01/           # NextFlow workflow template
│   ├── ai_scripts/                    # Python/Bash pipeline scripts
│   ├── INPUT_user/                    # User-provided inputs (manifests, FASTAs)
│   ├── OUTPUT_pipeline/               # Workflow outputs
│   ├── OUTPUT_to_input/               # Outputs archived with this run
│   ├── pipeline.nf                    # NextFlow pipeline definition
│   ├── config.yaml                    # Pipeline configuration
│   └── nextflow.config                # NextFlow execution settings
├── output_to_input/                   # Outputs shared to downstream subprojects
├── upload_to_server/                  # Curated outputs for external access
└── gigantic_ai/                       # AI documentation and validation
    └── ai_documentation/
        ├── documentation/             # Session logs
        ├── validation/                # QC scripts
        └── logs/                      # Execution logs
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
