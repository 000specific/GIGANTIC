# genomesDB - GIGANTIC Genome Database System

**AI**: Claude Code | Opus 4.5 | 2026 February 12
**Human**: Eric Edsinger

**Status**: The active genomesDB. Build outputs live in `workflow-RUN_1` of each STEP.

---

## Purpose

The genomesDB subproject manages genome and proteome data for GIGANTIC projects. It provides a standardized pipeline for collecting, evaluating, and building genome databases from multiple sources.

**This subproject runs early** - most other GIGANTIC subprojects depend on the genome databases produced here.

---

## GIGANTIC Source Data Naming Conventions

### Source Manifest Format

The source manifest is a TSV file with four columns:

```
genus_species	path/to/genome	path/to/gtf	path/to/proteome
```

**Example** (using relative paths to project-level INPUT_user):
```tsv
genus_species	genome_path	genome_annotation_path	proteome_path
Homo_sapiens	../../../../INPUT_user/genomic_resources/genomes/Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.fasta	../../../../INPUT_user/genomic_resources/annotations/Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.gff3	../../../../INPUT_user/genomic_resources/proteomes/Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.aa
Mus_musculus	../../../../INPUT_user/genomic_resources/genomes/Mus_musculus-genome_ncbi_GCF_000001635.27-downloaded_20240115.fasta	../../../../INPUT_user/genomic_resources/annotations/Mus_musculus-genome_ncbi_GCF_000001635.27-downloaded_20240115.gff3	../../../../INPUT_user/genomic_resources/proteomes/Mus_musculus-genome_ncbi_GCF_000001635.27-downloaded_20240115.aa
```

**Project-level INPUT_user structure**:
```
INPUT_user/
├── species_set/
│   └── species_list.txt              # Master species list for the project
└── genomic_resources/
    ├── genomes/                       # .fasta files
    ├── proteomes/                     # .aa files
    ├── annotations/                   # .gff3/.gtf files
    └── maps/                          # identifier mapping .tsv files
```

### File Naming Convention

All source data files follow this structure:

```
genus_species-genome_source_identifier-downloaded_date.extension
```

**Components**:
- `genus_species` - Species name in Genus_species format
- `genome_source_identifier` - Literal string "genome" joined with source database and assembly ID (e.g., genome_ncbi_GCF_000001405.40, genome_figshare_12345)
- `downloaded_date` - Date downloaded in downloaded_YYYYMMDD format (e.g., downloaded_20240115)
- `extension` - File type: `.fasta` (genome), `.gff3` (annotation), `.aa` (proteome)

**Examples**:
```
Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.fasta    # Genome sequence
Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.gff3    # Genome annotation
Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.aa      # Proteome (amino acids)
```

### Sequence Header Convention

FASTA sequence headers follow this structure:

```
>genus_species-source_gene_id-source_transcript_id-source_protein_id
```

**Components**:
- `genus_species` - Species name matching the file name
- `source_gene_id` - Gene identifier from source database
- `source_transcript_id` - Transcript identifier from source database
- `source_protein_id` - Protein identifier from source database

**Example headers**:
```
>Homo_sapiens-ENSG00000139618-ENST00000380152-ENSP00000369497
>Mus_musculus-MGI:87853-NM_007393-NP_031419
>Drosophila_melanogaster-FBgn0000003-FBtr0071763-FBpp0071429
```

---

## T0 and T1 Proteome Concepts

GIGANTIC distinguishes two proteome types based on transcript representation:

- **T1 (one protein per gene/locus)**: The primary proteome used by GIGANTIC for homolog discovery, orthogroup identification, and species tree construction. For NCBI genomes, T1 means the longest transcript per gene extracted from `protein.faa` using the GFF3 annotation. For evigene transcriptomes, T1 means the main transcript per locus selected from the okayset using evgclass headers.

- **T0 (all transcripts per locus)**: The complete proteome including alternative transcripts. For NCBI genomes, T0 includes all protein isoforms. For evigene transcriptomes, T0 includes both main and alt transcripts from the okayset.

**GIGANTIC uses T1 by default** for all downstream analyses (orthogroups, gene trees, annotations). T0 is retained as a reference but is not used in standard pipelines.

---

## Pipeline Structure

genomesDB is organized as four sequential steps plus an optional preparatory step, each with its own workflow:

```
genomesDB/
├── STEP_0-prepare_proteomes/          # (OPTIONAL) Prepare T1 proteomes from evigene transcriptomes
│   └── workflow-COPYME-evigene_to_T1/
├── STEP_1-sources/                    # Ingest user-provided genome/proteome files
│   └── workflow-COPYME-ingest_source_data/
├── STEP_2-standardize_and_evaluate/   # Standardize and evaluate quality
│   └── workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/
├── STEP_3-databases/                  # Build BLAST databases
│   └── workflow-COPYME-build_gigantic_genomesDB/
└── STEP_4-create_final_species_set/   # Select and copy final species set
    └── workflow-COPYME-create_final_species_set/
```

### STEP_0-prepare_proteomes (OPTIONAL)

**Purpose**: Extract T1 proteomes from evigene transcriptome assemblies.

**When to use**: Only needed when your species set includes evigene transcriptomes. If all your data comes from NCBI genomes, skip STEP_0 entirely.

**Key Concept**: Evigene transcriptome assemblies produce an okayset containing main and alt transcripts with classification headers (evgclass). STEP_0 parses these headers to extract only the main transcript per locus, producing a T1 proteome suitable for GIGANTIC.

**Note**: For NCBI genomes, T1 extraction happens later in STEP_2 (Script 003), where the longest transcript per gene is extracted from `protein.faa` using the GFF3 annotation.

**Workflow**: `STEP_0-prepare_proteomes/workflow-COPYME-prepare_proteomes/`

**Inputs**: Evigene okayset FASTA files with evgclass headers
**Outputs**: T1 proteome FASTA files ready for STEP_1

### STEP_1-sources (USER-DRIVEN)

**Purpose**: Ingest user-provided proteome files into GIGANTIC.

**Key Concept**: STEP_1 does NOT automatically download data. Users provide source data from outside GIGANTIC. For NCBI genomes, provide the full `protein.faa` file (T1 extraction happens in STEP_2). For evigene transcriptomes, provide the T1 proteome produced by STEP_0.

**Workflow**: `STEP_1-sources/workflow-COPYME-ingest_source_data/`

**Inputs**: Source manifest listing genome, GTF, and proteome paths
**Outputs**: Proteome files organized in GIGANTIC structure

### STEP_2-standardize_and_evaluate

**Purpose**: Standardize file formats, evaluate genome quality, apply phylonames.

**Workflow**: `STEP_2-standardize_and_evaluate/workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/`

**Inputs**: Proteome files from STEP_1
**Outputs**: Standardized proteomes with phyloname-based naming

### STEP_3-databases

**Purpose**: Build BLAST databases and other search indices.

**Workflow**: `STEP_3-databases/workflow-COPYME-build_gigantic_genomesDB/`

**Inputs**: Standardized proteomes from STEP_2
**Outputs**: BLAST databases, species manifests, proteome indices

### STEP_4-create_final_species_set

**Purpose**: Select and copy final species set for downstream subprojects.

**Workflow**: `STEP_4-create_final_species_set/workflow-COPYME-create_final_species_set/`

**Inputs**: Cleaned proteomes from STEP_2, BLAST databases from STEP_3, optional species selection
**Outputs**: Final proteomes and BLAST databases with `speciesN_` naming convention

---

## Directory Structure

```
genomesDB/
├── README.md                           # This file
├── AI_GUIDE-genomesDB.md               # AI assistant guidance (subproject level)
├── RUN-clean_and_record_subproject.sh  # Cleanup script for entire subproject
├── RUN-update_upload_to_server.sh      # Update server sharing symlinks
├── output_to_input/                    # Final outputs for downstream subprojects
├── upload_to_server/                   # Files to share via GIGANTIC server
│
├── STEP_0-prepare_proteomes/           # (OPTIONAL) Prepare T1 from evigene transcriptomes
│   ├── README.md
│   ├── output_to_input/                # T1 proteomes for STEP_1
│   └── workflow-COPYME-prepare_proteomes/
│       ├── INPUT_user/
│       ├── OUTPUT_pipeline/
│       ├── RUN-workflow.sh
│       ├── RUN-workflow.sbatch
│       └── ai/
│
├── STEP_1-sources/
│   ├── README.md                       # Step-specific documentation
│   ├── AI_GUIDE-sources.md             # AI guidance for this step
│   ├── RUN-clean_and_record_subproject.sh  # Step-level cleanup
│   ├── output_to_input/                # Outputs passed to STEP_2
│   └── workflow-COPYME-ingest_source_data/
│       ├── INPUT_user/                 # Source manifest goes here
│       ├── OUTPUT_pipeline/            # Workflow outputs
│       ├── RUN-workflow.sh             # Local execution
│       ├── RUN-workflow.sbatch         # SLURM execution
│       └── ai/                         # Pipeline scripts
│
├── STEP_2-standardize_and_evaluate/
│   ├── README.md
│   ├── AI_GUIDE-standardize_and_evaluate.md
│   ├── RUN-clean_and_record_subproject.sh
│   ├── output_to_input/                # Outputs passed to STEP_3
│   └── workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/
│       ├── INPUT_user/
│       ├── OUTPUT_pipeline/
│       ├── RUN-workflow.sh             # Local execution
│       ├── RUN-workflow.sbatch         # SLURM execution
│       └── ai/
│
├── STEP_3-databases/
│   ├── README.md
│   ├── AI_GUIDE-databases.md
│   ├── RUN-clean_and_record_subproject.sh
│   ├── output_to_input/                # Step outputs (also copied to subproject root)
│   └── workflow-COPYME-build_gigantic_genomesDB/
│       ├── INPUT_user/
│       ├── OUTPUT_pipeline/
│       ├── RUN-workflow.sh             # Local execution
│       ├── RUN-workflow.sbatch         # SLURM execution
│       └── ai/
│
└── STEP_4-create_final_species_set/
    ├── README.md
    ├── AI_GUIDE-create_final_species_set.md
    ├── RUN-clean_and_record_subproject.sh
    ├── output_to_input/                # Final species set for downstream subprojects
    └── workflow-COPYME-create_final_species_set/
        ├── INPUT_user/
        ├── OUTPUT_pipeline/
        ├── RUN-workflow.sh             # Local execution
        ├── RUN-workflow.sbatch         # SLURM execution
        └── ai/
```

---

## Data Flow

```
STEP_0-prepare_proteomes (optional) → STEP_1-sources → STEP_2-standardize_and_evaluate → STEP_3-databases → STEP_4-create_final_species_set → Downstream Subprojects
         ↓                                 ↓                      ↓                           ↓                        ↓
    output_to_input/                  output_to_input/      output_to_input/           output_to_input/        output_to_input/
    STEP_0-prepare_                   STEP_1-sources/     STEP_2-standardize_         STEP_3-databases/   STEP_4-create_final_
    proteomes/                                            and_evaluate/                                    species_set/
```

STEP_0 is only needed when working with evigene transcriptomes. For NCBI genomes, start directly at STEP_1.

Each step publishes outputs to the single subproject-root `output_to_input/` directory, under its own STEP subdirectory. STEP_4's outputs are the final species set that downstream GIGANTIC subprojects reference.

---

## Quick Start

### Running All Steps

```bash
# STEP_0 (OPTIONAL): Prepare T1 proteomes from evigene transcriptomes
# Only needed if you have evigene data. Skip for NCBI genomes.
cd STEP_0-prepare_proteomes/workflow-COPYME-prepare_proteomes/
# Place evigene okayset files in INPUT_user/
bash RUN-workflow.sh

# STEP_1: Ingest source data
cd ../../STEP_1-sources/workflow-COPYME-ingest_source_data/
# Create INPUT_user/source_manifest.tsv with your data
bash RUN-workflow.sh

# STEP_2: Standardize and evaluate
cd ../../STEP_2-standardize_and_evaluate/workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/
bash RUN-workflow.sh

# STEP_3: Build databases
cd ../../STEP_3-databases/workflow-COPYME-build_gigantic_genomesDB/
bash RUN-workflow.sh

# STEP_4: Create final species set
cd ../../STEP_4-create_final_species_set/workflow-COPYME-create_final_species_set/
# Optional: edit INPUT_user/selected_species.txt to filter species
bash RUN-workflow.sh
```

### Cleanup After Completion

```bash
# Clean entire subproject (all steps)
cd genomesDB/
bash RUN-clean_and_record_subproject.sh --all

# Or clean individual steps
cd STEP_1-sources/
bash RUN-clean_and_record_subproject.sh --all
```

---

## Research Notebook Integration

AI sessions are extracted project-wide to:
```
research_notebook/research_ai/sessions/
```

Workflow run logs are saved to each workflow's own `ai/logs/` directory.

---

## Outputs Shared Downstream (`output_to_input/`)

Other GIGANTIC subprojects reference genomesDB outputs via:
```
genomesDB/output_to_input/
```

**Dependent subprojects**:
- **annotations_hmms** - Uses proteome files for functional annotation
- **orthogroups** - Uses proteome files for ortholog identification
- **trees_gene_families** - Uses BLAST databases for homolog searches
- **All other subprojects** - Reference proteomes and databases

---

## Dependencies

genomesDB workflows depend on the `phylonames` subproject for species naming. Run phylonames first to generate the species mapping.

---

## Notes

- STEP_1 is user-driven - users provide source data, no automatic downloads
- Step 2 evaluation may flag low-quality genomes for review
- Step 3 BLAST databases require substantial disk space
- The complete pipeline may take several hours for large species sets
