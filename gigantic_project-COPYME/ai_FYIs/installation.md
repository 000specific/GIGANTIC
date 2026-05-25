# Installation Guide

This guide covers software dependencies and environment setup for GIGANTIC.

---

## System Requirements

- **Operating System**: Linux (tested on CentOS/RHEL, Ubuntu)
- **Memory**: 16 GB minimum, 64 GB recommended for large datasets
- **Storage**: Varies by dataset size; demo requires ~1 GB

## Core Dependencies

| Software | Version | Purpose |
|----------|---------|---------|
| NextFlow | >= 21.04 | Workflow orchestration |
| Python | >= 3.8 | Pipeline scripts |
| Conda/Mamba | Latest | Environment management |

## Bioinformatics Tools

These are installed via conda environments:

| Tool | Purpose |
|------|---------|
| BLAST+ | Sequence similarity search |
| MAFFT | Multiple sequence alignment |
| FastTree | Fast phylogenetic inference |
| IQ-TREE | Maximum likelihood phylogenetics |
| ClipKit | Alignment trimming |
| InterProScan | Functional annotation |
| OrthoFinder | Ortholog identification |
| OrthoHMM | HMM-based ortholog clustering |

## Installing Conda Environments

From the GIGANTIC root directory:

```bash
bash environments/install_environments.sh
```

This creates the following environments:

- `gigantic_base` - Core Python dependencies
- `gigantic_phylogenetics` - Tree building tools
- `gigantic_annotations` - Annotation tools
- `gigantic_orthogroups` - Ortholog identification tools

## Manual Installation

If you prefer manual installation, see the environment YAML files in `environments/`:

```bash
conda env create -f environments/gigantic_base.yml
conda env create -f environments/gigantic_phylogenetics.yml
# etc.
```

## HPC/SLURM Configuration

For HPC systems, edit `nextflow.config` in each subproject template to match your cluster:

```groovy
process {
    executor = 'slurm'
    queue = 'your_partition'
    // Adjust resources as needed
}
```

## Verifying Installation

Run the demo to verify everything is working:

```bash
cd demo
bash run_demo.sh
```

---

*Documentation under development. Check back for updates.*
