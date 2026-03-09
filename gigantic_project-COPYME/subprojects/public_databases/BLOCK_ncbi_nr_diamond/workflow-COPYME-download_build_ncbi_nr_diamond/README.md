# NCBI nr DIAMOND Database Workflow

Download the NCBI nr protein database and build a DIAMOND search database.

## Quick Start

1. Edit `START_HERE-user_config.yaml` with your project name and settings
2. Edit `RUN-workflow.sbatch` with your SLURM account and qos (for HPC)
3. Run the workflow:
   - **Local**: `bash RUN-workflow.sh`
   - **SLURM**: `sbatch RUN-workflow.sbatch`

## Results

The DIAMOND database appears in `OUTPUT_pipeline/2-output/nr.dmnd` and is symlinked to:
- `../../output_to_input/BLOCK_ncbi_nr_diamond/nr.dmnd` (for downstream subprojects)

## Resource Requirements

- **Disk**: ~300 GB free (nr.gz ~100 GB + nr.dmnd ~150 GB)
- **Memory**: ~100 GB for DIAMOND database build
- **Time**: 6-24 hours depending on network speed and CPU count

## Need Help?

Ask your AI assistant to read `ai/AI_GUIDE-ncbi_nr_diamond_workflow.md` for detailed guidance.
