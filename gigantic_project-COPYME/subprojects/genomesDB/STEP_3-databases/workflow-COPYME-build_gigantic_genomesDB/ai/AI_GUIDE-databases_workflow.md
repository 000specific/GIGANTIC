# AI Guide: STEP_3 Workflow - Build GIGANTIC GenomesDB BLAST Databases

**For AI Assistants**: Read the subproject guide (`../../AI_GUIDE-databases.md`) first for STEP_3 concepts and troubleshooting. This guide focuses on running the workflow.

**Location**: `gigantic_project-COPYME/subprojects/genomesDB/STEP_3-databases/workflow-COPYME-build_gigantic_genomesDB/ai/`

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../../../../AI_GUIDE-project.md` |
| genomesDB concepts, pipeline architecture | `../../../AI_GUIDE-genomesDB.md` |
| STEP_3 concepts, troubleshooting | `../../AI_GUIDE-databases.md` |
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

Edit `databases_config.yaml` if needed:

```yaml
inputs:
  # Species selection manifest from STEP_2 (via subproject output_to_input/)
  species_manifest: "../../output_to_input/STEP_2-standardize_and_evaluate/species_selection_manifest.tsv"

  # Cleaned proteomes from STEP_2 (via subproject output_to_input/)
  proteomes_dir: "../../output_to_input/STEP_2-standardize_and_evaluate/gigantic_proteomes_cleaned"

blast:
  # Name for the BLAST database directory
  database_name: "gigantic-T1-blastp"

  # Number of parallel makeblastdb jobs (4-8 recommended)
  parallel_jobs: 4
```

Default paths work if STEP_2 has been run and its `RUN-workflow.sh` created the `output_to_input/` symlinks.

### 3. Ensure prerequisites are met

- STEP_2 must be complete (proteomes cleaned and symlinked to `output_to_input/`)
- Species selection manifest must have `Include=YES` for species to include
- `ai_gigantic_genomesdb` conda environment must be available (or BLAST+, NextFlow, Python3 in PATH)

### 4. Run the workflow

**Local:**
```bash
bash RUN-workflow.sh
```

**SLURM** (edit account/qos in sbatch file first):
```bash
sbatch RUN-workflow.sbatch
```

### 5. Verify outputs

See verification commands below.

---

## Script Pipeline

| Order | Script | Purpose | Input | Output |
|-------|--------|---------|-------|--------|
| 1 | `001_ai-python-filter_species_manifest.py` | Filter species to Include=YES only | Species selection manifest from STEP_2 | `1-output/1_ai-filtered_species_manifest.tsv` |
| 2 | `002_ai-python-build_per_genome_blastdbs.py` | Build per-genome BLAST protein databases | Filtered manifest + cleaned proteomes | `2-output/gigantic-T1-blastp/` (per-genome BLAST databases) |

**Pipeline flow**: Script 001 filters the manifest to Include=YES species only --> Script 002 reads the filtered manifest and builds one BLAST database per species.

---

## Verification Commands

After the workflow completes, verify outputs:

### Check filtered species

```bash
# How many species were included?
tail -n +2 OUTPUT_pipeline/1-output/1_ai-filtered_species_manifest.tsv | wc -l

# View the filtered manifest
head OUTPUT_pipeline/1-output/1_ai-filtered_species_manifest.tsv
```

### Check BLAST databases

```bash
# Count BLAST database sets (each species has multiple files)
ls OUTPUT_pipeline/2-output/gigantic-T1-blastp/*.aa | wc -l

# Verify BLAST database files exist for a species
ls OUTPUT_pipeline/2-output/gigantic-T1-blastp/ | head -20

# View makeblastdb commands log
cat OUTPUT_pipeline/2-output/2_ai-makeblastdb_commands.sh
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
# Filter manifest log
cat OUTPUT_pipeline/1-output/1_ai-log-filter_species_manifest.log

# Build BLAST databases log
cat OUTPUT_pipeline/2-output/2_ai-log-build_per_genome_blastdbs.log
```

---

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Species selection manifest not found" | STEP_2 not run or symlinks missing | Run STEP_2 first; verify `../../output_to_input/STEP_2-standardize_and_evaluate/species_selection_manifest.tsv` exists |
| "Proteomes directory not found" | STEP_2 symlinks missing | Verify `../../output_to_input/STEP_2-standardize_and_evaluate/gigantic_proteomes_cleaned/` exists |
| "No species have Include=YES" | Manifest not edited or all species excluded | Edit `species_selection_manifest.tsv` and set `Include=YES` for species to include |
| "makeblastdb not found" | BLAST+ not installed or not in PATH | Activate conda environment: `module load conda && conda activate ai_gigantic_genomesdb` |
| "Proteome file not found: ..." | Species in manifest but proteome missing | Check STEP_2 output; ensure proteome exists for this species |
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
