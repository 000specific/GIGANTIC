# AI Guide: OCL Analysis Workflow

**AI**: Claude Code | Opus 4.6 | 2026 April 13
**Human**: Eric Edsinger

**For AI Assistants**: Read the subproject guide (`../../../AI_GUIDE-orthogroups_X_ocl.md`)
first for concepts and architecture. This guide focuses on running the workflow.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../AI_GUIDE-project.md` |
| Subproject concepts | `../../../AI_GUIDE-orthogroups_X_ocl.md` |
| STEP architecture | `../../AI_GUIDE-ocl_analysis.md` |
| Running the workflow | This file |

---

## Step-by-Step Execution

### 1. Prerequisites

Verify upstream subprojects have populated their `output_to_input/` directories:

```bash
# Check trees_species output exists
ls ../../../trees_species/output_to_input/BLOCK_permutations_and_features/

# Check orthogroups output exists (match your tool choice)
ls ../../../orthogroups/output_to_input/BLOCK_orthohmm/

# Check proteomes exist (replace speciesN with your species set)
ls ../../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/
```

### 2. Configure

Edit `START_HERE-user_config.yaml`:

```yaml
run_label: "species70_X_OrthoHMM"    # Unique name for this exploration
species_set_name: "species70"
orthogroup_tool: "OrthoHMM"

inputs:
  structure_manifest: "INPUT_user/structure_manifest.tsv"
  trees_species_dir: "../../../trees_species/output_to_input/BLOCK_permutations_and_features"
  orthogroups_dir: "../../../orthogroups/output_to_input/BLOCK_orthohmm"
  proteomes_dir: "../../../genomesDB/output_to_input/STEP_4-create_final_species_set/species70_gigantic_T1_proteomes"

include_fasta_in_output: false

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

Single entry point for both local and SLURM execution — behavior determined by
`execution_mode` in the config above:

```bash
bash RUN-workflow.sh
```

On first run, the conda env `aiG-orthogroups_X_ocl-ocl_analysis` is created
automatically from `ai/conda_environment.yml` (via mamba, falls back to conda).

### 4. Verify

```bash
# Check validation passed for each structure
cat OUTPUT_pipeline/structure_001/5-output/5_ai-validation_report.txt

# Check QC metrics
cat OUTPUT_pipeline/structure_001/5-output/5_ai-qc_metrics.tsv

# Check symlinks were created
ls ../../output_to_input/BLOCK_ocl_analysis/species70_X_OrthoHMM/
```

---

## Script Pipeline Detail

### Script 001: Prepare Inputs
- Reads from upstream subprojects via config paths
- Loads and standardizes phylogenetic blocks, parent-child tables, paths, clade mappings
- Converts orthogroup IDs to GIGANTIC identifiers
- **Output**: `1-output/` (6 files per structure)

### Script 002: Determine Origins
- MRCA algorithm: single-species (~86%) get species as origin
- Multi-species: path intersection + deepest divergence point
- Loads proteome FASTA sequences (config-driven path)
- Emits per orthogroup:
  - `Origin_Phylogenetic_Block` — tree-structural edge `parent::child` (e.g.
    `C069_Holozoa::C082_Metazoa`). Feature-agnostic identifier.
  - `Origin_Phylogenetic_Block_State` — block tagged with the Origin letter,
    `parent::child-O` (e.g. `C069_Holozoa::C082_Metazoa-O`). Feature-specific
    identifier in the five-state vocabulary {A, O, P, L, X}.
- **Output**: `2-output/` (origins table + per-clade files + summary)

### Script 003: Classify Block-States and Quantify Conservation / Loss
- Reads Script 002's block and block-state identifiers.
- TEMPLATE_03 dual-metric algorithm classifies each (block, orthogroup) pair
  into one of the five block-states:
  - `-A` Inherited Absence (pre-origin): parent absent, child absent, upstream of the orthogroup's origin
  - `-O` Origin (event): parent absent, child present (emitted by Script 002, not re-scored here)
  - `-P` Inherited Presence (conservation): parent present, child present
  - `-L` Loss (event): parent present, child absent
  - `-X` Inherited Loss (post-loss): parent absent, child absent, downstream of a loss
- Terminal self-loops (parent == child at leaf) are excluded from the block
  set — they are placeholder rows, not true parent-to-child blocks.
- Edge case: zero inherited transitions -> rates = 0.0 (handled explicitly).
- **Output**: `3-output/` (block stats + per-orthogroup TEMPLATE_03 patterns + summary)

### Script 004: Comprehensive Analysis
- Integrates Scripts 002 + 003 data, preserving both `Origin_Phylogenetic_Block`
  and `Origin_Phylogenetic_Block_State` columns.
- Cross-validates orthogroup counts (Script 003 vs 004)
- Generates per-clade and per-species summaries
- **Output**: `4-output/` (complete summary + clade stats + species stats + validation)

### Script 005: Validate Results
- 7 validation checks across all scripts
- **Strict fail-fast**: exits with code 1 on ANY failure
- **Output**: `5-output/` (validation report + error log + QC metrics)

---

## Common Execution Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "conda not found" | On HPC, conda module not loaded | `module load conda` (HiPerGator) then re-run `bash RUN-workflow.sh` |
| Env create hangs on Lustre | Login node contention + small-file writes | Set `execution_mode: "slurm"` so env creation runs on a compute node |
| "No such file" for trees_species | Wrong relative path in config | From the workflow dir, it's `../../../trees_species/...` (3 ups, not 4) |
| SLURM job OOM killed | Structure has too many orthogroups | Increase `memory_gb` in `START_HERE-user_config.yaml` |
| Stale cached results | Used `-resume` after script changes | `resume: false` (default) avoids this; if cache got stale, delete `work/`, `.nextflow/`, `.nextflow.log*` and re-run |
| Validation exit code 1 | Data inconsistency found | Check `5-output/5_ai-validation_error_log.txt` for specific failures |

---

## Resource Estimates

| Process | Memory | CPUs | Time | Notes |
|---------|--------|------|------|-------|
| prepare_inputs | 14 GB | 2 | < 1hr | Loads large ID mappings + proteomes |
| determine_origins | 4 GB | 1 | < 1hr | MRCA algorithm |
| quantify_conservation_loss | 4 GB | 1 | < 1hr | TEMPLATE_03 |
| comprehensive_ocl_analysis | 8 GB | 1 | < 1hr | Integration + summaries |
| validate_results | 4 GB | 1 | < 30min | Read + verify |

---

## Diagnostic Commands

```bash
# Check pipeline progress
tail -f OUTPUT_pipeline/structure_001/logs/1_ai-log-prepare_inputs-structure_001.log

# Count processed structures
ls -d OUTPUT_pipeline/structure_*/5-output/ 2>/dev/null | wc -l

# Check for any failed validations
grep -l "FAIL" OUTPUT_pipeline/structure_*/5-output/5_ai-validation_report.txt

# View NextFlow execution trace
cat OUTPUT_pipeline/pipeline_trace.txt
```
