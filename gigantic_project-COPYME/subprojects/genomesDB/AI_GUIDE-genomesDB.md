# AI Guide: genomesDB Subproject

**For AI Assistants**: Read `../../AI_GUIDE-project.md` first for GIGANTIC overview, directory structure, and general patterns. This guide covers genomesDB-specific concepts and the four-step architecture.

**Location**: `gigantic_project-COPYME/subprojects/genomesDB/`

**Status**: The active genomesDB. Build outputs live in `workflow-RUN_1` of each STEP. The specific species set is determined by the source manifest provided in STEP_1.

---

## ⚠️ CRITICAL: Surface Discrepancies - No Silent Changes

**The user is managing this project - you must surface discrepancies so the user can make decisions. Silent changes undermine project management.**

- ❌ **NEVER** silently do something different than requested
- ❌ **NEVER** assume you know better and proceed without asking
- ✅ **ALWAYS** stop and explain the discrepancy
- ✅ **ALWAYS** ask for clarification before proceeding

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../AI_GUIDE-project.md` |
| genomesDB concepts, pipeline structure | This file |
| STEP_0 prepare_proteomes workflow | `STEP_0-prepare_proteomes/workflow-COPYME-*/ai/AI_GUIDE-*_workflow.md` |
| STEP_1 sources workflow | `STEP_1-sources/workflow-COPYME-*/ai/AI_GUIDE-*_workflow.md` |
| STEP_2 standardize_and_evaluate workflow | `STEP_2-standardize_and_evaluate/workflow-COPYME-*/ai/AI_GUIDE-*_workflow.md` |
| STEP_3 databases workflow | `STEP_3-databases/workflow-COPYME-*/ai/AI_GUIDE-*_workflow.md` |
| STEP_4 create_final_species_set workflow | `STEP_4-create_final_species_set/workflow-COPYME-*/ai/AI_GUIDE-*_workflow.md` |

---

## What This Subproject Does

**Purpose**: Manage genome and proteome data for GIGANTIC projects.

**Pipeline**:
0. **Prepare Proteomes** *(optional)* - Extract T1 proteomes from evigene transcriptomes
1. **Sources** - Ingest user-provided proteome files (USER-DRIVEN, no auto-downloads)
2. **Standardize and Evaluate** - Standardize formats, apply phylonames, evaluate quality
3. **Databases** - Build BLAST databases and search indices
4. **Create Final Species Set** - Select and copy final species set for downstream subprojects

**Critical**: Run phylonames subproject FIRST - genomesDB depends on phylonames for species naming.

---

## T0 and T1 Proteome Concepts

GIGANTIC distinguishes two proteome types based on transcript representation:

| Type | Definition | Use in GIGANTIC |
|------|-----------|-----------------|
| **T1** | One protein per gene/locus | Default for all analyses (orthogroups, gene trees, annotations) |
| **T0** | All transcripts per locus | Retained as reference, not used in standard pipelines |

**How T1 is obtained depends on the data source**:

| Data Source | T1 Extraction Method | Where It Happens |
|-------------|----------------------|------------------|
| **NCBI genomes** | Longest transcript per gene, extracted from `protein.faa` using GFF3 annotation | STEP_2, Script 003 |
| **Evigene transcriptomes** | Main transcript per locus, selected from okayset using evgclass headers | STEP_0 |

**T0 composition by source**:

| Data Source | T0 Contains |
|-------------|-------------|
| **NCBI genomes** | All protein isoforms from `protein.faa` |
| **Evigene transcriptomes** | Main + alt transcripts from okayset |

**Key principle**: GIGANTIC uses T1 by default for homolog discovery. One representative protein per gene avoids inflating BLAST hits and orthogroup assignments with redundant isoforms.

---

## GIGANTIC Source Data Naming Conventions

### Source Manifest Format

The source manifest is a **four-column TSV**:

```
genus_species	genome_path	genome_annotation_path	proteome_path
```

**Example** (using relative paths to project-level INPUT_user):
```tsv
genus_species	genome_path	genome_annotation_path	proteome_path
Homo_sapiens	../../../../INPUT_user/genomic_resources/genomes/Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.fasta	../../../../INPUT_user/genomic_resources/annotations/Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.gff3	../../../../INPUT_user/genomic_resources/proteomes/Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.aa
Mus_musculus	../../../../INPUT_user/genomic_resources/genomes/Mus_musculus-genome_ncbi_GCF_000001635.27-downloaded_20240115.fasta	../../../../INPUT_user/genomic_resources/annotations/Mus_musculus-genome_ncbi_GCF_000001635.27-downloaded_20240115.gff3	../../../../INPUT_user/genomic_resources/proteomes/Mus_musculus-genome_ncbi_GCF_000001635.27-downloaded_20240115.aa
```

### File Naming Convention

**All source files follow this structure**:

```
genus_species-genome_source_identifier-downloaded_date.extension
```

| Component | Description | Example |
|-----------|-------------|---------|
| `genus_species` | Species name | `Homo_sapiens` |
| `genome_source_identifier` | "genome" joined with source database + assembly ID | `genome_ncbi_GCF_000001405.40` |
| `downloaded_date` | downloaded_YYYYMMDD format | `downloaded_20240115` |
| `extension` | File type | `.fasta`, `.gff3`, `.aa` |

**File type extensions**:
- `.fasta` - Genome sequence (nucleotide)
- `.gff3` - Genome annotation
- `.aa` - Proteome (amino acid sequences)

**Examples**:
```
Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.fasta
Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.gff3
Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.aa
```

### Sequence Header Convention

**FASTA headers follow this structure**:

```
>genus_species-source_gene_id-source_transcript_id-source_protein_id
```

| Component | Description | Example |
|-----------|-------------|---------|
| `genus_species` | Must match filename species | `Homo_sapiens` |
| `source_gene_id` | Gene ID from source database | `ENSG00000139618` |
| `source_transcript_id` | Transcript ID from source | `ENST00000380152` |
| `source_protein_id` | Protein ID from source | `ENSP00000369497` |

**Example headers**:
```
>Homo_sapiens-ENSG00000139618-ENST00000380152-ENSP00000369497
>Mus_musculus-MGI:87853-NM_007393-NP_031419
>Drosophila_melanogaster-FBgn0000003-FBtr0071763-FBpp0071429
```

**Why this format?**
- Species is immediately identifiable from any sequence
- Full provenance chain: gene → transcript → protein
- Enables tracing back to source databases
- Consistent across all GIGANTIC analyses

---

## Pipeline Architecture

### STEP_0-prepare_proteomes (OPTIONAL)

**Directory**: `STEP_0-prepare_proteomes/`
**Workflow**: `workflow-COPYME-prepare_proteomes`

**When to use**: Only needed when your species set includes evigene transcriptomes. If all data comes from NCBI genomes, skip STEP_0 entirely.

**Function**:
- Parse evigene okayset FASTA files with evgclass headers
- Extract main transcript per locus (T1) based on evgclass classification
- Produce clean T1 proteome FASTA files ready for STEP_1

**Note**: For NCBI genomes, T1 extraction happens later in STEP_2 (Script 003), where the longest transcript per gene is extracted from `protein.faa` using the GFF3 annotation. STEP_0 exists because evigene transcriptomes require a different extraction method that must happen before ingestion.

**Outputs**:
- `output_to_input/STEP_0-prepare_proteomes/` - T1 proteomes for STEP_1

### STEP_1-sources (USER-DRIVEN)

**Directory**: `STEP_1-sources/`
**Workflow**: `workflow-COPYME-ingest_source_data`

**Critical Concept**: STEP_1 does NOT download data automatically. Users provide their own source files. For NCBI genomes, provide the full `protein.faa` file (T1 extraction happens in STEP_2). For evigene transcriptomes, provide the T1 proteome produced by STEP_0.

**Function**:
- Accept user-provided manifest with genome, GTF, proteome paths
- Validate source files exist
- Hard copy proteomes to OUTPUT_pipeline
- Create symlinks in output_to_input for STEP_2

**Outputs**:
- `output_to_input/STEP_1-sources/proteomes/` - Symlinks for STEP_2

### STEP_2-standardize_and_evaluate

**Directory**: `STEP_2-standardize_and_evaluate/`
**Workflow**: `workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb`

**Function**:
- Rename files using phyloname convention
- Validate FASTA format
- Calculate genome statistics
- Flag quality issues

**Outputs**:
- `output_to_input/STEP_2-standardize_and_evaluate/standardized_proteomes/` - Clean files for STEP_3
- Evaluation reports

### STEP_3-databases

**Directory**: `STEP_3-databases/`
**Workflow**: `workflow-COPYME-build_gigantic_genomesDB`

**Function**:
- Build BLAST databases (blastp)
- Create species manifests
- Generate proteome indices

**Outputs**:
- `output_to_input/STEP_3-databases/` - BLAST databases

### STEP_4-create_final_species_set

**Directory**: `STEP_4-create_final_species_set/`
**Workflow**: `workflow-COPYME-create_final_species_set`

**Function**:
- User reviews STEP_2 quality metrics and selects species to keep
- Validates species selection against STEP_2 and STEP_3 outputs
- Copies selected proteomes and BLAST databases
- Creates `speciesN_` named directories for downstream subprojects

**Outputs**:
- `output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/` - Final proteomes
- `output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_blastp/` - Final BLAST databases

---

## Directory Structure (relative to subproject root)

```
genomesDB/
├── README.md                           # Human documentation
├── AI_GUIDE-genomesDB.md               # THIS FILE
├── RUN-clean_and_record_subproject.sh  # Cleanup for entire subproject
├── RUN-update_upload_to_server.sh      # Update server symlinks
│
├── output_to_input/                    # Final outputs for downstream
├── upload_to_server/                   # Server sharing
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
│   ├── README.md
│   ├── AI_GUIDE-sources.md
│   ├── RUN-clean_and_record_subproject.sh
│   └── workflow-COPYME-ingest_source_data/
│       ├── INPUT_user/
│       │   └── source_manifest.tsv     # User creates this
│       ├── OUTPUT_pipeline/
│       ├── RUN-workflow.sh             # Local execution
│       ├── RUN-workflow.sbatch         # SLURM execution
│       └── ai/
│
├── STEP_2-standardize_and_evaluate/
│   ├── README.md
│   ├── AI_GUIDE-standardize_and_evaluate.md
│   ├── RUN-clean_and_record_subproject.sh
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
    └── workflow-COPYME-create_final_species_set/
        ├── INPUT_user/
        ├── OUTPUT_pipeline/
        ├── RUN-workflow.sh             # Local execution
        ├── RUN-workflow.sbatch         # SLURM execution
        └── ai/
```

---

## Data Flow Between Steps

```
output_to_input/STEP_0-prepare_proteomes/ (optional, evigene only)
                         ↓
output_to_input/STEP_1-sources/ → STEP_2-standardize_and_evaluate/INPUT_user/
                                              ↓
output_to_input/STEP_2-standardize_and_evaluate/ → STEP_3-databases/INPUT_user/
                                                            ↓
          STEP_2 + STEP_3 outputs → STEP_4-create_final_species_set
                                              ↓
                   output_to_input/STEP_4-create_final_species_set/
                                              ↓
                              (Other GIGANTIC subprojects)
```

**T1 extraction paths**: For NCBI genomes, T1 is extracted in STEP_2 (Script 003) from the full `protein.faa` using GFF3. For evigene transcriptomes, T1 is extracted in STEP_0 from the okayset using evgclass headers, so STEP_1 receives an already-filtered T1 proteome.

---

## Path Depth Adjustment

Step directories are nested ONE level deeper than standard subprojects:

| Location | Relative path to project root |
|----------|-------------------------------|
| `genomesDB/` | `../../` |
| `genomesDB/STEP_1-sources/` | `../../../` |
| `genomesDB/STEP_1-sources/workflow-COPYME-*/` | `../../../../` |
| `genomesDB/STEP_1-sources/workflow-COPYME-*/ai/` | `../../../../../` |

---

## Research Notebook Location

genomesDB logging uses two locations:

- **AI sessions** (project-wide): `research_notebook/research_ai/sessions/`
- **Workflow run logs** (per-workflow): `workflow-*/ai/logs/`

```
research_notebook/research_ai/sessions/    # All AI sessions (project-wide, not per-subproject)
workflow-*/ai/logs/                         # Run logs specific to each workflow
workflow-*/ai/validation/                   # Validation outputs specific to each workflow
```

Sessions are consolidated project-wide. Run logs stay with the workflow that generated them.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "Species not found" | phylonames not run | Run phylonames subproject first |
| "Source file not found" | Path in manifest doesn't exist | Verify paths with `ls` |
| STEP_2 can't find inputs | STEP_1 not run | Run STEP_1-sources workflow first |
| STEP_3 can't find inputs | STEP_2 not run | Run STEP_2-standardize_and_evaluate first |
| BLAST database empty | No proteomes passed QC | Check STEP_2 evaluation reports |
| STEP_4 can't find inputs | STEP_2 or STEP_3 not run | Run STEP_2 and STEP_3 first |
| STEP_4 species not found | Species in selection but not in STEP_2/STEP_3 | Check spelling in selected_species.txt |
| "No phyloname mapping" | Missing mapping file | Run phylonames, check output_to_input |
| Manifest format error | Wrong columns or delimiter | Use 4 tab-separated columns |
| STEP_0 evgclass parsing fails | Missing or malformed evgclass headers | Verify okayset files have proper evigene classification headers |
| Evigene T1 has too few sequences | Alt transcripts not separated | Check evgclass filtering logic in STEP_0 scripts |

### Diagnostic Commands

```bash
# Check phylonames dependency
ls ../phylonames/output_to_input/maps/

# Check STEP_0 outputs (if using evigene transcriptomes)
ls output_to_input/STEP_0-prepare_proteomes/

# Check STEP_1 outputs
ls output_to_input/STEP_1-sources/

# Check STEP_2 outputs
ls output_to_input/STEP_2-standardize_and_evaluate/

# Check STEP_3 outputs
ls output_to_input/STEP_3-databases/

# Check STEP_4 outputs (final species set)
ls output_to_input/STEP_4-create_final_species_set/
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `STEP_0-prepare_proteomes/workflow-*/INPUT_user/` | Evigene okayset files (optional) | **YES** (if using evigene) |
| `STEP_1-sources/workflow-*/INPUT_user/source_manifest.tsv` | List of genomes/proteomes to ingest | **YES** |
| `STEP_2-standardize_and_evaluate/workflow-*/INPUT_user/` | (from STEP_1) | No |
| `STEP_3-databases/workflow-*/INPUT_user/` | (from STEP_2) | No |
| `STEP_4-create_final_species_set/workflow-*/START_HERE-user_config.yaml` | Paths to STEP_2/STEP_3 outputs | **YES** |
| `STEP_4-create_final_species_set/workflow-*/INPUT_user/selected_species.txt` | Species selection (optional) | **YES** (optional) |
| `output_to_input/STEP_4-create_final_species_set/` | Final species set | No |
| `upload_to_server/upload_manifest.tsv` | What to share | **YES** |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| Starting genomesDB | "Have you run the phylonames subproject first?" |
| Starting genomesDB | "Are your species from NCBI genomes, evigene transcriptomes, or a mix of both? (Evigene transcriptomes need STEP_0 to extract T1 proteomes before STEP_1.)" |
| Before STEP_0 | "Where are your evigene okayset files? Do the FASTA headers contain evgclass classification information?" |
| Before STEP_1 | "Where are your genome, GTF, and proteome files located?" |
| Manifest creation | "Are your files named with the GIGANTIC convention? (genus_species-genome_source_identifier-downloaded_date.ext)" |
| Header format | "Do your FASTA headers follow the convention? (genus_species-gene_id-transcript_id-protein_id)" |
| Quality thresholds | "What quality thresholds should we use for evaluation?" |
| Before STEP_4 | "Have STEP_2 and STEP_3 completed? Do you want all species or a subset?" |
| Error occurred | "Which step failed? What error message?" |

---

## Next Steps After genomesDB

Guide users to:
1. **annotations_hmms** - Run functional annotations on proteomes
2. **orthogroups** - Identify ortholog groups across species
3. **trees_gene_families** - Build gene family phylogenies
