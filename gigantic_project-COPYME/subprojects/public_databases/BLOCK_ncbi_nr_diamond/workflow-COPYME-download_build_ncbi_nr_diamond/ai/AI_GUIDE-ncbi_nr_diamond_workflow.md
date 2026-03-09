# AI Guide: NCBI nr DIAMOND Database Workflow

**For AI Assistants**: This guide covers workflow execution. For BLOCK overview, see `../../AI_GUIDE-ncbi_nr_diamond.md`. For GIGANTIC overview, see `../../../../AI_GUIDE-project.md`.

**Location**: `gigantic_project-*/subprojects/public_databases/BLOCK_ncbi_nr_diamond/workflow-COPYME-download_build_ncbi_nr_diamond/`

---

## CRITICAL: Surface Discrepancies - No Silent Changes

**The user is managing this project - you must surface discrepancies so the user can make decisions. Silent changes undermine project management.**

- NEVER silently do something different than requested
- NEVER assume you know better and proceed without asking
- ALWAYS stop and explain the discrepancy
- ALWAYS ask for clarification before proceeding

---

## Workflow Naming Convention

| Type | Naming Pattern | Description |
|------|----------------|-------------|
| **COPYME** (template) | `workflow-COPYME-[name]` | The template workflow - NOT numbered. Only ONE COPYME per workflow type. |
| **RUN** (instance) | `workflow-RUN_XX-[name]` | Numbered copies for actual runs. Each run gets its own directory. |

**To create a new run:**
```bash
# From the BLOCK directory (BLOCK_ncbi_nr_diamond/)
cp -r workflow-COPYME-download_build_ncbi_nr_diamond workflow-RUN_01-download_build_ncbi_nr_diamond
cd workflow-RUN_01-download_build_ncbi_nr_diamond
# Edit config, then run
```

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../AI_GUIDE-project.md` |
| BLOCK overview | `../../AI_GUIDE-ncbi_nr_diamond.md` |
| Running the workflow | This file |

---

## Workflow Directory Structure

```
workflow-COPYME-download_build_ncbi_nr_diamond/
|
├── README.md                        # Quick start guide
├── RUN-workflow.sh                  # Local: bash RUN-workflow.sh
├── RUN-workflow.sbatch              # SLURM: sbatch RUN-workflow.sbatch
├── START_HERE-user_config.yaml      # Project name and settings
|
├── INPUT_user/                      # (empty - no user input files needed)
|
├── OUTPUT_pipeline/                 # All outputs
│   ├── 1-output/                    # Downloaded nr.gz
│   ├── 2-output/                    # DIAMOND database (nr.dmnd)
│   ├── 3-output/                    # Validation report
│   └── 4-output/                    # Run log
|
└── ai/                              # Internal - users don't touch
    ├── AI_GUIDE-ncbi_nr_diamond_workflow.md  # THIS FILE
    ├── main.nf
    ├── nextflow.config
    ├── logs/                        # NextFlow logs
    └── scripts/
        ├── 001_ai-bash-download_ncbi_nr.sh
        ├── 002_ai-bash-build_diamond_database.sh
        ├── 003_ai-python-validate_database.py
        └── 004_ai-python-write_run_log.py
```

---

## User Workflow

### Step 1: Review Configuration

Edit `START_HERE-user_config.yaml`:
```yaml
project:
  name: "my_project"  # Change this

diamond:
  threads: 15  # Match your SLURM --cpus-per-task
```

### Step 2: Run

**Local**:
```bash
bash RUN-workflow.sh
```

**SLURM** (edit account/qos first):
```bash
sbatch RUN-workflow.sbatch
```

---

## SLURM Execution Details

| Setting | Value | Notes |
|---------|-------|-------|
| `--account` | `moroz` | **Edit for your cluster** |
| `--qos` | `moroz` | **Edit for your cluster** |
| `--mem` | `100gb` | Required for DIAMOND makedb on nr |
| `--time` | `48:00:00` | Download + build can take many hours |
| `--cpus-per-task` | `15` | Threads for DIAMOND makedb |

**Check job status**: `squeue -u $USER`

**View logs**: `cat slurm_logs/ncbi_nr_diamond-*.log`

---

## Expected Runtime

| Step | Duration |
|------|----------|
| Download nr.gz (~100 GB) | 2-12 hours (network dependent) |
| DIAMOND makedb | 1-4 hours (CPU/memory dependent) |
| Validation | < 1 minute |
| Total | 3-16 hours typical |

---

## Script Pipeline

| Script | Does | Creates |
|--------|------|---------|
| 001 | Downloads NCBI nr FASTA | `1-output/nr.gz` |
| 002 | Builds DIAMOND database | `2-output/nr.dmnd` |
| 003 | Validates database | `3-output/validation_report.txt` |
| 004 | Writes run log | `4-output/run_log.txt` |

---

## Output Files

### OUTPUT_pipeline/ Contents

| Directory | Contents |
|-----------|----------|
| `1-output/` | Downloaded nr.gz (~100 GB) |
| `2-output/` | DIAMOND database nr.dmnd (~150 GB) |
| `3-output/` | Validation report (sequence count, file size) |
| `4-output/` | Timestamped run log |

### Downstream Location

```
../../output_to_input/BLOCK_ncbi_nr_diamond/nr.dmnd
```

This is what other subprojects reference for DIAMOND searches.

---

## Verification Commands

```bash
# Did download complete?
ls -lh OUTPUT_pipeline/1-output/nr.gz

# Did DIAMOND database build?
ls -lh OUTPUT_pipeline/2-output/nr.dmnd

# Check database info
diamond dbinfo -d OUTPUT_pipeline/2-output/nr.dmnd

# Did validation pass?
cat OUTPUT_pipeline/3-output/validation_report.txt

# Is symlink in place?
ls -la ../../output_to_input/BLOCK_ncbi_nr_diamond/

# Check disk space
df -h .
```

---

## Troubleshooting

### Download fails or stalls

**Causes**: Network issue, NCBI maintenance, firewall

**Solutions**:
```bash
# wget -c resumes partial downloads - just re-run
bash RUN-workflow.sh

# Test connectivity
curl -I https://ftp.ncbi.nlm.nih.gov/blast/db/FASTA/nr.gz
```

### Out of disk space

**Cause**: nr.gz (~100 GB) + nr.dmnd (~150 GB) need ~300 GB

**Solution**: Free up space or use a different filesystem with more capacity.

### DIAMOND makedb killed (OOM)

**Cause**: Insufficient memory for building database from nr

**Solution**: Increase `--mem` in `RUN-workflow.sbatch` to at least 100 GB.

### Validation reports 0 sequences

**Cause**: Corrupted or incomplete download

**Solution**:
```bash
rm OUTPUT_pipeline/1-output/nr.gz
bash RUN-workflow.sh  # Re-download fresh
```

### NextFlow errors

**Clean and retry**:
```bash
rm -rf work .nextflow .nextflow.log*
bash RUN-workflow.sh
```

### Permission denied

**Solution**:
```bash
chmod +x RUN-workflow.sh
chmod +x ai/scripts/*.sh
```

---

## Manual Execution (for debugging)

```bash
cd workflow-COPYME-download_build_ncbi_nr_diamond

# Run scripts individually
bash ai/scripts/001_ai-bash-download_ncbi_nr.sh --output-dir OUTPUT_pipeline/1-output --url "https://ftp.ncbi.nlm.nih.gov/blast/db/FASTA/nr.gz"
bash ai/scripts/002_ai-bash-build_diamond_database.sh --input-file OUTPUT_pipeline/1-output/nr.gz --output-dir OUTPUT_pipeline/2-output --threads 15
python3 ai/scripts/003_ai-python-validate_database.py --database-path OUTPUT_pipeline/2-output/nr.dmnd --output-dir OUTPUT_pipeline/3-output
python3 ai/scripts/004_ai-python-write_run_log.py --validation-report OUTPUT_pipeline/3-output/validation_report.txt --output-dir OUTPUT_pipeline/4-output
```
