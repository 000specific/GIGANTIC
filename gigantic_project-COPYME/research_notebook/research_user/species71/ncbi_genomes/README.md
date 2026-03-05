# NCBI Genomes - Species69 Database Acquisition

## Overview

This subproject downloads genome assemblies, GFF3 annotations, and protein sequences
from NCBI for 34 species using the NCBI datasets CLI, then extracts T1 (longest
transcript per gene) proteomes for use in downstream GIGANTIC pipelines.

## Species

34 species across major animal and outgroup lineages (31 RefSeq/GCF + 3 GenBank/GCA):

- **Porifera**: Oscarella lobularis, Corticium candelabrum, Halichondria panicea, Dysidea avara, Sycon ciliatum
- **Ctenophora**: Bolinopsis microptera
- **Placozoa**: Trichoplax adhaerens, Trichoplax sp. H2
- **Cnidaria**: Hydra vulgaris, Hydractinia symbiolongicarpus, Nematostella vectensis, Acropora muricata, Pocillopora verrucosa
- **Xenacoelomorpha**: Symsagittifera roscoffensis
- **Orthonectida**: Intoshia linei
- **Mollusca**: Aplysia californica, Octopus bimaculoides, Crassostrea virginica, Pomacea canaliculata, Liolophura japonica, Haliotis asinina, Patella vulgata, Biomphalaria glabrata
- **Arthropoda**: Drosophila melanogaster
- **Nematoda**: Caenorhabditis elegans
- **Nemertea**: Lineus longissimus
- **Priapulida**: Priapulus caudatus
- **Nematomorpha**: Gordionus sp. m RMFG-2023
- **Rotifera**: Adineta vaga
- **Echinodermata**: Lytechinus variegatus
- **Chordata**: Homo sapiens, Branchiostoma lanceolatum
- **Choanoflagellata**: Monosiga brevicollis MX1
- **Holomycota**: Fonticula alba

## Directory Structure

```
ncbi_genomes/
├── nf_workflow-COPYME_01-ncbi_genomes/   # Workflow template (copy to RUN_N before running)
│   ├── INPUT_user/
│   │   └── ncbi_genomes_manifest.tsv     # Species + NCBI accession manifest
│   ├── OUTPUT_pipeline/                  # Pipeline outputs (populated after run)
│   │   ├── 1-output/downloads/           # Raw zip files from NCBI
│   │   ├── 2-output/                     # Unzipped + renamed files
│   │   │   ├── genome/                   # Genus_species-ncbi_genomes.fasta
│   │   │   ├── gff3/                     # Genus_species-ncbi_genomes.gff3
│   │   │   └── protein/                  # Genus_species-ncbi_genomes.faa
│   │   ├── 3-output/T1_proteomes/        # T1 proteomes (.aa)
│   │   └── 4-output/                     # Symlinks manifest
│   ├── ai/                               # Pipeline scripts and NextFlow definition
│   ├── RUN_ncbi_genomes.sh               # Local execution
│   ├── RUN_ncbi_genomes.sbatch           # SLURM execution
│   ├── ncbi_genomes_config.yaml          # User-editable configuration
│   └── README.md                         # Workflow documentation
├── output_to_input/                      # Downstream access point
│   └── T1_proteomes/                     # Symlinks to T1 proteomes
├── user_research/                        # Personal workspace
└── README.md                             # This file
```

## Quick Start

```bash
# 1. Copy the template to a run directory
cp -r nf_workflow-COPYME_01-ncbi_genomes nf_workflow-RUN_1_01-ncbi_genomes

# 2. Enter the run directory
cd nf_workflow-RUN_1_01-ncbi_genomes

# 3. Run locally
bash RUN_ncbi_genomes.sh

# 4. Or submit to SLURM
sbatch RUN_ncbi_genomes.sbatch
```

## Downstream Access

T1 proteomes are available via symlinks at:
```
ncbi_genomes/output_to_input/T1_proteomes/
```

## Source Data

- **Input table**: Table X2 - GIGANTIC Aplysia Genome Project - SequencesDB 2024
- **Download method**: NCBI datasets CLI v16.31.0
- **Data types**: genome (.fasta), GFF3 annotation (.gff3), protein sequences (.faa)
