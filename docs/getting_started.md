# Getting Started with GIGANTIC

**Genome Integration and Gene Analysis across Numerous Topology-Interrogated Clades**

This guide will walk you through setting up your first GIGANTIC project.

---

## Prerequisites

Before starting, ensure you have:

- **Git** for cloning the repository
- **Conda or Mamba** for environment management
- **NextFlow** >= 21.04 for running workflows
- **Python** >= 3.8

## Step 1: Clone the Repository

```bash
git clone https://github.com/000specific/GIGANTIC.git
cd GIGANTIC
```

## Step 2: Install Conda Environments

```bash
bash environments/install_environments.sh
```

This will create the necessary conda environments for all GIGANTIC tools.

## Step 3: Run the Demo

Test your installation with the demo dataset:

```bash
cd demo
bash run_demo.sh
```

The demo uses 3 species (*Homo sapiens*, *Aplysia californica*, *Octopus bimaculoides*) and runs through the complete pipeline.

## Step 4: Set Up Your Own Project

Create a new GIGANTIC project:

```bash
bash scripts/setup_gigantic_project.sh my_project_name
```

This creates a project directory with all subproject templates ready to customize.

## Step 5: Add Your Species

1. Place your proteome FASTA files in `genomesDB/000_user/`
2. Create a species manifest in `genomesDB/workflow-COPYME/INPUT_user/`
3. Generate phylonames for your species using the `phylonames/` subproject

## Next Steps

- Read the [Installation Guide](installation.md) for detailed software requirements
- Review the [Architecture Overview](overview.md) to understand how subprojects connect
- Check the [Tutorials](tutorials/) for step-by-step guides for each subproject

---

*Documentation under development. Check back for updates.*
