# STEP_1-sources - Ingest Source Proteomes

**AI**: Claude Code | Opus 4.5 | 2026 February 12
**Human**: Eric Edsinger

---

## Purpose

STEP_1 of the genomesDB pipeline. **Ingests user-provided proteome files** into GIGANTIC for downstream processing.

**Part of**: genomesDB subproject (see `../README.md`)

---

## Key Concept: USER-DRIVEN Ingestion

Unlike other GIGANTIC subprojects, **STEP_1 does NOT automatically download data**.

Users:
1. Obtain proteomes from their own sources (NCBI downloads, lab data, collaborator files, etc.)
2. Store them anywhere accessible (e.g., `user_research/`)
3. Create a manifest listing paths to their genome, GTF, and proteome files
4. Run the ingestion workflow to bring them into GIGANTIC

This design gives users complete control over what enters the GIGANTIC pipeline.

---

## GIGANTIC Source Data Naming Conventions

### Source Manifest Format (REQUIRED)

The manifest is a **four-column TSV**:

```
genus_species	genome_path	gtf_path	proteome_path
```

**Example**:
```tsv
genus_species	genome_path	gtf_path	proteome_path
Homo_sapiens	/data/Homo_sapiens-genome-GCF_000001405.40-20240115.fasta	/data/Homo_sapiens-genome-GCF_000001405.40-20240115.gtf	/data/Homo_sapiens-genome-GCF_000001405.40-20240115.aa
Mus_musculus	../user_research/Mus_musculus-genome-GCF_000001635.27-20240115.fasta	../user_research/Mus_musculus-genome-GCF_000001635.27-20240115.gtf	../user_research/Mus_musculus-genome-GCF_000001635.27-20240115.aa
```

### File Naming Convention (REQUIRED)

All source files must follow this structure:

```
genus_species-genome-source_genome_project_identifier-download_date.extension
```

**Components**:
| Part | Description | Example |
|------|-------------|---------|
| `genus_species` | Species name | `Homo_sapiens` |
| `genome` | Literal string | `genome` |
| `source_genome_project_identifier` | Source ID | `GCF_000001405.40` |
| `download_date` | YYYYMMDD | `20240115` |
| `extension` | File type | `.fasta`, `.gtf`, `.aa` |

**Examples**:
```
Homo_sapiens-genome-GCF_000001405.40-20240115.fasta    # Genome
Homo_sapiens-genome-GCF_000001405.40-20240115.gtf      # Annotation
Homo_sapiens-genome-GCF_000001405.40-20240115.aa       # Proteome
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

# 2. Local execution:
bash RUN-workflow.sh

# 3. Or SLURM (edit account/qos first):
sbatch RUN-workflow.sbatch
```

See `workflow-COPYME-ingest_source_data/README.md` for detailed instructions.

---

## Outputs

- **Hard copies**: `OUTPUT_pipeline/1-output/proteomes/` (archived for reproducibility)
- **Symlinks**: `output_to_input/proteomes/` (passed to STEP_2)
- **Ingestion log**: Tracks what was ingested and when

**Passed to STEP_2 via**: `output_to_input/proteomes/`

---

## user_research/ Directory

The `user_research/` directory is your personal workspace:
- Store source genomes/proteomes before ingestion
- Keep custom scripts, analyses, notes
- Organize however you want

**NOT part of GIGANTIC** - only the README is version-controlled.

---

## Research Notebook

All logs and sessions saved to:
```
research_notebook/research_ai/subproject-genomesDB/
```

---

## Dependencies

- phylonames subproject (for species naming in STEP_2)

---

## Directory Structure

```
STEP_1-sources/
├── README.md                    # This file
├── AI_GUIDE-sources.md          # Guide for AI assistants
├── output_to_input/             # Symlinks passed to STEP_2
│   └── proteomes/               # Created by workflow
├── user_research/               # Your personal workspace (not part of GIGANTIC)
│   └── README.md                # Only this README is in GIGANTIC
└── workflow-COPYME-ingest_source_data/  # The ingestion workflow template
    ├── README.md
    ├── RUN-workflow.sh
    ├── RUN-workflow.sbatch
    ├── ingest_sources_config.yaml
    ├── INPUT_user/
    │   └── source_manifest.tsv  # 4-column manifest (genus_species, genome, gtf, proteome)
    └── ai/
```
