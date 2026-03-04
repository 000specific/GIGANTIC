# AI Guide: BLOCK_ocl_analysis

**AI**: Claude Code | Opus 4.6 | 2026 March 04
**Human**: Eric Edsinger

**For AI Assistants**: Read the subproject guide (`../AI_GUIDE-orthogroups_X_ocl.md`) first.
This guide covers BLOCK-specific details.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../AI_GUIDE-project.md` |
| Subproject concepts | `../AI_GUIDE-orthogroups_X_ocl.md` |
| BLOCK architecture | This file |
| Running the workflow | `workflow-COPYME-ocl_analysis/ai/AI_GUIDE-ocl_analysis_workflow.md` |

---

## What This BLOCK Does

BLOCK_ocl_analysis contains a single workflow-COPYME template that runs the complete
5-script OCL pipeline. Each COPYME copy represents one exploration (one combination of
species set and orthogroup clustering tool).

---

## COPYME Pattern

```
BLOCK_ocl_analysis/
├── workflow-COPYME-ocl_analysis/    # Template (never run directly)
├── workflow-RUN_01-ocl_analysis/    # Copy for Species71 X OrthoFinder
├── workflow-RUN_02-ocl_analysis/    # Copy for Species71 X OrthoHMM
└── workflow-RUN_03-ocl_analysis/    # Copy for Species71 X Broccoli
```

Each copy has its own `ocl_config.yaml` with a unique `run_label`, and outputs go to
separate subdirectories in `output_to_input/BLOCK_ocl_analysis/{run_label}/`.

---

## Creating a New Run

```bash
# 1. Copy the template
cp -r workflow-COPYME-ocl_analysis workflow-RUN_01-ocl_analysis

# 2. Edit config for this specific run
cd workflow-RUN_01-ocl_analysis
vi ocl_config.yaml
# Set: run_label, orthogroup_tool, input paths

# 3. Edit structure manifest
vi INPUT_user/structure_manifest.tsv
# Add structure IDs (001, 002, ... 105)

# 4. Run
bash RUN-workflow.sh          # Local
sbatch RUN-workflow.sbatch    # SLURM cluster
```

---

## The 5-Script Pipeline

| Script | Purpose | Key Output |
|--------|---------|------------|
| 001 | Prepare inputs from upstream subprojects | Standardized orthogroups, blocks, paths |
| 002 | Determine MRCA origin of each orthogroup | Orthogroup origins with clade annotations |
| 003 | Quantify conservation/loss (TEMPLATE_03) | Per-block stats, per-orthogroup patterns |
| 004 | Generate comprehensive summaries | Complete OCL summary, clade stats, species stats |
| 005 | Validate all results (fail-fast) | Validation report, error log, QC metrics |

Scripts are sequential per structure but parallel across structures (NextFlow manages this).

---

## Output Per Structure

```
OUTPUT_pipeline/structure_NNN/
├── 1-output/    Standardized inputs from upstream subprojects
├── 2-output/    Orthogroup origins + per-clade files
├── 3-output/    Conservation/loss per block + per orthogroup
├── 4-output/    Comprehensive summaries (primary downstream file)
├── 5-output/    Validation report + QC metrics
└── logs/        Per-script log files
```
