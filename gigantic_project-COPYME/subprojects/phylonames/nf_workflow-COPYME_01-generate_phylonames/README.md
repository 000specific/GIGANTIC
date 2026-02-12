# Phylonames Workflow

Generate standardized phylogenetic names from NCBI taxonomy.

## Quick Start

1. Edit `phylonames_config.yaml` with your project name
2. Put your species list in `INPUT_user/species_list.txt` (one species per line, e.g., `Homo_sapiens`)
3. Run the workflow:
   - **Local**: `bash RUN-phylonames.sh`
   - **SLURM**: Edit account/qos in `RUN-phylonames.sbatch`, then `sbatch RUN-phylonames.sbatch`

## Results

Your mapping file appears in `OUTPUT_pipeline/3-output/` and is also copied to `../output_to_input/maps/` for downstream subprojects.

A **taxonomy summary** (Markdown and HTML) is generated in `OUTPUT_pipeline/5-output/` showing:
- Taxonomic distribution (species counts by kingdom/phylum)
- UNOFFICIAL clades (user-provided classifications)
- Numbered clades (NCBI gaps you could name)

## Need Help?

Ask your AI assistant to read `ai/AI_GUIDE-phylonames_workflow.md` for detailed guidance.
