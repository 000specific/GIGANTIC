# AI Guide: STEP_1-sources (genomesDB)

**For AI Assistants**: This guide covers STEP_1 of the genomesDB subproject. For genomesDB overview and four-step architecture, see `../AI_GUIDE-genomesDB.md`. For GIGANTIC overview, see `../../../AI_GUIDE-project.md`.

**Location**: `gigantic_project-COPYME/subprojects/genomesDB/STEP_1-sources/`

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
| GIGANTIC overview, directory structure | `../../../AI_GUIDE-project.md` |
| genomesDB concepts, four-step structure | `../AI_GUIDE-genomesDB.md` |
| STEP_1 sources concepts (this step) | This file |
| Running the workflow | `workflow-COPYME-*/ai/AI_GUIDE-ingest_sources_workflow.md` |

---

## Critical Concept: STEP_1 is USER-DRIVEN

**This is the most important thing to understand about STEP_1.**

Unlike other GIGANTIC subprojects that automatically download or generate data, **STEP_1-sources is completely user-driven**:

| Other GIGANTIC Steps | STEP_1-sources |
|---------------------|----------------|
| Automatic downloads | NO automatic downloads |
| Pipeline fetches data | User provides data |
| Workflow creates new data | Workflow ingests existing data |
| Minimal user input | User controls all inputs |

**Why this design?**
- Users have their own genome/proteome sources
- Different projects need different species
- Users may have custom or unpublished genomes
- Complete control over what enters GIGANTIC

**user_research/ directory**:
- Located at `STEP_1-sources/user_research/`
- User's personal workspace for source data
- NOT part of GIGANTIC (only README is version-controlled)
- Can contain anything: raw downloads, scripts, notes, analyses
- Workflow reads FROM here but doesn't manage it

---

## GIGANTIC Source Data Naming Conventions

### Source Manifest Format (4 columns)

**CRITICAL**: The manifest must have exactly 4 tab-separated columns:

```
genus_species	genome_path	genome_annotation_path	proteome_path
```

| Column | Description |
|--------|-------------|
| `genus_species` | Species identifier (e.g., `Homo_sapiens`) |
| `genome_path` | Path to genome FASTA file |
| `genome_annotation_path` | Path to genome annotation file (GFF3 or GTF) |
| `proteome_path` | Path to proteome (amino acid) file |

**Example manifest** (using relative paths to project-level INPUT_user):
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

**All source files MUST follow**:

```
genus_species-genome_source_identifier-downloaded_date.extension
```

| Component | Description | Example |
|-----------|-------------|---------|
| `genus_species` | Species name | `Homo_sapiens` |
| `genome_source_identifier` | "genome" joined with source database + assembly ID | `genome_ncbi_GCF_000001405.40` |
| `downloaded_date` | downloaded_YYYYMMDD format | `downloaded_20240115` |
| `extension` | File type | `.fasta`, `.gff3`, `.aa` |

**Extension by file type**:
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

**FASTA headers MUST follow**:

```
>genus_species-source_gene_id-source_transcript_id-source_protein_id
```

| Component | Description | Example |
|-----------|-------------|---------|
| `genus_species` | Must match filename | `Homo_sapiens` |
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
- Species identifiable from any sequence
- Full provenance: gene → transcript → protein
- Enables tracing to source databases
- Consistent across all GIGANTIC

---

## What This Step Does

**Purpose**: Ingest user-provided proteome files into GIGANTIC structure.

**Process**:
1. User provides 4-column manifest with genome, GTF, proteome paths
2. Workflow validates all sources exist
3. Workflow hard-copies proteomes to OUTPUT_pipeline (archival)
4. Workflow creates symlinks in output_to_input (for STEP_2)

**Outputs**:
- Archived proteome copies in `OUTPUT_pipeline/1-output/proteomes/`
- Symlinks in `output_to_input/proteomes/` passed to STEP_2-standardize_and_evaluate

---

## Path Depth

From this step directory, project root is at `../../../`:

| Location | Relative path to project root |
|----------|-------------------------------|
| `STEP_1-sources/` | `../../../` |
| `STEP_1-sources/workflow-COPYME-*/` | `../../../../` |

---

## Research Notebook Location

Workflow run logs are saved to each workflow's `ai/logs/` directory. AI sessions are extracted project-wide to `research_notebook/research_ai/sessions/`.

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `workflow-*/INPUT_user/source_manifest.tsv` | 4-column manifest | **YES** (required) |
| `workflow-*/START_HERE-user_config.yaml` | Project name, options | **YES** (project name) |
| `workflow-*/RUN-*.sbatch` | SLURM account/qos | **YES** (SLURM users) |
| `output_to_input/proteomes/` | Symlinks for STEP_2 | No (auto-created) |
| `user_research/` | User's personal source data | Personal space |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| User says "add genomes to GIGANTIC" | "Do you have your genome, GTF, and proteome files ready? Are they named with the GIGANTIC convention?" |
| User asks about downloading | "STEP_1 doesn't download automatically. Do you need help preparing your source files with the correct naming convention?" |
| Files not named correctly | "GIGANTIC requires files named as: genus_species-genome_source_identifier-downloaded_date.extension. Would you like help renaming your files?" |
| Headers not formatted | "GIGANTIC requires headers as: >genus_species-gene_id-transcript_id-protein_id. Do your FASTA files follow this format?" |
| Manifest wrong format | "The manifest needs 4 columns: genus_species, genome_path, genome_annotation_path, proteome_path. Can you verify your manifest format?" |

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "Source file not found" | Path in manifest doesn't exist | Verify path with `ls /path/from/manifest` |
| "Manifest format error" | Wrong columns or delimiter | Must be 4 tab-separated columns |
| "Permission denied" | Can't read source or write output | Check file permissions with `ls -la` |
| "Wrong file naming" | Files not following convention | Rename to `genus_species-genome_source_identifier-downloaded_date.ext` |
| "Wrong header format" | FASTA headers incorrect | Reformat to `>genus_species-gene_id-transcript_id-protein_id` |
| Symlinks broken | Hard copy failed or paths wrong | Re-run workflow or run script 002 manually |

---

## Helping Users Get Started

**Common scenario**: User has proteomes but they're not properly named.

**Guide them through**:

1. **Check file naming**:
   ```
   # Current: my_genome.fasta
   # Required: Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.fasta
   ```

2. **Check FASTA headers**:
   ```
   # Current: >NP_001234
   # Required: >Homo_sapiens-ENSG00000139618-ENST00000380152-NP_001234
   ```

3. **Create 4-column manifest** (paths point to project-level `INPUT_user/genomic_resources/` subdirectories):
   ```tsv
   genus_species	genome_path	genome_annotation_path	proteome_path
   Homo_sapiens	../../../../INPUT_user/genomic_resources/genomes/Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.fasta	../../../../INPUT_user/genomic_resources/annotations/Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.gff3	../../../../INPUT_user/genomic_resources/proteomes/Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.aa
   ```

4. **Copy workflow template**:
   ```bash
   cp -r workflow-COPYME-ingest_source_data workflow-RUN_01-ingest_source_data
   ```

5. **Add manifest and run**:
   ```bash
   cd workflow-RUN_01-ingest_source_data
   # Create INPUT_user/source_manifest.tsv
   bash RUN-workflow.sh
   ```

**After ingestion**: Guide to STEP_2-standardize_and_evaluate for format standardization and phyloname application.

---

## Directory Structure

```
STEP_1-sources/
├── README.md                    # Human-readable overview
├── AI_GUIDE-sources.md          # THIS FILE
├── output_to_input/             # Symlinks passed to STEP_2
│   └── proteomes/               # Created by workflow
│       ├── Species1.aa -> ...
│       └── proteome_manifest.tsv
├── user_research/               # User's personal workspace
│   └── README.md                # Only this is part of GIGANTIC
└── workflow-COPYME-ingest_source_data/
    ├── README.md
    ├── RUN-workflow.sh
    ├── RUN-workflow.sbatch
    ├── START_HERE-user_config.yaml
    ├── INPUT_user/
    │   ├── source_manifest.tsv      # User creates this (4 columns)
    │   └── source_manifest_example.tsv
    ├── OUTPUT_pipeline/
    │   └── 1-output/
    │       ├── proteomes/           # Hard copies
    │       └── ingestion_log.tsv
    └── ai/
        ├── AI_GUIDE-ingest_sources_workflow.md
        ├── main.nf
        ├── nextflow.config
        └── scripts/
            ├── 001_ai-python-validate_source_manifest.py
            ├── 002_ai-python-ingest_source_data.py
            └── 003_ai-bash-create_output_symlinks.sh
```
