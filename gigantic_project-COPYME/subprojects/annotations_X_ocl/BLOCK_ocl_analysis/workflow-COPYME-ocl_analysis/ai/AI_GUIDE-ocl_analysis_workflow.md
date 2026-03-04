# AI Guide: OCL Analysis Workflow (Annotations)

**AI**: Claude Code | Opus 4.6 | 2026 March 04
**Human**: Eric Edsinger

**For AI Assistants**: Read the subproject guide (`../../../AI_GUIDE-annotations_X_ocl.md`)
first for concepts and architecture. This guide focuses on running the workflow.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../AI_GUIDE-project.md` |
| Subproject concepts | `../../../AI_GUIDE-annotations_X_ocl.md` |
| BLOCK architecture | `../../AI_GUIDE-ocl_analysis.md` |
| Running the workflow | This file |

---

## Step-by-Step Execution

### 1. Prerequisites

Verify upstream subprojects have completed:

```bash
# Check trees_species output exists
ls ../../../../trees_species/output_to_input/BLOCK_permutations_and_features/

# Check annotations output exists (match your database choice)
ls ../../../../annotations_hmms/output_to_input/BLOCK_build_annotation_database/annotation_databases/database_pfam/
```

### 2. Configure

Edit `ocl_config.yaml`:

```yaml
run_label: "Species71_pfam"
species_set_name: "species71"
annotation_database: "pfam"

annogroup_subtypes:
  - "single"
  - "combo"
  - "zero"

inputs:
  structure_manifest: "INPUT_user/structure_manifest.tsv"
  trees_species_dir: "../../../../trees_species/output_to_input/BLOCK_permutations_and_features"
  annotations_dir: "../../../../annotations_hmms/output_to_input/BLOCK_build_annotation_database/annotation_databases/database_pfam"
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
ls ../../output_to_input/BLOCK_ocl_analysis/Species71_pfam/
```

---

## Script Pipeline Detail

### Script 001: Create Annogroups
- Phase A: Loads phylogenetic tree data (blocks, parent-child, paths, clade mappings)
- Phase B: Loads per-species annotation files from annotations_hmms (7-column TSV)
- Phase C: Creates annogroups per subtype (single, combo, zero) with sequential IDs
- Phase D: Writes annogroup map + per-subtype files + subtypes manifest
- **Output**: `1-output/` (phylogenetic data + annogroup map + per-subtype files)

### Script 002: Determine Origins
- MRCA algorithm: single-species get species as origin
- Multi-species: path intersection + deepest divergence point
- Species names from annogroup map (already Genus_species format)
- **Output**: `2-output/` (origins table + per-clade files + summary)

### Script 003: Quantify Conservation and Loss
- TEMPLATE_03 dual-metric algorithm
- Four event types per annogroup per block
- Terminal self-loop exclusion
- Edge case: zero inherited transitions -> rates = 0.0
- Includes Annogroup_Subtype in per-annogroup output (17 columns)
- **Output**: `3-output/` (block stats + annogroup patterns + summary)

### Script 004: Comprehensive Analysis
- Per-subtype complete OCL summaries
- **All-subtypes integrated summary** (primary downstream file)
- Cross-validates annogroup counts
- Generates per-clade and per-species summaries
- **Output**: `4-output/` (per-subtype summaries + all-types summary + clade stats + species stats)

### Script 005: Validate Results
- 8 validation checks (one more than orthogroups_X_ocl)
- Check 8: Annogroup subtype consistency, no duplicate IDs, ID format validation
- **Strict fail-fast**: exits with code 1 on ANY failure
- **Output**: `5-output/` (validation report + error log + QC metrics)

---

## Common Execution Errors

| Error | Cause | Solution |
|-------|-------|----------|
| NextFlow "command not found" | Conda env not activated | Run `module load conda && conda activate ai_gigantic_annotations_X_ocl` |
| "No such file" for trees_species | Wrong relative path in config | Verify `trees_species_dir` path resolves from workflow directory |
| "No annotation files found" | Wrong database or path | Verify `annotations_dir` contains species annotation TSVs |
| SLURM job OOM killed | Structure has too many annogroups | Increase memory in nextflow.config |
| Stale cached results | Updated scripts but used `-resume` | Delete `work/`, `.nextflow/`, `.nextflow.log*` and re-run fresh |
| Validation exit code 1 | Data inconsistency found | Check `5-output/5_ai-validation_error_log.txt` for specific failures |

---

## Resource Estimates

| Process | Memory | CPUs | Time | Notes |
|---------|--------|------|------|-------|
| create_annogroups | 8 GB | 1 | < 1hr | Loads all species annotation files |
| determine_origins | 4 GB | 1 | < 1hr | MRCA algorithm |
| quantify_conservation_loss | 4 GB | 1 | < 1hr | TEMPLATE_03 |
| comprehensive_ocl_analysis | 8 GB | 1 | < 1hr | Per-subtype + all-types integration |
| validate_results | 4 GB | 1 | < 30min | Read + verify |

---

## Diagnostic Commands

```bash
# Check pipeline progress
tail -f OUTPUT_pipeline/structure_001/logs/1_ai-log-create_annogroups-structure_001.log

# Count processed structures
ls -d OUTPUT_pipeline/structure_*/5-output/ 2>/dev/null | wc -l

# Check for any failed validations
grep -l "FAIL" OUTPUT_pipeline/structure_*/5-output/5_ai-validation_report.txt

# View NextFlow execution trace
cat OUTPUT_pipeline/pipeline_trace.txt

# Check annogroup counts per subtype
head -1 OUTPUT_pipeline/structure_001/1-output/1_ai-annogroup_subtypes_manifest.tsv
wc -l OUTPUT_pipeline/structure_001/1-output/1_ai-annogroups-*.tsv
```
