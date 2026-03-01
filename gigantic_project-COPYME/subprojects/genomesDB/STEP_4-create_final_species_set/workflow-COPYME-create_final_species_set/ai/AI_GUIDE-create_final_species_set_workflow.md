# AI Guide: STEP_4 Workflow - Create Final Species Set

**For AI Assistants**: Read the subproject guide (`../AI_GUIDE-create_final_species_set.md`) first for STEP_4 concepts and troubleshooting. This guide focuses on running the workflow.

**Location**: `gigantic_project-COPYME/subprojects/genomesDB/STEP_4-create_final_species_set/workflow-COPYME-create_final_species_set/ai/`

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../../../../AI_GUIDE-project.md` |
| genomesDB concepts, pipeline architecture | `../../../AI_GUIDE-genomesDB.md` |
| STEP_4 concepts, troubleshooting | `../../AI_GUIDE-create_final_species_set.md` |
| Running the workflow (this guide) | This file |

---

## Step-by-Step Execution

### 1. Copy the template

```bash
cd STEP_4-create_final_species_set/
cp -r workflow-COPYME-create_final_species_set workflow-RUN_01-create_final_species_set
cd workflow-RUN_01-create_final_species_set
```

### 2. Configure input paths

Edit `final_species_set_config.yaml`:

```yaml
inputs:
  # Path to cleaned proteomes from STEP_2
  step2_proteomes: "../STEP_2-standardize_and_evaluate/workflow-RUN_01-.../OUTPUT_pipeline/2-output/gigantic_proteomes_cleaned"

  # Path to BLAST databases from STEP_3
  step3_blastp: "../STEP_3-databases/workflow-RUN_01-.../OUTPUT_pipeline/1-output/gigantic_blastp"

  # Species selection file (optional - defaults to all species)
  selected_species: "INPUT_user/selected_species.txt"
```

### 3. Optional: configure species selection

Create `INPUT_user/selected_species.txt` with one species per line:

```
Homo_sapiens
Mus_musculus
Drosophila_melanogaster
```

If this file does not exist or is empty, **all species** from STEP_2 are included.

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
| 1 | `001_ai-python-validate_species_selection.py` | Validates species exist in STEP_2 and STEP_3 | Config paths + optional species list | `1-output/1_ai-validated_species_list.txt`, `1-output/1_ai-species_count.txt` |
| 2 | `002_ai-python-copy_selected_files.py` | Copies proteomes and BLAST DBs for selected species | Validated species list + STEP_2/STEP_3 paths | `2-output/speciesN_gigantic_T1_proteomes/`, `2-output/speciesN_gigantic_T1_blastp/` |

**Pipeline flow**: Script 001 produces the validated species list and count --> Script 002 reads those to copy the correct files.

---

## Verification Commands

After the workflow completes, verify outputs:

### Check validated species list

```bash
# How many species were validated?
cat OUTPUT_pipeline/1-output/1_ai-species_count.txt

# View the validated species
cat OUTPUT_pipeline/1-output/1_ai-validated_species_list.txt
```

### Check copied files

```bash
# Count proteome files
ls OUTPUT_pipeline/2-output/species*_gigantic_T1_proteomes/ | wc -l

# Count BLAST database files
ls OUTPUT_pipeline/2-output/species*_gigantic_T1_blastp/ | wc -l

# View copy manifest
head OUTPUT_pipeline/2-output/2_ai-copy_manifest.tsv
```

### Check output_to_input (for downstream subprojects)

```bash
# Final proteomes for downstream
ls ../../output_to_input/species*_gigantic_T1_proteomes/ | head

# Final BLAST DBs for downstream
ls ../../output_to_input/species*_gigantic_T1_blastp/ | head
```

### Check logs

```bash
# Validation log
cat OUTPUT_pipeline/1-output/1_ai-log-validate_species_selection.log

# Copy log
cat OUTPUT_pipeline/2-output/2_ai-log-copy_selected_files.log
```

---

## Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Config file not found" | `final_species_set_config.yaml` missing | Ensure you copied the template correctly |
| "NextFlow not found" | Conda environment not activated | Run `module load conda && conda activate ai_gigantic_genomesdb` |
| "No proteomes found at path" | Wrong path in config for `step2_proteomes` | Verify the path exists: `ls <path_from_config>` |
| "No BLAST databases found at path" | Wrong path in config for `step3_blastp` | Verify the path exists: `ls <path_from_config>` |
| "Species X in selection but not in STEP_2" | Typo in species name or species not processed | Check spelling in `selected_species.txt`; verify STEP_2 output |
| "Species X in STEP_2 but not in STEP_3" | STEP_3 incomplete for some species | Run STEP_3 for missing species or remove from selection |
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

## What Happens After STEP_4

Once STEP_4 completes, downstream subprojects access the final species set at:

```
genomesDB/STEP_4-create_final_species_set/output_to_input/
├── speciesN_gigantic_T1_proteomes/    # Proteome files
└── speciesN_gigantic_T1_blastp/       # BLAST database files
```

These are also accessible from the genomesDB root `output_to_input/` directory, depending on how the workflow publishes outputs.

Downstream subprojects that use this data:
- **orthogroups** (orthohmm, broccoli, orthofinder)
- **gene_trees** (trees-gene_families, trees-orthogroups)
- **annotations** (HMM annotations)
