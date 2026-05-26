# AI Guide: STEP_3 Workflow - Build GIGANTIC GenomesDB BLAST Databases

**For AI Assistants**: Read the subproject guide (`../../AI_GUIDE.md`) first for STEP_3 concepts and troubleshooting. This guide focuses on running the workflow.

**Location**: `gigantic_project-COPYME/subprojects/genomesDB/STEP_3-databases/workflow-COPYME-build_gigantic_genomesDB/ai/`

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../../../../AI_GUIDE.md` |
| genomesDB concepts, pipeline architecture | `../../../AI_GUIDE.md` |
| STEP_3 concepts, troubleshooting | `../../AI_GUIDE.md` |
| Running the workflow (this guide) | This file |

---

## Step-by-Step Execution

### 1. Copy the template

```bash
cd STEP_3-databases/
cp -r workflow-COPYME-build_gigantic_genomesDB workflow-RUN_01-build_gigantic_genomesDB
cd workflow-RUN_01-build_gigantic_genomesDB
```

### 2. Configure (optional)

Edit `START_HERE-user_config.yaml` if needed:

```yaml
inputs:
  # Cleaned proteomes from STEP_2 (via subproject output_to_input/)
  # STEP_3 builds a BLAST DB for every .aa file in this directory; no filtering.
  proteomes_dir: "../../output_to_input/STEP_2-standardize_and_evaluate/gigantic_proteomes_cleaned"

blast:
  # Name for the BLAST database directory
  database_name: "gigantic-T1-blastp"

  # Number of parallel makeblastdb jobs (4-8 recommended)
  parallel_jobs: 4
```

Default paths work if STEP_2 has been run and its `RUN-workflow.sh` created the `output_to_input/STEP_2-standardize_and_evaluate/gigantic_proteomes_cleaned/` symlink.

### 3. Ensure prerequisites are met

- STEP_2 must be complete (proteomes cleaned and published to `output_to_input/STEP_2-standardize_and_evaluate/gigantic_proteomes_cleaned/`)
- `aiG-genomesDB` conda environment must be available (or BLAST+, NextFlow, Python3 in PATH)
- **No species selection happens here** — STEP_3 builds BLAST DBs for every proteome from STEP_2. Filtering happens in STEP_4.

### 4. Run the workflow

**Local:**
```bash
bash RUN-workflow.sh
```

**SLURM**: Edit `START_HERE-user_config.yaml`, set `execution_mode: "slurm"` and
fill in `slurm_account` / `slurm_qos`, then:
```bash
bash RUN-workflow.sh   # self-submits to SLURM
```

### 5. Verify outputs

See verification commands below.

---

## Script Pipeline (2 scripts)

| Order | Script | Purpose | Input | Output |
|---|---|---|---|---|
| 1 | `001_ai-python-build_per_genome_blastdbs.py` | Build per-genome BLAST protein databases for every .aa proteome from STEP_2 (no filtering) | `proteomes_dir` (`output_to_input/STEP_2-standardize_and_evaluate/gigantic_proteomes_cleaned/`) | `1-output/gigantic-T1-blastp/` (per-genome BLAST databases) + `1-output/1_ai-makeblastdb_commands.sh` |
| 2 | `002_ai-python-write_run_log.py` | Write per-run audit log | n/a | `ai/logs/run_*.log` |

**Pipeline flow**: Script 001 reads every `.aa` in the cleaned-proteomes
directory and builds one BLAST database per species; script 002 writes
an audit log. There is no separate "filter species manifest" step — earlier
docs claimed one, but STEP_3 does not filter. Species selection is the
user's call in STEP_4.

---

## Verification Commands

After the workflow completes, verify outputs:

### Check BLAST databases

```bash
# Count BLAST database sets (each species has multiple files alongside the .aa)
ls OUTPUT_pipeline/1-output/gigantic-T1-blastp/*.aa | wc -l

# Verify BLAST database files exist
ls OUTPUT_pipeline/1-output/gigantic-T1-blastp/ | head -20

# View makeblastdb commands log
cat OUTPUT_pipeline/1-output/1_ai-makeblastdb_commands.sh
```

### Check output_to_input (for downstream subprojects)

```bash
# BLAST databases accessible to other subprojects
ls ../../output_to_input/STEP_3-databases/gigantic-T1-blastp/ | head

# Verify symlink target is correct
readlink ../../output_to_input/STEP_3-databases/gigantic-T1-blastp
```

### Check logs

```bash
# Build BLAST databases log
cat OUTPUT_pipeline/1-output/1_ai-log-build_per_genome_blastdbs.log

# Per-run audit log (script 002)
ls -ltr ai/logs/ | tail -3
```

---

## Common Errors

| Error | Cause | Solution |
|---|---|---|
| "Proteomes directory not found" | STEP_2 outputs not published | Run STEP_2 first; verify `../../output_to_input/STEP_2-standardize_and_evaluate/gigantic_proteomes_cleaned/` exists |
| "Empty proteomes directory" | STEP_2 ran but produced no cleaned proteomes | Check STEP_2 logs; re-run STEP_2 if needed |
| "makeblastdb not found" | BLAST+ not installed or not in PATH | Activate conda environment: `module load conda && conda activate aiG-genomesDB` |
| Pipeline cached stale results | Old `work/` directory from previous run | Remove NextFlow cache: `rm -rf work .nextflow .nextflow.log*` and re-run |

---

## NextFlow Details

- **Pipeline definition**: `ai/main.nf`
- **Configuration**: `ai/nextflow.config`
- **Work directory**: `work/` (auto-created by NextFlow, safe to delete after success)
- **Resume**: Use `nextflow run ai/main.nf -resume` to resume a failed run

**Clearing cache** (if scripts were updated):
```bash
rm -rf work .nextflow .nextflow.log*
bash RUN-workflow.sh
```

---

## SLURM Settings

| Setting | Value | Notes |
|---------|-------|-------|
| `--account` | `YOUR_ACCOUNT` | **Must edit** for your cluster |
| `--qos` | `YOUR_QOS` | **Must edit** for your cluster |
| `--cpus-per-task` | 8 | Supports parallel makeblastdb jobs |
| `--mem` | 60gb | Sufficient for large proteome databases |
| `--time` | 2:00:00 | Adjust based on species count |

---

## What Happens After STEP_3

Once STEP_3 completes, the BLAST databases are accessible at:

```
genomesDB/output_to_input/STEP_3-databases/
└── gigantic-T1-blastp/    # Per-genome BLAST protein databases
```

Proceed to **STEP_4-create_final_species_set** to select and copy the final species set (proteomes + BLAST databases) for downstream subprojects.

Downstream subprojects that use BLAST databases:
- **trees_gene_families** (homolog discovery via BLAST searches)
- **trees_gene_groups** (homolog discovery)
