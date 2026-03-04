# AI Guide: OCL Analysis Workflow

**AI**: Claude Code | Opus 4.6 | 2026 March 04
**Human**: Eric Edsinger

**For AI Assistants**: Read the subproject guide (`../../../AI_GUIDE-orthogroups_X_ocl.md`)
first for concepts and architecture. This guide focuses on running the workflow.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../AI_GUIDE-project.md` |
| Subproject concepts | `../../../AI_GUIDE-orthogroups_X_ocl.md` |
| BLOCK architecture | `../../AI_GUIDE-ocl_analysis.md` |
| Running the workflow | This file |

---

## Step-by-Step Execution

### 1. Prerequisites

Verify upstream subprojects have completed:

```bash
# Check trees_species output exists
ls ../../../../trees_species/output_to_input/BLOCK_permutations_and_features/

# Check orthogroups output exists (match your tool choice)
ls ../../../../orthogroups/output_to_input/BLOCK_orthofinder/

# Check proteomes exist
ls ../../../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/
```

### 2. Configure

Edit `ocl_config.yaml`:

```yaml
run_label: "Species71_X_OrthoFinder"    # Unique name for this exploration
species_set_name: "species71"
orthogroup_tool: "OrthoFinder"

inputs:
  structure_manifest: "INPUT_user/structure_manifest.tsv"
  trees_species_dir: "../../../../trees_species/output_to_input/BLOCK_permutations_and_features"
  orthogroups_dir: "../../../../orthogroups/output_to_input/BLOCK_orthofinder"
  proteomes_dir: "../../../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes"

include_fasta_in_output: false
```

Edit `INPUT_user/structure_manifest.tsv`:

```
structure_id
001
002
003
```

### 3. Run

```bash
# Local execution
bash RUN-workflow.sh

# SLURM cluster
sbatch RUN-workflow.sbatch
```

### 4. Verify

```bash
# Check validation passed for each structure
cat OUTPUT_pipeline/structure_001/5-output/5_ai-validation_report.txt

# Check QC metrics
cat OUTPUT_pipeline/structure_001/5-output/5_ai-qc_metrics.tsv

# Check symlinks were created
ls ../../output_to_input/BLOCK_ocl_analysis/Species71_X_OrthoFinder/
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
- **Output**: `2-output/` (origins table + per-clade files + summary)

### Script 003: Quantify Conservation and Loss
- TEMPLATE_03 dual-metric algorithm
- Four event types per orthogroup per block
- Terminal self-loop exclusion
- Edge case: zero inherited transitions -> rates = 0.0
- **Output**: `3-output/` (block stats + orthogroup patterns + summary)

### Script 004: Comprehensive Analysis
- Integrates Scripts 002 + 003 data
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
| NextFlow "command not found" | Conda env not activated | Run `module load conda && conda activate ai_gigantic_orthogroups_X_ocl` |
| "No such file" for trees_species | Wrong relative path in config | Verify `trees_species_dir` path resolves from workflow directory |
| SLURM job OOM killed | Structure has too many orthogroups | Increase memory in nextflow.config |
| Stale cached results | Updated scripts but used `-resume` | Delete `work/`, `.nextflow/`, `.nextflow.log*` and re-run fresh |
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
