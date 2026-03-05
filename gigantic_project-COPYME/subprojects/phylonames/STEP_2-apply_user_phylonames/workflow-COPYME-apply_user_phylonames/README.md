# Phylonames STEP 2: Apply User Phylonames

**STEP 2** applies your custom phylonames to override the NCBI-generated phylonames from STEP 1.

## Prerequisites

1. Run STEP 1 first to generate initial phylonames
2. Review the STEP 1 taxonomy summary to identify species needing overrides
3. Create `INPUT_user/user_phylonames.tsv` with your custom phylonames

## Quick Start

1. Copy the example: `cp INPUT_user/user_phylonames_example.tsv INPUT_user/user_phylonames.tsv`
2. Edit `INPUT_user/user_phylonames.tsv` with your custom phylonames
3. Edit `START_HERE-user_config.yaml` - set your project name (must match STEP 1)
4. Run: `bash RUN-workflow.sh` (local) or `sbatch RUN-workflow.sbatch` (SLURM)

## User Phylonames Format

Tab-separated file with columns: `genus_species<TAB>custom_phyloname`

```
Monosiga_brevicollis_MX1	Holozoa_Choanozoa_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1
Chromosphaera_perkinsii	Holozoa_Ichthyosporea_Ichthyophonida_Chromosphaeraceae_Chromosphaera_perkinsii
```

## Results

- **Final mapping**: `OUTPUT_pipeline/1-output/final_project_mapping.tsv`
- **Unofficial clades report**: `OUTPUT_pipeline/1-output/unofficial_clades_report.tsv`
- **Updated taxonomy summary**: `OUTPUT_pipeline/2-output/` (Markdown and HTML)
- **Downstream symlink**: `../../output_to_input/maps/` (updated to point to STEP 2 output)

## UNOFFICIAL Marking

By default, clades that differ from NCBI get an "UNOFFICIAL" suffix to maintain transparency about data sources. Set `mark_unofficial: false` in `START_HERE-user_config.yaml` to disable.
