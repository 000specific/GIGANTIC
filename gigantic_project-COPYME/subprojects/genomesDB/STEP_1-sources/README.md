# STEP_1-sources — Ingest Source Genomes/Proteomes/Annotations

<!-- ============================================================================
AI:      Claude Code | Opus 4.5 | 2026 February 12 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent subproject: [`../README.md`](../README.md) — genomesDB overview
- Parent project: [`../../../README.md`](../../../README.md)
- This STEP's AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)
- Workflow to run: [`workflow-COPYME-ingest_source_data/README.md`](workflow-COPYME-ingest_source_data/README.md)
- **Next STEP**: [`../STEP_2-standardize_and_evaluate/`](../STEP_2-standardize_and_evaluate/) — standardize + evaluate

---

## Purpose

STEP_1 of the genomesDB pipeline. **Ingests user-provided genome, proteome, and annotation files** into GIGANTIC for downstream processing.

**Part of**: genomesDB subproject (see `../README.md`)

---

## Key Concept: USER-DRIVEN Ingestion

Unlike other GIGANTIC subprojects, **STEP_1 does NOT automatically download data**.

Users:
1. Obtain proteomes from their own sources (NCBI downloads, lab data, collaborator files, etc.)
2. Store them anywhere accessible (e.g., `research_notebook/research_user/`)
3. Create a manifest listing paths to their genome, genome annotation, and proteome files
4. Run the ingestion workflow to bring them into GIGANTIC

This design gives users complete control over what enters the GIGANTIC pipeline.

---

## GIGANTIC Source Data Naming Conventions

### Source Manifest Format (REQUIRED)

The manifest is a **four-column TSV**:

```
genus_species	genome_path	genome_annotation_path	proteome_path
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

### File Naming Convention (REQUIRED)

All source files must follow this structure:

```
genus_species-genome_source_identifier-downloaded_date.extension
```

**Components**:
| Part | Description | Example |
|------|-------------|---------|
| `genus_species` | Species name | `Homo_sapiens` |
| `genome_source_identifier` | "genome" joined with source database + assembly ID | `genome_ncbi_GCF_000001405.40` |
| `downloaded_date` | downloaded_YYYYMMDD format | `downloaded_20240115` |
| `extension` | File type | `.fasta`, `.gff3`, `.aa` |

**Examples**:
```
Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.fasta    # Genome
Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.gff3    # Annotation
Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.aa      # Proteome
```

### Sequence Header Convention (REQUIRED)

FASTA headers must follow:

```
>genus_species-source_gene_id-source_transcript_id-source_protein_id
```

**Example headers**:
```
>Homo_sapiens-ENSG00000139618-ENST00000380152-ENSP00000369497
>Mus_musculus-MGI:87853-NM_007393-NP_031419
```

---

## Workflow

```bash
cd workflow-COPYME-ingest_source_data/

# 1. Create your manifest with all 4 columns
nano INPUT_user/source_manifest.tsv

# 2. Run (unified driver — local or SLURM via execution_mode YAML key, §29)
bash RUN-workflow.sh
```

See `workflow-COPYME-ingest_source_data/README.md` for detailed instructions.

---

## Outputs

- **Hard copies**: `OUTPUT_pipeline/1-output/proteomes/` (archived for reproducibility)
- **Symlinks**: `output_to_input/STEP_1-sources/T1_proteomes/` (passed to STEP_2)
- **Ingestion log**: Tracks what was ingested and when

**Passed to STEP_2 via**: `output_to_input/STEP_1-sources/T1_proteomes/`

---

## research_notebook/research_user/ Directory

The `research_notebook/research_user/` directory is the user's personal workspace (per gigantic_conventions §1, §25):
- Store source genomes/proteomes before ingestion
- Keep custom scripts, analyses, notes
- Organize however you want

**NOT part of GIGANTIC** - only the README is version-controlled.

---

## Research Notebook

Workflow run logs are saved to each workflow's `ai/logs/` directory. AI sessions are extracted project-wide to `research_notebook/research_ai/sessions/`.

---

## Dependencies

- phylonames subproject (for species naming in STEP_2)

---

## Directory Structure

```
STEP_1-sources/
├── README.md                    # This file
├── AI_GUIDE.md          # Guide for AI assistants
├── output_to_input/             # Symlinks passed to STEP_2
│   └── proteomes/               # Created by workflow
├── research_notebook/research_user/               # Your personal workspace (not part of GIGANTIC)
│   └── README.md                # Only this README is in GIGANTIC
└── workflow-COPYME-ingest_source_data/  # The ingestion workflow template
    ├── README.md
    ├── RUN-workflow.sh
    ├── START_HERE-user_config.yaml
    ├── INPUT_user/
    │   └── source_manifest.tsv  # 4-column manifest (genus_species, genome, genome_annotation, proteome)
    └── ai/
```
