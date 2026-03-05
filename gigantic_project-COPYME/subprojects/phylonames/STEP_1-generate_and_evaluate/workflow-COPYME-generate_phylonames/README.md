# Phylonames Workflow (STEP_1)

Generate standardized phylogenetic names from NCBI taxonomy.

This is **STEP_1** of the 2-STEP phylonames architecture. It downloads NCBI taxonomy, generates phylonames for all species, creates your project-specific mapping, and produces a taxonomy summary for review.

## Quick Start

1. Edit `START_HERE-user_config.yaml` with your project name
2. Put your species list in `INPUT_user/species_list.txt` (one species per line, e.g., `Homo_sapiens`)
3. Run the workflow:
   - **Local**: `bash RUN-workflow.sh`
   - **SLURM**: Edit account/qos in `RUN-workflow.sbatch`, then `sbatch RUN-workflow.sbatch`

## Results

Your mapping file appears in `OUTPUT_pipeline/3-output/` and is symlinked to:
- `../../output_to_input/STEP_1-generate_and_evaluate/maps/` (canonical STEP_1 location)
- `../../output_to_input/maps/` (convenience symlink for downstream subprojects)

A **taxonomy summary** (Markdown and HTML) is generated in `OUTPUT_pipeline/4-output/` showing:
- Taxonomic distribution (species counts by kingdom/phylum)
- UNOFFICIAL clades (user-provided classifications)
- Numbered clades (NCBI gaps you could name)

## After Running

Review the taxonomy summary to identify species that received NOTINNCBI placeholders or need custom phylonames. If overrides are needed, run **STEP_2** to apply user-defined phylonames on top of the STEP_1 output.

## Need Help?

Ask your AI assistant to read `ai/AI_GUIDE-phylonames_workflow.md` for detailed guidance.
