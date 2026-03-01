# AI Guide: genomesDB Subproject

**For AI Assistants**: Read `../../AI_GUIDE-project.md` first for GIGANTIC overview, directory structure, and general patterns. This guide covers genomesDB-specific concepts and the four-step architecture.

**Location**: `gigantic_project-COPYME/subprojects/genomesDB/`

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
| genomesDB concepts, four-step structure | This file |
| STEP_1 sources workflow | `STEP_1-sources/workflow-COPYME-*/ai/AI_GUIDE-*_workflow.md` |
| STEP_2 standardize_and_evaluate workflow | `STEP_2-standardize_and_evaluate/workflow-COPYME-*/ai/AI_GUIDE-*_workflow.md` |
| STEP_3 databases workflow | `STEP_3-databases/workflow-COPYME-*/ai/AI_GUIDE-*_workflow.md` |
| STEP_4 create_final_species_set workflow | `STEP_4-create_final_species_set/workflow-COPYME-*/ai/AI_GUIDE-*_workflow.md` |

---

## What This Subproject Does

**Purpose**: Manage genome and proteome data for GIGANTIC projects.

**Four-Step Pipeline**:
1. **Sources** - Ingest user-provided proteome files (USER-DRIVEN, no auto-downloads)
2. **Standardize and Evaluate** - Standardize formats, apply phylonames, evaluate quality
3. **Databases** - Build BLAST databases and search indices
4. **Create Final Species Set** - Select and copy final species set for downstream subprojects

**Critical**: Run phylonames subproject FIRST - genomesDB depends on phylonames for species naming.

---

## GIGANTIC Source Data Naming Conventions

### Source Manifest Format

The source manifest is a **four-column TSV**:

```
genus_species	genome_path	gtf_path	proteome_path
```

**Example**:
```tsv
genus_species	genome_path	gtf_path	proteome_path
Homo_sapiens	/data/Homo_sapiens-genome-GCF_000001405.40-20240115.fasta	/data/Homo_sapiens-genome-GCF_000001405.40-20240115.gtf	/data/Homo_sapiens-genome-GCF_000001405.40-20240115.aa
Mus_musculus	/data/Mus_musculus-genome-GCF_000001635.27-20240115.fasta	/data/Mus_musculus-genome-GCF_000001635.27-20240115.gtf	/data/Mus_musculus-genome-GCF_000001635.27-20240115.aa
```

### File Naming Convention

**All source files follow this structure**:

```
genus_species-genome-source_genome_project_identifier-download_date.extension
```

| Component | Description | Example |
|-----------|-------------|---------|
| `genus_species` | Species name | `Homo_sapiens` |
| `genome` | Literal string (indicates genome-level data) | `genome` |
| `source_genome_project_identifier` | Source database + assembly ID | `GCF_000001405.40` |
| `download_date` | YYYYMMDD format | `20240115` |
| `extension` | File type | `.fasta`, `.gtf`, `.gff`, `.aa` |

**File type extensions**:
- `.fasta` - Genome sequence (nucleotide)
- `.gff` or `.gtf` - Gene annotation
- `.aa` - Proteome (amino acid sequences)

**Examples**:
```
Homo_sapiens-genome-GCF_000001405.40-20240115.fasta
Homo_sapiens-genome-GCF_000001405.40-20240115.gtf
Homo_sapiens-genome-GCF_000001405.40-20240115.aa
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

## Four-Step Architecture

### STEP_1-sources (USER-DRIVEN)

**Directory**: `STEP_1-sources/`
**Workflow**: `workflow-COPYME-ingest_source_data`

**Critical Concept**: STEP_1 does NOT download data automatically. Users provide their own source files.

**Function**:
- Accept user-provided manifest with genome, GTF, proteome paths
- Validate source files exist
- Hard copy proteomes to OUTPUT_pipeline
- Create symlinks in output_to_input for STEP_2

**Outputs**:
- `STEP_1-sources/output_to_input/proteomes/` - Symlinks for STEP_2

### STEP_2-standardize_and_evaluate

**Directory**: `STEP_2-standardize_and_evaluate/`
**Workflow**: `workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb`

**Function**:
- Rename files using phyloname convention
- Validate FASTA format
- Calculate genome statistics
- Flag quality issues

**Outputs**:
- `STEP_2-standardize_and_evaluate/output_to_input/standardized_proteomes/` - Clean files for STEP_3
- Evaluation reports

### STEP_3-databases

**Directory**: `STEP_3-databases/`
**Workflow**: `workflow-COPYME-build_gigantic_genomesDB`

**Function**:
- Build BLAST databases (blastp)
- Create species manifests
- Generate proteome indices

**Outputs**:
- `STEP_3-databases/output_to_input/` - BLAST databases

### STEP_4-create_final_species_set

**Directory**: `STEP_4-create_final_species_set/`
**Workflow**: `workflow-COPYME-create_final_species_set`

**Function**:
- User reviews STEP_2 quality metrics and selects species to keep
- Validates species selection against STEP_2 and STEP_3 outputs
- Copies selected proteomes and BLAST databases
- Creates `speciesN_` named directories for downstream subprojects

**Outputs**:
- `STEP_4-create_final_species_set/output_to_input/speciesN_gigantic_T1_proteomes/` - Final proteomes
- `STEP_4-create_final_species_set/output_to_input/speciesN_gigantic_T1_blastp/` - Final BLAST databases

---

## Directory Structure (relative to subproject root)

```
genomesDB/
├── README.md                           # Human documentation
├── AI_GUIDE-genomesDB.md               # THIS FILE
├── RUN-clean_and_record_subproject.sh  # Cleanup for entire subproject
├── RUN-update_upload_to_server.sh      # Update server symlinks
│
├── user_research/                      # Personal workspace
├── output_to_input/                    # Final outputs for downstream
├── upload_to_server/                   # Server sharing
│
├── STEP_1-sources/
│   ├── README.md
│   ├── AI_GUIDE-sources.md
│   ├── RUN-clean_and_record_subproject.sh
│   ├── user_research/                  # User's source data storage
│   ├── output_to_input/                # → STEP_2 inputs
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
│   ├── user_research/
│   ├── output_to_input/                # → STEP_3 inputs
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
│   ├── user_research/
│   ├── output_to_input/                # → STEP_4 inputs
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
    ├── user_research/
    ├── output_to_input/                # Final species set for downstream subprojects
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
STEP_1-sources/output_to_input/ → STEP_2-standardize_and_evaluate/INPUT_user/
                                              ↓
STEP_2-standardize_and_evaluate/output_to_input/ → STEP_3-databases/INPUT_user/
                                                            ↓
          STEP_2 + STEP_3 outputs → STEP_4-create_final_species_set
                                              ↓
                   STEP_4-create_final_species_set/output_to_input/
                                              ↓
                              (Other GIGANTIC subprojects)
```

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

All genomesDB AI sessions (from ANY step) save to ONE location:
```
research_notebook/research_ai/subproject-genomesDB/
├── logs/
└── sessions/
```

This consolidates documentation regardless of which step generated it.

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

### Diagnostic Commands

```bash
# Check phylonames dependency
ls ../phylonames/output_to_input/maps/

# Check STEP_1 outputs
ls STEP_1-sources/output_to_input/

# Check STEP_2 outputs
ls STEP_2-standardize_and_evaluate/output_to_input/

# Check STEP_3 outputs
ls STEP_3-databases/output_to_input/

# Check STEP_4 outputs (final species set)
ls STEP_4-create_final_species_set/output_to_input/
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `STEP_1-sources/workflow-*/INPUT_user/source_manifest.tsv` | List of genomes/proteomes to ingest | **YES** |
| `STEP_2-standardize_and_evaluate/workflow-*/INPUT_user/` | (from STEP_1) | No |
| `STEP_3-databases/workflow-*/INPUT_user/` | (from STEP_2) | No |
| `STEP_4-create_final_species_set/workflow-*/final_species_set_config.yaml` | Paths to STEP_2/STEP_3 outputs | **YES** |
| `STEP_4-create_final_species_set/workflow-*/INPUT_user/selected_species.txt` | Species selection (optional) | **YES** (optional) |
| `STEP_4-create_final_species_set/output_to_input/` | Final species set | No |
| `upload_to_server/upload_manifest.tsv` | What to share | **YES** |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| Starting genomesDB | "Have you run the phylonames subproject first?" |
| Before STEP_1 | "Where are your genome, GTF, and proteome files located?" |
| Manifest creation | "Are your files named with the GIGANTIC convention? (genus_species-genome-source_id-date.ext)" |
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
