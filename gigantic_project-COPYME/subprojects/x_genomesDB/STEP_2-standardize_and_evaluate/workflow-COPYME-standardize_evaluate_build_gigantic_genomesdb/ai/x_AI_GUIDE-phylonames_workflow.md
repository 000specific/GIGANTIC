# AI Guide: Phylonames Workflow

**For AI Assistants**: This guide covers workflow execution. For concepts (numbered clades, user phylonames), see `../../AI_GUIDE-phylonames.md`. For GIGANTIC overview, see `../../../../AI_GUIDE-project.md`.

**Location**: `gigantic_project-*/subprojects/phylonames/workflow-COPYME-generate_phylonames/`

---

## Workflow Naming Convention

GIGANTIC uses a **COPYME/RUN naming system** for workflows:

| Type | Naming Pattern | Description |
|------|----------------|-------------|
| **COPYME** (template) | `workflow-COPYME-[name]` | The template workflow - NOT numbered. Only ONE COPYME per workflow type. |
| **RUN** (instance) | `workflow-RUN_XX-[name]` | Numbered copies for actual runs. Each run gets its own directory. |

**Examples:**
- `workflow-COPYME-generate_phylonames` - The template (this directory)
- `workflow-RUN_01-generate_phylonames` - First run instance
- `workflow-RUN_02-generate_phylonames` - Second run instance

**To create a new run:**
```bash
# From the subproject directory (phylonames/)
cp -r workflow-COPYME-generate_phylonames workflow-RUN_01-generate_phylonames
cd workflow-RUN_01-generate_phylonames
# Edit config, add inputs, then run
```

**Key Principle**: COPYME stays clean as the template. All actual work happens in RUN_XX directories.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../AI_GUIDE-project.md` |
| Phylonames concepts | `../../AI_GUIDE-phylonames.md` |
| Running the workflow | This file |

---

## Workflow Directory Structure

```
workflow-COPYME-generate_phylonames/
│
├── README.md                    # Quick start guide
├── RUN-phylonames.sh            # Local: bash RUN-phylonames.sh
├── RUN-phylonames.sbatch        # SLURM: sbatch RUN-phylonames.sbatch
├── phylonames_config.yaml       # Project name and options
│
├── INPUT_user/                  # Copied from INPUT_gigantic/ at runtime
│   ├── species_list.txt         # Species to process
│   └── user_phylonames.tsv      # (Optional) Custom phylonames
│
├── OUTPUT_pipeline/             # All outputs
│   ├── 1-output/                # NCBI taxonomy database
│   ├── 2-output/                # Master phylonames for all NCBI species
│   ├── 3-output/                # Project-specific mapping
│   ├── 4-output/                # (Optional) User phylonames applied
│   └── 5-output/                # Taxonomy summary (MD and HTML)
│
└── ai/                          # Internal - users don't touch
    ├── AI_GUIDE-phylonames_workflow.md  # THIS FILE
    ├── main.nf
    ├── nextflow.config
    └── scripts/
        ├── 001_ai-bash-download_ncbi_taxonomy.sh
        ├── 002_ai-python-generate_phylonames.py
        ├── 003_ai-python-create_species_mapping.py
        ├── 004_ai-python-apply_user_phylonames.py
        ├── 005_ai-python-generate_taxonomy_summary.py
        └── 006_ai-python-write_run_log.py
```

---

## User Workflow

### Step 1: Add Species

**Recommended**: Edit project-wide list (single source of truth):
```bash
# From workflow directory
nano ../../../../INPUT_gigantic/species_list.txt
```

**Alternative**: Edit workflow-specific copy:
```bash
nano INPUT_user/species_list.txt
```

**Format**:
```
# Comments start with #
Homo_sapiens
Aplysia_californica
Octopus_bimaculoides
```

### Step 2: Set Project Name

Edit `phylonames_config.yaml`:
```yaml
project:
  name: "my_project"  # Change this
```

### Step 3: Run

**Local**:
```bash
bash RUN-phylonames.sh
```

**SLURM** (edit account/qos first):
```bash
# Edit RUN-phylonames.sbatch:
#SBATCH --account=YOUR_ACCOUNT
#SBATCH --qos=YOUR_QOS

sbatch RUN-phylonames.sbatch
```

---

## SLURM Execution Details

| Setting | Value | Notes |
|---------|-------|-------|
| `--account` | `YOUR_ACCOUNT` | **Must edit** |
| `--qos` | `YOUR_QOS` | **Must edit** |
| `--mem` | `8gb` | Usually sufficient |
| `--time` | `2:00:00` | First run ~15min, subsequent <1min |
| `--cpus-per-task` | `2` | Minimal parallelism needed |

**Check job status**: `squeue -u $USER`

**View logs**: `cat slurm_logs/phylonames-*.log`

---

## Expected Runtime

| Scenario | Duration |
|----------|----------|
| First run (download + generate) | ~15 minutes |
| Subsequent runs (mapping only) | < 1 minute |

---

## Output Files

### OUTPUT_pipeline/ Contents

| Directory | Contents |
|-----------|----------|
| `1-output/` | NCBI taxonomy database (~2GB) |
| `2-output/phylonames` | All NCBI phylonames (~2.5M lines) |
| `2-output/phylonames_taxonid` | All phylonames with taxon IDs |
| `2-output/map-phyloname_X_ncbi_taxonomy_info.tsv` | Complete NCBI mapping |
| `3-output/[project]_map-genus_species_X_phylonames.tsv` | **Your mapping** |
| `4-output/` | (Optional) User phylonames applied |
| `5-output/[project]_taxonomy_summary.md` | Taxonomy summary (Markdown) |
| `5-output/[project]_taxonomy_summary.html` | Taxonomy summary (HTML) |

### Downstream Location

```
../../output_to_input/maps/[project]_map-genus_species_X_phylonames.tsv
```

This symlink is what other subprojects read.

---

## Verification Commands

```bash
# Did species list copy from INPUT_gigantic?
head INPUT_user/species_list.txt

# Did NCBI download complete?
ls -lh OUTPUT_pipeline/1-output/

# Did master phylonames generate?
wc -l OUTPUT_pipeline/2-output/phylonames

# Did project mapping create?
head OUTPUT_pipeline/3-output/*_map-genus_species_X_phylonames.tsv

# Did taxonomy summary generate?
ls OUTPUT_pipeline/5-output/

# Is symlink in place?
ls -la ../../output_to_input/maps/
```

---

## Troubleshooting

### "Species not found"

**Check**:
1. Spelling: `Homo_sapiens` not `Homo sapeins`
2. Format: Use underscore, not space
3. Name: NCBI may use different name (check ncbi.nlm.nih.gov/taxonomy)

**Diagnose**:
```bash
# Show your species list
cat INPUT_user/species_list.txt

# Count lines in output (should match input species count)
wc -l OUTPUT_pipeline/3-output/*_map*.tsv
```

### "Download failed"

**Causes**: Network issue, firewall, NCBI maintenance

**Solutions**:
```bash
# Test connectivity
ping google.com
curl -I ftp.ncbi.nlm.nih.gov

# Try again (often resolves itself)
bash RUN-phylonames.sh
```

### "No database directory"

**Cause**: Script 001 didn't complete

**Solution**: Run download first:
```bash
bash ai/scripts/001_ai-bash-download_ncbi_taxonomy.sh
```

### "Permission denied"

**Solution**:
```bash
chmod +x RUN-phylonames.sh
chmod +x ai/scripts/*.sh
```

### NextFlow errors

**Clean and retry**:
```bash
rm -rf work .nextflow .nextflow.log*
bash RUN-phylonames.sh
```

---

## Script Pipeline

| Script | Does | Creates |
|--------|------|---------|
| 001 | Downloads NCBI taxonomy | `1-output/database-ncbi_taxonomy_*` |
| 002 | Generates ALL phylonames | `2-output/phylonames`, `2-output/phylonames_taxonid` |
| 003 | Creates project mapping | `3-output/[project]_map-*.tsv` |
| 004 | (Optional) Applies user overrides | `4-output/*.tsv` |
| 005 | Generates taxonomy summary | `5-output/[project]_taxonomy_summary.md/.html` |
| 006 | Writes run log | Research notebook log entry |

---

## Manual Execution (for debugging)

```bash
cd workflow-COPYME-generate_phylonames

# Run scripts individually
bash ai/scripts/001_ai-bash-download_ncbi_taxonomy.sh
python3 ai/scripts/002_ai-python-generate_phylonames.py
python3 ai/scripts/003_ai-python-create_species_mapping.py \
    --species-list INPUT_user/species_list.txt \
    --output OUTPUT_pipeline/3-output/my_project_map.tsv
```

---

## After Successful Run

1. **Verify output**: `head ../../output_to_input/maps/*_map*.tsv`
2. **Next subproject**: Guide user to `genomesDB`
3. **Keep results**: Other subprojects read from `output_to_input/maps/`
