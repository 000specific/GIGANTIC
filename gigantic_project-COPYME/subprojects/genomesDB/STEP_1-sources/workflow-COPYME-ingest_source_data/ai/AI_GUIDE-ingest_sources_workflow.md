# AI Guide: Source Data Ingestion Workflow

**For AI Assistants**: This guide covers workflow execution. For genomesDB concepts and three-step architecture, see `../../../AI_GUIDE-genomesDB.md`. For GIGANTIC overview, see `../../../../../AI_GUIDE-project.md`.

**Location**: `gigantic_project-COPYME/subprojects/genomesDB/STEP_1-sources/workflow-COPYME-ingest_source_data/`

---

## Key Concept: STEP_1 is USER-DRIVEN

Unlike other GIGANTIC subprojects that download or generate data automatically, **STEP_1-sources is completely user-driven**:

- Users provide data (proteomes, genomes, GFFs) from **outside GIGANTIC** (their own downloads, lab data, etc.)
- The workflow **ingests** (validates, hard copies, symlinks) user data into GIGANTIC structure
- No automatic downloads - users control what enters the pipeline

This distinction is critical when helping users with STEP_1.

---

## Workflow Naming Convention

GIGANTIC uses a **COPYME/RUN naming system** for workflows:

| Type | Naming Pattern | Description |
|------|----------------|-------------|
| **COPYME** (template) | `workflow-COPYME-[name]` | The template workflow - NOT numbered. Only ONE COPYME per workflow type. |
| **RUN** (instance) | `workflow-RUN_XX-[name]` | Numbered copies for actual runs. Each run gets its own directory. |

**Examples:**
- `workflow-COPYME-ingest_source_data` - The template (this directory)
- `workflow-RUN_01-ingest_source_data` - First run instance
- `workflow-RUN_02-ingest_source_data` - Second run instance

**To create a new run:**
```bash
# From the STEP_1-sources directory
cp -r workflow-COPYME-ingest_source_data workflow-RUN_01-ingest_source_data
cd workflow-RUN_01-ingest_source_data
# Edit config, add manifest, then run
```

**Key Principle**: COPYME stays clean as the template. All actual work happens in RUN_XX directories.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../../AI_GUIDE-project.md` |
| genomesDB concepts, three-step architecture | `../../../AI_GUIDE-genomesDB.md` |
| STEP_1 sources concepts | `../../AI_GUIDE-sources.md` |
| Running the workflow | This file |

---

## Architecture: 3 Scripts, 3 Output Directories

**Core design principle**: Each script writes directly to its own numbered output directory. No NextFlow `publishDir` magic -- scripts receive output paths as arguments and write there directly.

```
workflow-COPYME-ingest_source_data/
│
├── README.md                       # Quick start guide
├── RUN-ingest_sources.sh           # Local: bash RUN-ingest_sources.sh
├── RUN-ingest_sources.sbatch       # SLURM: sbatch RUN-ingest_sources.sbatch
├── ingest_sources_config.yaml      # Project name and ingestion options
│
├── INPUT_user/                     # User creates manifest here
│   ├── source_manifest.tsv         # User creates this (required)
│   └── source_manifest_example.tsv # Example format
│
├── OUTPUT_pipeline/
│   ├── 1-output/                   # Script 001 output: validation report
│   │   ├── 1_ai-source_validation_report.tsv
│   │   └── 1_ai-validation_summary.txt
│   ├── 2-output/                   # Script 002 output: ingested data
│   │   ├── T1_proteomes/
│   │   ├── genomes/
│   │   ├── gene_annotations/
│   │   └── 2_ai-ingestion_log.tsv
│   └── 3-output/                   # Script 003 output: symlink manifest
│       └── 3_ai-symlink_manifest.tsv
│
└── ai/                             # Internal - users don't touch
    ├── AI_GUIDE-ingest_sources_workflow.md  # THIS FILE
    ├── main.nf
    ├── nextflow.config
    └── scripts/
        ├── 001_ai-python-validate_source_manifest.py
        ├── 002_ai-python-ingest_source_data.py
        └── 003_ai-bash-create_output_symlinks.sh
```

### Script Pipeline

| Script | Does | Creates |
|--------|------|---------|
| 001 | Reads manifest, validates all file paths exist, writes report | `1-output/1_ai-source_validation_report.tsv`, `1_ai-validation_summary.txt` |
| 002 | Hard-copies all source data into organized subdirectories | `2-output/T1_proteomes/`, `genomes/`, `gene_annotations/`, `2_ai-ingestion_log.tsv` |
| 003 | Creates symlinks in `output_to_input/` pointing to `2-output/` copies | `3-output/3_ai-symlink_manifest.tsv` + actual symlinks |

**Why this matters**: No invisible work. Every step produces visible output. A human can trace exactly what happened at each stage.

---

## User Workflow

### Step 1: Prepare Source Data

Users must have data files accessible somewhere (examples):
- `../user_research/species71/output_to_input/` - Personal research data
- `/shared/lab/genomes/` - Lab shared resources
- Any accessible path on the system

### Step 2: Ensure Files Follow GIGANTIC Naming Convention

**File names must follow**:
```
genus_species-genome-source_genome_project_identifier-download_date.extension
```

Examples:
```
Homo_sapiens-genome-GCF_000001405.40-20240115.fasta   # genome
Homo_sapiens-genome-GCF_000001405.40-20240115.gff3    # annotation
Homo_sapiens-genome-GCF_000001405.40-20240115.aa      # proteome
```

**FASTA headers must follow**:
```
>genus_species-source_gene_id-source_transcript_id-source_protein_id
```

Example: `>Homo_sapiens-ENSG00000139618-ENST00000380152-ENSP00000369497`

### Step 3: Create Source Manifest

Create `INPUT_user/source_manifest.tsv` with **4 columns**:

```tsv
genus_species	genome_path	gff_path	proteome_path
Homo_sapiens	/data/Homo_sapiens-genome-GCF_000001405.40-20240115.fasta	/data/Homo_sapiens-genome-GCF_000001405.40-20240115.gff3	/data/Homo_sapiens-genome-GCF_000001405.40-20240115.aa
Mus_musculus	../user_research/Mus_musculus-genome-GCF_000001635.27-20240115.fasta	../user_research/Mus_musculus-genome-GCF_000001635.27-20240115.gff3	../user_research/Mus_musculus-genome-GCF_000001635.27-20240115.aa
```

**Format requirements**:
- Tab-separated (TSV)
- Header row: `genus_species`, `genome_path`, `gff_path`, `proteome_path`
- One species per line
- Paths can be absolute or relative to workflow directory
- Use "NA" for missing data types

### Step 4: Set Project Name

Edit `ingest_sources_config.yaml`:
```yaml
project:
  name: "my_project"  # Change this
```

### Step 5: Run

**Local**:
```bash
bash RUN-ingest_sources.sh
```

**SLURM** (edit account/qos first):
```bash
# Edit RUN-ingest_sources.sbatch:
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --qos=YOUR_QOS

sbatch RUN-ingest_sources.sbatch
```

---

## SLURM Execution Details

| Setting | Value | Notes |
|---------|-------|-------|
| `--account` | `YOUR_ACCOUNT` | **Must edit** |
| `--qos` | `YOUR_QOS` | **Must edit** |
| `--mem` | `4gb` | Usually sufficient for copying |
| `--time` | `1:00:00` | Depends on file count/size |
| `--cpus-per-task` | `1` | Sequential copying |

**Check job status**: `squeue -u $USER`

**View logs**: `cat slurm_logs/ingest_sources-*.log`

---

## Expected Runtime

| Scenario | Duration |
|----------|----------|
| 10 small files (~10MB each) | < 1 minute |
| 70 species, mixed data types | 5-15 minutes |
| 100+ species with large genomes | 30+ minutes |

Runtime depends primarily on file sizes and I/O speed.

---

## Verification Commands

```bash
# Did validation pass?
cat OUTPUT_pipeline/1-output/1_ai-validation_summary.txt

# Did data copy?
ls OUTPUT_pipeline/2-output/T1_proteomes/ | wc -l
ls OUTPUT_pipeline/2-output/genomes/ | wc -l
ls OUTPUT_pipeline/2-output/gene_annotations/ | wc -l

# Check ingestion log
head OUTPUT_pipeline/2-output/2_ai-ingestion_log.tsv

# Are symlinks in place?
ls ../../output_to_input/T1_proteomes/ | wc -l
ls ../../output_to_input/genomes/ | wc -l
ls ../../output_to_input/gene_annotations/ | wc -l

# Verify symlinks resolve
head ../../output_to_input/T1_proteomes/*.aa | head -5

# Check symlink manifest
head OUTPUT_pipeline/3-output/3_ai-symlink_manifest.tsv
```

---

## Troubleshooting

### "Source file not found" / Validation fails

**Cause**: File path in manifest doesn't exist or is inaccessible

**Diagnose**:
```bash
cat OUTPUT_pipeline/1-output/1_ai-validation_summary.txt
grep "no" OUTPUT_pipeline/1-output/1_ai-source_validation_report.tsv
```

**Solutions**:
1. Fix path in manifest
2. Ensure file is accessible (permissions)
3. Use absolute path if relative path fails

### "Permission denied on copy"

**Cause**: Can't read source file or write to output directory

**Solutions**:
```bash
# Check source file permissions
ls -la /path/to/source.fasta

# Check output directory permissions
ls -la OUTPUT_pipeline/

# Make scripts executable
chmod +x RUN-ingest_sources.sh
chmod +x ai/scripts/*.sh
```

### "Symlinks broken"

**Cause**: Data in `2-output/` was moved/deleted after symlink creation

**Diagnose**:
```bash
ls -la ../../output_to_input/T1_proteomes/ | head -5
```

**Fix**: Re-run the workflow or manually re-run script 003:
```bash
bash ai/scripts/003_ai-bash-create_output_symlinks.sh \
    OUTPUT_pipeline/2-output \
    ../../output_to_input \
    OUTPUT_pipeline/3-output
```

### NextFlow errors

**Clean and retry**:
```bash
rm -rf work .nextflow .nextflow.log*
bash RUN-ingest_sources.sh
```

---

## Manual Execution (for debugging)

```bash
cd workflow-RUN_XX-ingest_source_data

# Script 001: Validate manifest
python3 ai/scripts/001_ai-python-validate_source_manifest.py \
    --manifest INPUT_user/source_manifest.tsv \
    --output-dir OUTPUT_pipeline/1-output \
    --workflow-dir .

# Script 002: Ingest data
python3 ai/scripts/002_ai-python-ingest_source_data.py \
    --manifest INPUT_user/source_manifest.tsv \
    --output-dir OUTPUT_pipeline/2-output \
    --workflow-dir .

# Script 003: Create symlinks
bash ai/scripts/003_ai-bash-create_output_symlinks.sh \
    OUTPUT_pipeline/2-output \
    ../../output_to_input \
    OUTPUT_pipeline/3-output
```

---

## After Successful Run

1. **Verify output**: Check all three `OUTPUT_pipeline/` subdirectories
2. **Check symlinks**: `ls ../../output_to_input/T1_proteomes/`
3. **Next step**: Run **STEP_2-standardize_and_evaluate** to:
   - Standardize proteome formats with phylonames
   - Generate genome N50 statistics
   - Evaluate quality

---

## What's NOT in user_research/

**Important**: The `user_research/` directory at the STEP_1 level is:
- NOT part of GIGANTIC (only the README is)
- User's personal space for source data
- Can contain anything the user wants

The workflow reads FROM user_research (or anywhere else) but stores GIGANTIC-managed copies in OUTPUT_pipeline.
