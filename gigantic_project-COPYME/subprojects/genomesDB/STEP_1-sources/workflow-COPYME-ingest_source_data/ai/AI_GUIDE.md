# AI Guide: Source Data Ingestion Workflow

**For AI Assistants**: This guide covers workflow execution. For genomesDB concepts and four-step architecture, see `../../../AI_GUIDE.md`. For GIGANTIC overview, see `../../../../../AI_GUIDE.md`.

**Location**: `gigantic_project-COPYME/subprojects/genomesDB/STEP_1-sources/workflow-COPYME-ingest_source_data/`

---

## ⚠️ CRITICAL: Surface Discrepancies - No Silent Changes

**The user is managing this project - you must surface discrepancies so the user can make decisions. Silent changes undermine project management.**

- ❌ **NEVER** silently do something different than requested
- ❌ **NEVER** assume you know better and proceed without asking
- ✅ **ALWAYS** stop and explain the discrepancy
- ✅ **ALWAYS** ask for clarification before proceeding

---

## Key Concept: STEP_1 is USER-DRIVEN

Unlike other GIGANTIC subprojects that download or generate data automatically, **STEP_1-sources is completely user-driven**:

- Users provide data (proteomes, genomes, genome annotations) from **outside GIGANTIC** (their own downloads, lab data, etc.)
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
| GIGANTIC overview | `../../../../../AI_GUIDE.md` |
| genomesDB concepts, four-step architecture | `../../../AI_GUIDE.md` |
| STEP_1 sources concepts | `../../AI_GUIDE.md` |
| Running the workflow | This file |

---

## Architecture: 3 Scripts, 3 Output Directories

**Core design principle**: Each script writes directly to its own numbered output directory. No NextFlow `publishDir` magic -- scripts receive output paths as arguments and write there directly.

```
workflow-COPYME-ingest_source_data/
│
├── README.md                       # Quick start guide
├── RUN-workflow.sh           # Unified driver: bash RUN-workflow.sh
│                             # (self-submits to SLURM if execution_mode: slurm)
├── START_HERE-user_config.yaml      # Project name, ingestion options, execution_mode
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
│   │   ├── genome_annotations/
│   │   └── 2_ai-ingestion_log.tsv
│   └── 3-output/                   # Script 003 output: symlink manifest
│       └── 3_ai-symlink_manifest.tsv
│
└── ai/                             # Internal - users don't touch
    ├── AI_GUIDE.md  # THIS FILE
    ├── main.nf
    ├── nextflow.config
    └── scripts/
        ├── 001_ai-python-validate_source_manifest.py
        ├── 002_ai-python-ingest_source_data.py
        ├── 003_ai-bash-create_output_symlinks.sh
        └── 004_ai-python-write_run_log.py
```

### Script Pipeline

The workflow runs 4 scripts; three sit inside NextFlow (`ai/main.nf`)
and one (003, the symlink creator) is invoked by `RUN-workflow.sh`
**after** the NextFlow pipeline succeeds.

| Script | Where called | Does | Creates |
|---|---|---|---|
| 001 | `ai/main.nf` process `validate_source_manifest` | Reads manifest, validates all file paths exist, writes report | `1-output/1_ai-source_validation_report.tsv`, `1-output/1_ai-validation_summary.txt` |
| 002 | `ai/main.nf` process `ingest_source_data` | Hard-copies all source data into organized subdirectories | `2-output/T1_proteomes/`, `2-output/genomes/`, `2-output/genome_annotations/`, `2-output/2_ai-ingestion_log.tsv` |
| 004 | `ai/main.nf` process `write_run_log` | Writes timestamped per-run log to `ai/logs/` | `ai/logs/run_*.log` |
| 003 | `RUN-workflow.sh` (post-pipeline, bash) | Creates symlinks in `../../output_to_input/STEP_1-sources/` pointing to the `2-output/` hard copies; writes a symlink manifest | `3-output/3_ai-symlink_manifest.tsv` + symlinks under `../../output_to_input/STEP_1-sources/{T1_proteomes,genomes,genome_annotations}/` |

**Why script 003 is outside main.nf**: The symlink layer crosses
workflow boundaries (writes into the subproject-level
`output_to_input/`). Keeping it in `RUN-workflow.sh` avoids NextFlow
having to manage paths outside its work tree.

**Why this matters**: No invisible work. Every step produces visible output. A human can trace exactly what happened at each stage.

---

## User Workflow

### Step 1: Prepare Source Data

Users must have data files in the project-level `INPUT_user/genomic_resources/` subdirectories or somewhere else accessible:
- `../../../../INPUT_user/genomic_resources/genomes/` - Project-level genome files (.fasta)
- `../../../../INPUT_user/genomic_resources/proteomes/` - Project-level proteome files (.aa)
- `../../../../INPUT_user/genomic_resources/annotations/` - Project-level annotation files (.gff3/.gtf)
- `../../../../INPUT_user/genomic_resources/maps/` - Identifier mapping files (.tsv)
- `../../../../research_notebook/research_user/` - Project-root sandbox (alternative, per §1, §25)
- Any accessible path on the system

### Step 2: Ensure Files Follow GIGANTIC Naming Convention

**File names must follow**:
```
genus_species-genome_source_identifier-downloaded_date.extension
```

Examples:
```
Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.fasta   # genome
Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.gff3    # annotation
Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.aa      # proteome
```

**FASTA headers must follow**:
```
>genus_species-source_gene_id-source_transcript_id-source_protein_id
```

Example: `>Homo_sapiens-ENSG00000139618-ENST00000380152-ENSP00000369497`

### Step 3: Create Source Manifest

Create `INPUT_user/source_manifest.tsv` with **4 columns**:

```tsv
genus_species	genome_path	genome_annotation_path	proteome_path
Homo_sapiens	../../../../INPUT_user/genomic_resources/genomes/Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.fasta	../../../../INPUT_user/genomic_resources/annotations/Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.gff3	../../../../INPUT_user/genomic_resources/proteomes/Homo_sapiens-genome_ncbi_GCF_000001405.40-downloaded_20240115.aa
Mus_musculus	../../../../INPUT_user/genomic_resources/genomes/Mus_musculus-genome_ncbi_GCF_000001635.27-downloaded_20240115.fasta	../../../../INPUT_user/genomic_resources/annotations/Mus_musculus-genome_ncbi_GCF_000001635.27-downloaded_20240115.gff3	../../../../INPUT_user/genomic_resources/proteomes/Mus_musculus-genome_ncbi_GCF_000001635.27-downloaded_20240115.aa
```

**Project-level INPUT_user structure** (where source data lives):
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

**Format requirements**:
- Tab-separated (TSV)
- Header row: `genus_species`, `genome_path`, `genome_annotation_path`, `proteome_path`
- One species per line
- Paths can be absolute or relative to workflow directory
- Relative paths to project-level `INPUT_user/genomic_resources/` subdirectories are recommended
- Use "NA" for missing data types

### Step 4: Set Project Name

Edit `START_HERE-user_config.yaml`:
```yaml
project:
  name: "my_project"  # Change this
```

### Step 5: Run

**Local**:
```bash
bash RUN-workflow.sh
```

**SLURM**: Edit `START_HERE-user_config.yaml`, set `execution_mode: "slurm"` and
fill in `slurm_account` / `slurm_qos`, then:
```bash
bash RUN-workflow.sh   # self-submits to SLURM
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
ls OUTPUT_pipeline/2-output/genome_annotations/ | wc -l

# Check ingestion log
head OUTPUT_pipeline/2-output/2_ai-ingestion_log.tsv

# Are symlinks in place?
ls ../../output_to_input/STEP_1-sources/T1_proteomes/ | wc -l
ls ../../output_to_input/STEP_1-sources/genomes/ | wc -l
ls ../../output_to_input/STEP_1-sources/genome_annotations/ | wc -l

# Verify symlinks resolve
head ../../output_to_input/STEP_1-sources/T1_proteomes/*.aa | head -5

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
chmod +x RUN-workflow.sh
chmod +x ai/scripts/*.sh
```

### "Symlinks broken"

**Cause**: Data in `2-output/` was moved/deleted after symlink creation

**Diagnose**:
```bash
ls -la ../../output_to_input/STEP_1-sources/T1_proteomes/ | head -5
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
bash RUN-workflow.sh
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
2. **Check symlinks**: `ls ../../output_to_input/STEP_1-sources/T1_proteomes/`
3. **Next step**: Run **STEP_2-standardize_and_evaluate** to:
   - Standardize proteome formats with phylonames
   - Generate genome N50 statistics
   - Evaluate quality

---

## On the user sandbox (research_notebook/research_user/)

Per conventions §1, §25, the user sandbox lives at the **single
project-root location**: `gigantic_project-COPYME/research_notebook/research_user/`
(there is no per-STEP or per-subproject `research_notebook/`). Properties:

- NOT part of GIGANTIC (contents are gitignored; never version-controlled)
- User's personal space for any source data, scripts, notes
- Wild-west organization — no naming/structure rules
- Can contain anything the user wants

The workflow reads from `INPUT_user/` (which contains symlinks into the
project-root sandbox per §17, §18), not directly from the sandbox itself.
GIGANTIC-managed copies of ingested data live in `OUTPUT_pipeline/`.
