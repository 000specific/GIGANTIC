# OrthoHMM Workflow

**Status**: Template - scripts pending implementation

Run OrthoHMM to identify orthogroups (gene families) using profile HMMs.

## Quick Start

1. Copy proteomes to `INPUT_user/`
2. Edit configuration (once implemented)
3. Run the workflow:
   - **Local**: `bash RUN-orthohmm.sh`
   - **SLURM**: Edit account/qos, then `sbatch RUN-orthohmm.sbatch`

## Inputs

- **Proteomes**: FASTA files from genomesDB (`genomesDB/STEP_2.../output_to_input/gigantic_proteomes/`)

## Results

Output will appear in `OUTPUT_pipeline/` and be copied to `../output_to_input/` for downstream use.

## Need Help?

Ask your AI assistant to read `../AI_GUIDE-orthohmm.md` for guidance.
