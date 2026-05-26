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

genomesDB is organized as four sequential STEPs, each with its own workflow:

```
genomesDB/
├── STEP_1-sources/                    # Ingest user-provided genome/proteome files
│   └── workflow-COPYME-ingest_source_data/
├── STEP_2-standardize_and_evaluate/   # Standardize and evaluate quality
│   └── workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/
├── STEP_3-databases/                  # Build BLAST databases
│   └── workflow-COPYME-build_gigantic_genomesDB/
└── STEP_4-create_final_species_set/   # Select and copy final species set
    └── workflow-COPYME-create_final_species_set/
```

### A note on evigene transcriptomes (user-side prep)

If your species set includes evigene transcriptome assemblies, the T1
proteome (one protein per gene) needs to be extracted from the okayset
using its `evgclass` headers **before** ingestion. This is **user-side
prep work**, not a GIGANTIC STEP: do it in
`research_notebook/research_user/<species>/` (your wild-west sandbox
per §1, §25), then symlink the resulting T1 `.aa` file into
`INPUT_user/genomic_resources/proteomes/` per §17, §18. STEP_1 then
ingests it like any other proteome.

For NCBI genomes, no user prep is needed — STEP_2 handles T1 extraction
from the full `protein.faa` using the GFF3 annotation.

(An older design had this evigene prep as a "STEP_0-prepare_proteomes"
inside genomesDB. That STEP has been deprecated in favor of the
INPUT_user staging pattern — the prep work belongs in the user's
sandbox, not inside the GIGANTIC subproject.)

### STEP_1-sources (USER-DRIVEN)

**Purpose**: Ingest user-provided proteome files into GIGANTIC.

**Key Concept**: STEP_1 does NOT automatically download data. Users
provide source data via symlinks in `INPUT_user/` (per §17, §18). For
NCBI genomes, provide the full `protein.faa` file (T1 extraction happens
in STEP_2). For evigene transcriptomes, do the T1 extraction in
`research_notebook/research_user/` first (see above) and provide the
extracted T1 proteome.

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
├── README.md                                # This file
├── AI_GUIDE.md                              # AI assistant guidance (subproject level)
│
├── RUN-clean_and_record_subproject.sh       # Subproject-level cleanup + session recording
├── RUN-update_upload_to_server.sh           # Subproject-level publisher (§38)
│
├── upload_to_server/                        # Single publish destination per §38
│                                            # (auto-populated by RUN-update_upload_to_server.sh)
│
├── output_to_input/                         # Outputs for downstream subprojects (§2)
│   ├── STEP_1-sources/
│   ├── STEP_2-standardize_and_evaluate/
│   ├── STEP_3-databases/
│   └── STEP_4-create_final_species_set/    # The final species set canonically lives here
│
├── research_notebook/                       # Personal workspace + AI session captures (§1, §25)
│
├── STEP_1-sources/
│   ├── README.md
│   ├── AI_GUIDE.md                          # STEP-level guide
│   └── workflow-COPYME-ingest_source_data/
│       ├── README.md
│       ├── RUN-workflow.sh                  # Unified driver — local or SLURM via execution_mode (§29)
│       ├── START_HERE-user_config.yaml      # Config: project name, execution_mode, slurm.*
│       ├── upload_manifest.tsv              # Server publish manifest (§38, §39)
│       ├── INPUT_user/                      # Source manifest goes here
│       ├── OUTPUT_pipeline/                 # Workflow outputs
│       └── ai/                              # NextFlow pipeline + scripts
│
├── STEP_2-standardize_and_evaluate/
│   ├── README.md
│   ├── AI_GUIDE.md
│   └── workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/
│       ├── README.md, RUN-workflow.sh, START_HERE-user_config.yaml
│       ├── upload_manifest.tsv              # Server publish manifest
│       ├── INPUT_user/, OUTPUT_pipeline/
│       └── ai/
│
├── STEP_3-databases/
│   ├── README.md
│   ├── AI_GUIDE.md
│   └── workflow-COPYME-build_gigantic_genomesDB/
│       ├── README.md, RUN-workflow.sh, START_HERE-user_config.yaml
│       ├── upload_manifest.tsv              # Server publish manifest
│       ├── INPUT_user/, OUTPUT_pipeline/
│       └── ai/
│
└── STEP_4-create_final_species_set/
    ├── README.md
    ├── AI_GUIDE.md
    └── workflow-COPYME-create_final_species_set/
        ├── README.md, RUN-workflow.sh, START_HERE-user_config.yaml
        ├── upload_manifest.tsv              # Server publish manifest
        ├── INPUT_user/, OUTPUT_pipeline/
        └── ai/
```

Per §38 + §41, genomesDB is a STEP-organized subproject with ONE
subproject-level `upload_to_server/` (no per-STEP `upload_to_server/`).
Per §29, the unified `RUN-workflow.sh` drives both local and SLURM
execution via the YAML `execution_mode` key.

---

## Data Flow

```
[user prep in research_notebook/research_user/ if needed (e.g., evigene T1 extraction)]
            ↓
INPUT_user/genomic_resources/  (symlinks per §17, §18)
            ↓
STEP_1-sources → STEP_2-standardize_and_evaluate → STEP_3-databases → STEP_4-create_final_species_set → Downstream Subprojects
       ↓                      ↓                           ↓                          ↓
  output_to_input/      output_to_input/           output_to_input/        output_to_input/
  STEP_1-sources/     STEP_2-standardize_         STEP_3-databases/   STEP_4-create_final_
                      and_evaluate/                                    species_set/
```

Each STEP publishes outputs to the single subproject-root
`output_to_input/` directory, under its own STEP subdirectory. STEP_4's
outputs are the final species set that downstream GIGANTIC subprojects
reference.

---

## Quick Start

### Running All Steps

```bash
# OPTIONAL pre-step (user-side, only for evigene transcriptomes):
#   Extract T1 proteome in research_notebook/research_user/<species>/
#   from the evigene okayset, then symlink the resulting .aa into
#   ../../INPUT_user/genomic_resources/proteomes/ (per §17, §18).
#   For NCBI genomes, no prep needed — STEP_2 handles T1 extraction.

# STEP_1: Ingest source data
cd STEP_1-sources/workflow-COPYME-ingest_source_data/
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
