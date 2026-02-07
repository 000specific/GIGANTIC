# Phylonames Workflow

Generate standardized phylogenetic names from NCBI taxonomy.

## Quick Start

1. Edit `phylonames_config.yaml` with your project name
2. Put your species list in `INPUT_user/species_list.txt` (one species per line, e.g., `Homo_sapiens`)
3. Run the workflow:
   - **Local**: `bash RUN_phylonames.sh`
   - **SLURM**: Edit account/qos in `RUN_phylonames.sbatch`, then `sbatch RUN_phylonames.sbatch`

## Results

Your mapping file appears in `OUTPUT_pipeline/` and is also copied to `../output_to_input/maps/` for downstream subprojects.

## Need Help?

Ask your AI assistant to read `ai/AI_GUIDE-phylonames_workflow.md` for detailed guidance.
