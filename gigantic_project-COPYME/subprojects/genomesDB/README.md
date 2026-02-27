# genomesDB - GIGANTIC Genome Database System

**AI**: Claude Code | Opus 4.5 | 2026 February 12
**Human**: Eric Edsinger

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

**Example**:
```tsv
genus_species	genome_path	gtf_path	proteome_path
Homo_sapiens	/data/Homo_sapiens-genome-GCF_000001405.40-20240115.fasta	/data/Homo_sapiens-genome-GCF_000001405.40-20240115.gtf	/data/Homo_sapiens-genome-GCF_000001405.40-20240115.aa
Mus_musculus	/data/Mus_musculus-genome-GCF_000001635.27-20240115.fasta	/data/Mus_musculus-genome-GCF_000001635.27-20240115.gtf	/data/Mus_musculus-genome-GCF_000001635.27-20240115.aa
```

### File Naming Convention

All source data files follow this structure:

```
genus_species-genome-source_genome_project_identifier-download_date.extension
```

**Components**:
- `genus_species` - Species name in Genus_species format
- `genome` - Literal string "genome" (indicates this is genome-level data)
- `source_genome_project_identifier` - Source database and assembly ID (e.g., GCF_000001405.40, PRJNA12345)
- `download_date` - Date downloaded in YYYYMMDD format
- `extension` - File type: `.fasta` (genome), `.gff` or `.gtf` (annotation), `.aa` (proteome)

**Examples**:
```
Homo_sapiens-genome-GCF_000001405.40-20240115.fasta    # Genome sequence
Homo_sapiens-genome-GCF_000001405.40-20240115.gtf      # Gene annotation
Homo_sapiens-genome-GCF_000001405.40-20240115.aa       # Proteome (amino acids)
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

## Three-Step Structure

genomesDB is organized as three sequential steps, each with its own workflow:

```
genomesDB/
├── STEP_1-sources/                    # Ingest user-provided genome/proteome files
│   └── workflow-COPYME-ingest_source_proteomes/
├── STEP_2-standardize_and_evaluate/   # Standardize and evaluate quality
│   └── workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/
└── STEP_3-databases/                  # Build BLAST databases
    └── workflow-COPYME-build_gigantic_genomesDB/
```

### STEP_1-sources (USER-DRIVEN)

**Purpose**: Ingest user-provided proteome files into GIGANTIC.

**Key Concept**: STEP_1 does NOT automatically download data. Users provide source data from outside GIGANTIC.

**Workflow**: `STEP_1-sources/workflow-COPYME-ingest_source_proteomes/`

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

---

## Directory Structure

```
genomesDB/
├── README.md                           # This file
├── AI_GUIDE-genomesDB.md               # AI assistant guidance (subproject level)
├── RUN-clean_and_record_subproject.sh  # Cleanup script for entire subproject
├── RUN-update_upload_to_server.sh      # Update server sharing symlinks
├── user_research/                      # Personal workspace for entire subproject
├── output_to_input/                    # Final outputs for downstream subprojects
├── upload_to_server/                   # Files to share via GIGANTIC server
│
├── STEP_1-sources/
│   ├── README.md                       # Step-specific documentation
│   ├── AI_GUIDE-sources.md             # AI guidance for this step
│   ├── RUN-clean_and_record_subproject.sh  # Step-level cleanup
│   ├── user_research/                  # Step-specific workspace (user's source data)
│   ├── output_to_input/                # Outputs passed to STEP_2
│   └── workflow-COPYME-ingest_source_proteomes/
│       ├── INPUT_user/                 # Source manifest goes here
│       ├── OUTPUT_pipeline/            # Workflow outputs
│       └── ai/                         # Pipeline scripts
│
├── STEP_2-standardize_and_evaluate/
│   ├── README.md
│   ├── AI_GUIDE-standardize_and_evaluate.md
│   ├── RUN-clean_and_record_subproject.sh
│   ├── user_research/
│   ├── output_to_input/                # Outputs passed to STEP_3
│   └── workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/
│       ├── INPUT_user/
│       ├── OUTPUT_pipeline/
│       └── ai/
│
└── STEP_3-databases/
    ├── README.md
    ├── AI_GUIDE-databases.md
    ├── RUN-clean_and_record_subproject.sh
    ├── user_research/
    ├── output_to_input/                # Step outputs (also copied to subproject root)
    └── workflow-COPYME-build_gigantic_genomesDB/
        ├── INPUT_user/
        ├── OUTPUT_pipeline/
        └── ai/
```

---

## Data Flow

```
STEP_1-sources → STEP_2-standardize_and_evaluate → STEP_3-databases → Downstream Subprojects
      ↓                      ↓                           ↓
 output_to_input        output_to_input          genomesDB/output_to_input
                                                 (shared with other subprojects)
```

Each step passes outputs to the next step via its `output_to_input/` directory. STEP_3's outputs are also copied to the main `genomesDB/output_to_input/` for use by other GIGANTIC subprojects.

---

## Quick Start

### Running All Steps

```bash
# STEP_1: Ingest source proteomes
cd STEP_1-sources/workflow-COPYME-ingest_source_proteomes/
# Create INPUT_user/source_manifest.tsv with your data
bash RUN-ingest_sources.sh

# STEP_2: Standardize and evaluate
cd ../../STEP_2-standardize_and_evaluate/workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/
bash RUN-workflow.sh

# STEP_3: Build databases
cd ../../STEP_3-databases/workflow-COPYME-build_gigantic_genomesDB/
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

All AI session recordings for genomesDB (regardless of which step they're from) are saved to:
```
research_notebook/research_ai/subproject-genomesDB/sessions/
```

This consolidates all genomesDB-related AI documentation in one location.

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
