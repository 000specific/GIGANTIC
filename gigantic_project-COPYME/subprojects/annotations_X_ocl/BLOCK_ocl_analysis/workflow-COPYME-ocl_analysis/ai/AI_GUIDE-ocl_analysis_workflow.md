# AI Guide: Annotations OCL Analysis Workflow

**AI**: Claude Code | Opus 4.6 | 2026 April 18
**Human**: Eric Edsinger

**For AI Assistants**: Read the subproject guide (`../../../AI_GUIDE-annotations_X_ocl.md`)
first for concepts and architecture. This guide focuses on running the workflow.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../AI_GUIDE-project.md` |
| Subproject concepts | `../../../AI_GUIDE-annotations_X_ocl.md` |
| STEP architecture | `../../AI_GUIDE-ocl_analysis.md` |
| Running the workflow | This file |

---

## Step-by-Step Execution

### 1. Prerequisites

Verify upstream subprojects have populated their `output_to_input/` directories:

```bash
# Check trees_species output exists
ls ../../../../trees_species/output_to_input/BLOCK_permutations_and_features/

# Check annotations_hmms output exists (replace DATABASE with your choice)
ls ../../../../annotations_hmms/output_to_input/BLOCK_build_annotation_database/annotation_databases/database_pfam/
```

### 2. Configure

Edit `START_HERE-user_config.yaml`:

```yaml
run_label: "species70_pfam"          # Unique name for this exploration
species_set_name: "species70"
annotation_database: "pfam"

annogroup_subtypes:
  - "single"
  - "combo"
  - "zero"

inputs:
  structure_manifest: "INPUT_user/structure_manifest.tsv"
  trees_species_dir: "../../../../trees_species/output_to_input/BLOCK_permutations_and_features"
  annotations_dir: "../../../../annotations_hmms/output_to_input/BLOCK_build_annotation_database/annotation_databases/database_pfam"

# Computational Resources (used when execution_mode is "slurm")
cpus: 3
memory_gb: 20
time_hours: 24

# Execution Mode: "local" (run here) or "slurm" (self-submit as SLURM job)
execution_mode: "slurm"
slurm_account: "moroz"
slurm_qos: "moroz"

resume: false
```

Edit `INPUT_user/structure_manifest.tsv`:

```
structure_id
001
002
003
```

### 3. Run

Single entry point for both local and SLURM execution -- behavior determined by
`execution_mode` in the config above:

```bash
bash RUN-workflow.sh
```

On first run, the conda env `aiG-annotations_X_ocl-ocl_analysis` is created
automatically from `ai/conda_environment.yml` (via mamba, falls back to conda).

### 4. Verify

```bash
# Check validation passed for each structure
cat OUTPUT_pipeline/structure_001/5-output/5_ai-structure_001_validation_report.txt

# Check QC metrics
cat OUTPUT_pipeline/structure_001/5-output/5_ai-structure_001_qc_metrics.tsv

# Check symlinks were created
ls ../../output_to_input/BLOCK_ocl_analysis/species70_pfam/
```

---

## Script Pipeline Detail

### Script 001: Create Annogroups
- Reads annotation files from annotations_hmms (7-column per-species TSV)
- Creates annogroups for each requested subtype (single, combo, zero)
- Loads phylogenetic data from trees_species (Rule 6 atomic identifiers)
- Writes standardized annogroups file with species already resolved to Genus_species
- **Output**: `1-output/` (phylogenetic files + annogroup map + per-subtype files + standardized features)

### Script 002: Determine Origins
- MRCA algorithm: single-species annogroups get species as origin
- Multi-species: path intersection + deepest divergence point
- Species come pre-resolved from Script 001 (no GIGANTIC ID parsing needed)
- Emits per annogroup:
  - `Origin_Phylogenetic_Block` -- tree-structural edge `parent::child`
  - `Origin_Phylogenetic_Block_State` -- block tagged with Origin letter, `parent::child-O`
- **Output**: `2-output/` (origins table + per-clade files + summary)

### Script 003: Classify Block-States and Quantify Conservation / Loss
- Classifies each (block, annogroup) pair into one of the five block-states:
  - `-A` Inherited Absence (pre-origin)
  - `-O` Origin (emitted by Script 002, not re-scored here)
  - `-P` Inherited Presence (conservation)
  - `-L` Loss (event)
  - `-X` Inherited Loss (post-loss)
- Terminal self-loops excluded from the block set
- Edge case: zero inherited transitions -> counts = 0 (handled explicitly)
- **Output**: `3-output/` (block stats + per-annogroup block-state counts + summary)

### Script 004: Comprehensive Analysis
- Integrates Scripts 002 + 003 data
- Generates all-types integrated summary (primary downstream file)
- Generates per-subtype summaries (one per annogroup subtype)
- Generates per-clade and per-species summaries
- Generates per (annogroup, species) phylogenetic path-states (Rule 7 AOPLX strings)
- Cross-validates annogroup counts (Script 003 vs 004)
- **Output**: `4-output/` (all-types + per-subtype summaries + clade stats + species stats + path-states + validation)

### Script 005: Validate Results
- 8 validation checks across all scripts, including path-state integrity (state machine)
- **Strict fail-fast**: exits with code 1 on ANY failure
- **Output**: `5-output/` (validation report + error log + QC metrics)

---

## Common Execution Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "conda not found" | On HPC, conda module not loaded | `module load conda` (HiPerGator) then re-run `bash RUN-workflow.sh` |
| Env create hangs on Lustre | Login node contention | Set `execution_mode: "slurm"` so env creation runs on a compute node |
| "No such file" for trees_species | Wrong relative path in config | From the workflow dir, it's `../../../../trees_species/...` (4 ups) |
| "No annotation files found" | Wrong database path or annotations_hmms not run | Verify `annotations_dir` points to correct database directory |
| SLURM job OOM killed | Database has too many annogroups | Increase `memory_gb` in `START_HERE-user_config.yaml` |
| Stale cached results | Used `-resume` after script changes | `resume: false` (default); if cache got stale, delete `work/`, `.nextflow/`, `.nextflow.log*` and re-run |
| Validation exit code 1 | Data inconsistency found | Check `5-output/5_ai-{structure}_validation_error_log.txt` for specific failures |

---

## Resource Estimates

| Process | Memory | CPUs | Time | Notes |
|---------|--------|------|------|-------|
| create_annogroups | 14 GB | 2 | < 1hr | Loads annotation files + creates annogroup map |
| determine_origins | 4 GB | 1 | < 1hr | MRCA algorithm |
| quantify_conservation_loss | 4 GB | 1 | < 1hr | Block-state classification |
| comprehensive_ocl_analysis | 8 GB | 1 | < 1hr | Integration + path-states + summaries |
| validate_results | 4 GB | 1 | < 30min | Read + verify |

---

## Diagnostic Commands

```bash
# Check pipeline progress
tail -f OUTPUT_pipeline/structure_001/logs/1_ai-log-create_annogroups-structure_001.log

# Count processed structures
ls -d OUTPUT_pipeline/structure_*/5-output/ 2>/dev/null | wc -l

# Check for any failed validations
grep -l "FAIL" OUTPUT_pipeline/structure_*/5-output/*validation_report.txt

# View NextFlow execution trace
cat OUTPUT_pipeline/pipeline_trace.txt
```
