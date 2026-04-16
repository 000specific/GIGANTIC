# AI Guide: BLOCK_ocl_analysis

**AI**: Claude Code | Opus 4.6 | 2026 April 13
**Human**: Eric Edsinger

**For AI Assistants**: Read the subproject guide (`../AI_GUIDE-orthogroups_X_ocl.md`) first.
This guide covers STEP-specific details.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../AI_GUIDE-project.md` |
| Subproject concepts | `../AI_GUIDE-orthogroups_X_ocl.md` |
| STEP architecture | This file |
| Running the workflow | `workflow-COPYME-ocl_analysis/ai/AI_GUIDE-ocl_analysis_workflow.md` |

---

## What This STEP Does

BLOCK_ocl_analysis contains a single workflow-COPYME template that runs the complete
OCL pipeline (6 scripts). Each COPYME copy represents one exploration — one
combination of species set and orthogroup clustering tool.

A future `STEP_2-occams_tree/` (planned) will consume
STEP_1's per-structure summaries and rank candidate species trees by total-loss
minimization.

---

## COPYME Pattern

```
BLOCK_ocl_analysis/
├── workflow-COPYME-ocl_analysis/    # Template (never run directly)
├── workflow-RUN_01-ocl_analysis/    # Copy for species70 X OrthoHMM
├── workflow-RUN_02-ocl_analysis/    # Copy for species70 X OrthoFinder
└── workflow-RUN_03-ocl_analysis/    # Copy for species70 X Broccoli
```

Each copy has its own `START_HERE-user_config.yaml` with a unique `run_label`, and outputs go to
separate subdirectories in `output_to_input/BLOCK_ocl_analysis/{run_label}/`.

---

## Creating a New Run

```bash
# 1. Copy the template
cp -r workflow-COPYME-ocl_analysis workflow-RUN_01-ocl_analysis

# 2. Edit config for this specific run
cd workflow-RUN_01-ocl_analysis
nano START_HERE-user_config.yaml
# Set: run_label, species_set_name, orthogroup_tool, input paths,
#      execution_mode ("local" or "slurm"), and if slurm: slurm_account/slurm_qos

# 3. Edit structure manifest (one structure_id per line)
nano INPUT_user/structure_manifest.tsv
# Add structure IDs (001, 002, ... 105)

# 4. Run — single entry point for both local and SLURM
bash RUN-workflow.sh
# Behavior depends on execution_mode in the config:
#   "local" → runs here
#   "slurm" → self-submits via sbatch with resources from config
```

The conda environment (`aiG-orthogroups_X_ocl-ocl_analysis`) is created
on-demand from `ai/conda_environment.yml` on first run — no separate install
step needed.

---

## The 6-Script Pipeline

| Script | Purpose | Key Output |
|--------|---------|------------|
| 001 | Prepare inputs from upstream subprojects | Standardized orthogroups, phylogenetic blocks (parent::child), paths |
| 002 | Determine MRCA origin of each orthogroup | Orthogroup origins with `Origin_Phylogenetic_Block` (parent::child) and `Origin_Phylogenetic_Block_State` (parent::child-O) |
| 003 | Classify each (block, orthogroup) pair into the five-state vocabulary (A/O/P/L/X); aggregate per-block and per-orthogroup statistics | Per-block stats, per-orthogroup TEMPLATE_03 patterns |
| 004 | Generate comprehensive summaries joining origins, states, and counts | Complete OCL summary with block/block-state columns, per-clade stats, per-species stats |
| 005 | Validate all results (fail-fast) | Validation report, error log, QC metrics |
| 006 | Write run log | Timestamped log of this run |

Scripts are sequential per structure but parallel across structures (NextFlow manages this).

### Block vs Block-State Vocabulary (Rule 7)

A **phylogenetic block** (written `parent_clade_id_name::child_clade_id_name`)
is a single parent-to-child edge on a species tree structure — feature-agnostic.
A **phylogenetic block-state** (written `parent_clade_id_name::child_clade_id_name-LETTER`)
is a block paired with a specific orthogroup's state on it. The LETTER is one of
five codes: **A** Inherited Absence, **O** Origin, **P** Inherited Presence,
**L** Loss, **X** Inherited Loss. Event blocks carry state O or L; inheritance
blocks carry state A, P, or X.

See Rule 7 of `../../../AI_GUIDE-project.md` and the full specification in
`../research_notebook/ai_research/planning-phylogenetic_blocks_and_locks/whitepaper.md`.

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
