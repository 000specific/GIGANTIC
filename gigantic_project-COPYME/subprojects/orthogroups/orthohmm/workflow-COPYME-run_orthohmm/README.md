# OrthoHMM Workflow

**AI**: Claude Code | Opus 4.5 | 2026 February 27
**Human**: Eric Edsinger

Run OrthoHMM to identify orthogroups (gene families) using profile HMMs.

## Quick Start

```bash
# 1. Copy this template to create a run instance
cp -r workflow-COPYME-run_orthohmm workflow-RUN_01-run_orthohmm
cd workflow-RUN_01-run_orthohmm/

# 2. Activate conda environment
module load conda  # HiPerGator only
conda activate ai_gigantic_orthogroups

# 3. Run the workflow
bash RUN-workflow.sh

# Or for SLURM (edit account/qos first):
sbatch RUN-workflow.sbatch
```

## Prerequisites

- **genomesDB STEP_2 complete**: Proteomes must exist in `genomesDB/STEP_2.../output_to_input/gigantic_proteomes/`
- **Conda environment**: `ai_gigantic_orthogroups`

## Workflow Steps

| Script | Output Directory | Description |
|--------|------------------|-------------|
| 001 | `1-output/` | Validate proteomes, create inventory |
| 002 | `2-output/` | Convert headers to short IDs |
| 003 | `3-output/` | Run OrthoHMM clustering |
| 004 | `4-output/` | Generate summary statistics |
| 005 | `5-output/` | Per-species QC analysis |
| 006 | `6-output/` | Restore GIGANTIC identifiers |

## Inputs

The workflow automatically reads proteomes from:
```
../../../genomesDB/STEP_2-standardize_and_evaluate/output_to_input/gigantic_proteomes/
```

No manual file copying required.

## Results

Results appear in `OUTPUT_pipeline/` subdirectories:

- `6-output/6_ai-orthogroups_gigantic_ids.txt` - Main orthogroup assignments
- `4-output/4_ai-orthohmm_summary_statistics.tsv` - Summary statistics
- `5-output/5_ai-orthogroups_per_species_summary.tsv` - Per-species QC

Key outputs are also copied to `../output_to_input/` for downstream subprojects.

## SLURM Resources

The default SBATCH settings are:
- CPUs: 100
- Memory: 200GB
- Time: 200 hours

These are appropriate for ~70 species. Adjust based on your dataset size.

## Need Help?

Ask your AI assistant to read `../AI_GUIDE-orthohmm.md` for guidance.
