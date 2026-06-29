# AI Guide: Annotations OCL Analysis Workflow

**AI**: Claude Code | Opus 4.6 | 2026 April 18
**Human**: Eric Edsinger

**For AI Assistants**: Read the BLOCK guide (`../../AI_GUIDE.md`)
first for concepts and architecture. This guide focuses on running the workflow.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../AI_GUIDE.md` |
| Parent subproject | `../../../README.md` and `../../../AI_GUIDE.md` |
| BLOCK concepts + workflow-execution overview | `../../AI_GUIDE.md` |
| Running the workflow | This file |

---

## Step-by-Step Execution

### 1. Prerequisites

Verify upstream subprojects have populated their `output_to_input/` directories:

```bash
# Check trees_species output exists
ls ../../../../trees_species/output_to_input/BLOCK_permutations_and_features/

# Check the annogroups subproject built the source's annogroup map (replace pfam)
ls ../../../../annogroups/output_to_input/BLOCK_build_annogroups/species70/pfam/2_ai-pfam-annogroup_map.tsv
```

### 2. Configure

Edit `START_HERE-user_config.yaml`:

```yaml
species_set_name: "species70"
annotation_databases: [ pfam, go, panther ]   # or "all"; the run fans out PER SOURCE
                                              # (replaces the old single-source run_label)

annogroup_types:                     # absent excluded (no single origin)
  - "feature"
  - "combination"
  - "architecture"

inputs:
  structure_manifest: "INPUT_user/structure_manifest.tsv"
  trees_species_dir: "../../../../trees_species/output_to_input/BLOCK_permutations_and_features"
  annogroups_dir: "../../../../annogroups/output_to_input/BLOCK_build_annogroups"

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
ls ../../output_to_input/BLOCK_annotations_X_ocl/species70_pfam/
```

---

## Script Pipeline Detail

### Script 001: Load Annogroups
- **Imports** annogroups from the annogroups subproject map (does NOT compute them)
- Loads the configured `annogroup_types` (feature, combination, architecture; absent excluded)
- Loads phylogenetic data from trees_species (Rule 6 atomic identifiers)
- Writes the standardized annogroups file (species already resolved to Genus_species) + annogroup map
- **Output**: `1-output/` (phylogenetic files + annogroup map + standardized annogroups-species_identifiers)

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
- Generates per-type summaries (one per annogroup type: feature, combination, architecture)
- Generates per-clade and per-species summaries
- Generates per (annogroup, species) phylogenetic path-states (Rule 7 AOPLX strings)
- Cross-validates annogroup counts (Script 003 vs 004)
- **Output**: `4-output/` (all-types + per-type summaries + clade stats + species stats + path-states + validation)

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
| "annogroup map not found" | Wrong path or the annogroups subproject not run for this source | Verify `annogroups_dir` + the source's `2_ai-<source>-annogroup_map.tsv` exists |
| SLURM job OOM killed | Source has many annogroups (e.g. architecture) | Increase `memory_gb` in `START_HERE-user_config.yaml` (Script 004 dominates) |
| Stale cached results | Used `-resume` after script changes | `resume: false` (default); if cache got stale, delete `work/`, `.nextflow/`, `.nextflow.log*` and re-run |
| Validation exit code 1 | Data inconsistency found | Check `5-output/5_ai-{structure}_validation_error_log.txt` for specific failures |

---

## Resource Estimates

| Process | Memory | CPUs | Time | Notes |
|---------|--------|------|------|-------|
| load_annogroups | 8 GB | 2 | < 5min | Imports annogroups from the annogroups subproject + writes phylo inputs |
| determine_origins | 4 GB | 1 | < 1hr | MRCA algorithm |
| quantify_conservation_loss | 4 GB | 1 | < 1hr | Block-state classification |
| comprehensive_ocl_analysis | 12 GB | 1 | < 1hr | Integration + path-states + summaries (measured ~6.4 GB peak) |
| validate_results | 4 GB | 1 | < 30min | Read + verify |

---

## Diagnostic Commands

```bash
# Check pipeline progress
tail -f OUTPUT_pipeline/structure_001/logs/1_ai-log-load_annogroups-structure_001.log

# Count processed structures
ls -d OUTPUT_pipeline/structure_*/5-output/ 2>/dev/null | wc -l

# Check for any failed validations
grep -l "FAIL" OUTPUT_pipeline/structure_*/5-output/*validation_report.txt

# View NextFlow execution trace
cat OUTPUT_pipeline/pipeline_trace.txt
```
