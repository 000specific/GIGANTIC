# AI Guide: Source Proteome Ingestion Workflow

**For AI Assistants**: This guide covers workflow execution. For genomesDB concepts and three-step architecture, see `../../../AI_GUIDE-genomesDB.md`. For GIGANTIC overview, see `../../../../../AI_GUIDE-project.md`.

**Location**: `gigantic_project-*/subprojects/x_genomesDB/STEP_1-sources/workflow-COPYME-ingest_source_proteomes/`

---

## Key Concept: STEP_1 is USER-DRIVEN

Unlike other GIGANTIC subprojects that download or generate data automatically, **STEP_1-sources is completely user-driven**:

- Users provide proteomes from **outside GIGANTIC** (their own downloads, lab data, etc.)
- The workflow **ingests** (hard copies + symlinks) user data into GIGANTIC structure
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
- `workflow-COPYME-ingest_source_proteomes` - The template (this directory)
- `workflow-RUN_01-ingest_source_proteomes` - First run instance
- `workflow-RUN_02-ingest_source_proteomes` - Second run instance

**To create a new run:**
```bash
# From the STEP_1-sources directory
cp -r workflow-COPYME-ingest_source_proteomes workflow-RUN_01-ingest_source_proteomes
cd workflow-RUN_01-ingest_source_proteomes
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

## Workflow Directory Structure

```
workflow-COPYME-ingest_source_proteomes/
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
├── OUTPUT_pipeline/                # All outputs
│   └── 1-output/
│       ├── proteomes/              # Hard copies of source proteomes
│       └── ingestion_log.tsv       # Log of what was ingested
│
└── ai/                             # Internal - users don't touch
    ├── AI_GUIDE-ingest_sources_workflow.md  # THIS FILE
    ├── main.nf
    ├── nextflow.config
    └── scripts/
        ├── 001_ai-python-ingest_proteomes.py
        ├── 002_ai-bash-create_output_symlinks.sh
        └── 003_ai-python-write_run_log.py
```

---

## User Workflow

### Step 1: Prepare Source Proteomes

Users must have proteome files accessible somewhere (examples):
- `../user_research/species69/proteomes/` - Personal research data
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
Homo_sapiens-genome-GCF_000001405.40-20240115.gtf    # annotation
Homo_sapiens-genome-GCF_000001405.40-20240115.aa     # proteome
```

**FASTA headers must follow**:
```
>genus_species-source_gene_id-source_transcript_id-source_protein_id
```

Example: `>Homo_sapiens-ENSG00000139618-ENST00000380152-ENSP00000369497`

### Step 3: Create Source Manifest

Create `INPUT_user/source_manifest.tsv` with **4 columns**:

```tsv
genus_species	genome_path	gtf_path	proteome_path
Homo_sapiens	/data/Homo_sapiens-genome-GCF_000001405.40-20240115.fasta	/data/Homo_sapiens-genome-GCF_000001405.40-20240115.gtf	/data/Homo_sapiens-genome-GCF_000001405.40-20240115.aa
Mus_musculus	../user_research/Mus_musculus-genome-GCF_000001635.27-20240115.fasta	../user_research/Mus_musculus-genome-GCF_000001635.27-20240115.gtf	../user_research/Mus_musculus-genome-GCF_000001635.27-20240115.aa
```

**Format requirements**:
- Tab-separated (TSV)
- Header row: `genus_species`, `genome_path`, `gtf_path`, `proteome_path`
- One species per line (all 3 files)
- Paths can be absolute or relative to workflow directory

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
| `--time` | `1:00:00` | Depends on proteome count/size |
| `--cpus-per-task` | `1` | Sequential copying |

**Check job status**: `squeue -u $USER`

**View logs**: `cat slurm_logs/ingest_sources-*.log`

---

## Expected Runtime

| Scenario | Duration |
|----------|----------|
| 10 small proteomes (~10MB each) | < 1 minute |
| 50 medium proteomes (~100MB each) | 5-10 minutes |
| 100+ large proteomes | 30+ minutes |

Runtime depends primarily on file sizes and I/O speed.

---

## Output Files

### OUTPUT_pipeline/ Contents

| Directory/File | Contents |
|----------------|----------|
| `1-output/proteomes/` | Hard copies of all source proteomes |
| `1-output/ingestion_log.tsv` | Log with species, source path, timestamp |

### Downstream Location (Symlinks)

```
../../output_to_input/proteomes/
├── Homo_sapiens.fasta -> ../workflow-RUN_XX-.../OUTPUT_pipeline/1-output/proteomes/Homo_sapiens.fasta
├── Mus_musculus.fasta -> ...
└── proteome_manifest.tsv
```

**STEP_2-standardize_and_evaluate** reads from `output_to_input/proteomes/`.

---

## Verification Commands

```bash
# Did manifest parse correctly?
wc -l INPUT_user/source_manifest.tsv

# Did proteomes copy?
ls -lh OUTPUT_pipeline/1-output/proteomes/

# Check ingestion log
cat OUTPUT_pipeline/1-output/ingestion_log.tsv

# Are symlinks in place?
ls -la ../../output_to_input/proteomes/

# Check proteome manifest
cat ../../output_to_input/proteome_manifest.tsv

# Verify symlinks resolve
head ../../output_to_input/proteomes/*.fasta
```

---

## Troubleshooting

### "Source file not found"

**Cause**: Proteome path in manifest doesn't exist

**Diagnose**:
```bash
# Check the path in manifest
cat INPUT_user/source_manifest.tsv

# Verify file exists
ls -la /path/from/manifest
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

### "Manifest format error"

**Cause**: Incorrect manifest format

**Requirements**:
- Tab-separated (not spaces)
- Header row must be: `species_name	proteome_path`
- No empty lines in data section

**Check format**:
```bash
# Show tab characters
cat -A INPUT_user/source_manifest.tsv
# Tabs show as ^I
```

### "Symlinks broken"

**Cause**: Hard copy didn't complete or paths incorrect

**Diagnose**:
```bash
# Check if symlink targets exist
ls -la ../../output_to_input/proteomes/

# If broken, re-run symlink creation
bash ai/scripts/002_ai-bash-create_output_symlinks.sh
```

### NextFlow errors

**Clean and retry**:
```bash
rm -rf work .nextflow .nextflow.log*
bash RUN-ingest_sources.sh
```

---

## Script Pipeline

| Script | Does | Creates |
|--------|------|---------|
| 001 | Parses manifest, validates sources, copies proteomes | `1-output/proteomes/`, `1-output/ingestion_log.tsv` |
| 002 | Creates symlinks to output_to_input | `../../output_to_input/proteomes/`, `proteome_manifest.tsv` |
| 003 | Writes run log to research notebook | Research notebook log entry |

---

## Manual Execution (for debugging)

```bash
cd workflow-COPYME-ingest_source_proteomes

# Run scripts individually
python3 ai/scripts/001_ai-python-ingest_proteomes.py \
    --manifest INPUT_user/source_manifest.tsv \
    --output-dir OUTPUT_pipeline/1-output

bash ai/scripts/002_ai-bash-create_output_symlinks.sh

python3 ai/scripts/003_ai-python-write_run_log.py
```

---

## After Successful Run

1. **Verify output**: `ls ../../output_to_input/proteomes/`
2. **Check manifest**: `cat ../../output_to_input/proteome_manifest.tsv`
3. **Next step**: Run **STEP_2-standardize_and_evaluate** to:
   - Standardize proteome formats
   - Apply GIGANTIC phyloname-based naming convention
   - Evaluate proteome quality

---

## What's NOT in user_research/

**Important**: The `user_research/` directory at the STEP_1 level is:
- NOT part of GIGANTIC (only the README is)
- User's personal space for source data
- Can contain anything the user wants

The workflow reads FROM user_research (or anywhere else) but stores GIGANTIC-managed copies in OUTPUT_pipeline.
