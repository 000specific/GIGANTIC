# AI Guide: STEP_1-sources (genomesDB)

**For AI Assistants**: This guide covers STEP_1 of the genomesDB subproject. For genomesDB overview and three-step architecture, see `../AI_GUIDE-genomesDB.md`. For GIGANTIC overview, see `../../../AI_GUIDE-project.md`.

**Location**: `gigantic_project-COPYME/subprojects/genomesDB/STEP_1-sources/`

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../../AI_GUIDE-project.md` |
| genomesDB concepts, three-step structure | `../AI_GUIDE-genomesDB.md` |
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
genus_species	genome_path	gtf_path	proteome_path
```

| Column | Description |
|--------|-------------|
| `genus_species` | Species identifier (e.g., `Homo_sapiens`) |
| `genome_path` | Path to genome FASTA file |
| `gtf_path` | Path to GTF/GFF annotation file |
| `proteome_path` | Path to proteome (amino acid) file |

**Example manifest**:
```tsv
genus_species	genome_path	gtf_path	proteome_path
Homo_sapiens	/data/Homo_sapiens-genome-GCF_000001405.40-20240115.fasta	/data/Homo_sapiens-genome-GCF_000001405.40-20240115.gtf	/data/Homo_sapiens-genome-GCF_000001405.40-20240115.aa
Mus_musculus	../user_research/Mus_musculus-genome-GCF_000001635.27-20240115.fasta	../user_research/Mus_musculus-genome-GCF_000001635.27-20240115.gtf	../user_research/Mus_musculus-genome-GCF_000001635.27-20240115.aa
```

### File Naming Convention

**All source files MUST follow**:

```
genus_species-genome-source_genome_project_identifier-download_date.extension
```

| Component | Description | Example |
|-----------|-------------|---------|
| `genus_species` | Species name | `Homo_sapiens` |
| `genome` | Literal string (indicates genome-level data) | `genome` |
| `source_genome_project_identifier` | Source database + assembly ID | `GCF_000001405.40` |
| `download_date` | Date in YYYYMMDD format | `20240115` |
| `extension` | File type | `.fasta`, `.gtf`, `.gff`, `.aa` |

**Extension by file type**:
- `.fasta` - Genome sequence (nucleotide)
- `.gtf` or `.gff` - Gene annotation
- `.aa` - Proteome (amino acid sequences)

**Examples**:
```
Homo_sapiens-genome-GCF_000001405.40-20240115.fasta
Homo_sapiens-genome-GCF_000001405.40-20240115.gtf
Homo_sapiens-genome-GCF_000001405.40-20240115.aa
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

All STEP_1 logs save to the genomesDB subproject location:
```
research_notebook/research_ai/subproject-genomesDB/
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `workflow-*/INPUT_user/source_manifest.tsv` | 4-column manifest | **YES** (required) |
| `workflow-*/ingest_sources_config.yaml` | Project name, options | **YES** (project name) |
| `workflow-*/RUN-*.sbatch` | SLURM account/qos | **YES** (SLURM users) |
| `output_to_input/proteomes/` | Symlinks for STEP_2 | No (auto-created) |
| `user_research/` | User's personal source data | Personal space |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| User says "add genomes to GIGANTIC" | "Do you have your genome, GTF, and proteome files ready? Are they named with the GIGANTIC convention?" |
| User asks about downloading | "STEP_1 doesn't download automatically. Do you need help preparing your source files with the correct naming convention?" |
| Files not named correctly | "GIGANTIC requires files named as: genus_species-genome-source_id-date.extension. Would you like help renaming your files?" |
| Headers not formatted | "GIGANTIC requires headers as: >genus_species-gene_id-transcript_id-protein_id. Do your FASTA files follow this format?" |
| Manifest wrong format | "The manifest needs 4 columns: genus_species, genome_path, gtf_path, proteome_path. Can you verify your manifest format?" |

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "Source file not found" | Path in manifest doesn't exist | Verify path with `ls /path/from/manifest` |
| "Manifest format error" | Wrong columns or delimiter | Must be 4 tab-separated columns |
| "Permission denied" | Can't read source or write output | Check file permissions with `ls -la` |
| "Wrong file naming" | Files not following convention | Rename to `genus_species-genome-source_id-date.ext` |
| "Wrong header format" | FASTA headers incorrect | Reformat to `>genus_species-gene_id-transcript_id-protein_id` |
| Symlinks broken | Hard copy failed or paths wrong | Re-run workflow or run script 002 manually |

---

## Helping Users Get Started

**Common scenario**: User has proteomes but they're not properly named.

**Guide them through**:

1. **Check file naming**:
   ```
   # Current: my_genome.fasta
   # Required: Homo_sapiens-genome-GCF_000001405.40-20240115.fasta
   ```

2. **Check FASTA headers**:
   ```
   # Current: >NP_001234
   # Required: >Homo_sapiens-ENSG00000139618-ENST00000380152-NP_001234
   ```

3. **Create 4-column manifest**:
   ```tsv
   genus_species	genome_path	gtf_path	proteome_path
   Homo_sapiens	/path/to/genome.fasta	/path/to/annotation.gtf	/path/to/proteome.aa
   ```

4. **Copy workflow template**:
   ```bash
   cp -r workflow-COPYME-ingest_source_proteomes workflow-RUN_01-ingest_source_proteomes
   ```

5. **Add manifest and run**:
   ```bash
   cd workflow-RUN_01-ingest_source_proteomes
   # Create INPUT_user/source_manifest.tsv
   bash RUN-ingest_sources.sh
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
└── workflow-COPYME-ingest_source_proteomes/
    ├── README.md
    ├── RUN-ingest_sources.sh
    ├── RUN-ingest_sources.sbatch
    ├── ingest_sources_config.yaml
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
            ├── 001_ai-python-ingest_proteomes.py
            ├── 002_ai-bash-create_output_symlinks.sh
            └── 003_ai-python-write_run_log.py
```
