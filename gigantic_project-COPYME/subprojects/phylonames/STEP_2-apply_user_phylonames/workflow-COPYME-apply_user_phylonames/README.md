<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26
Human:   Eric Edsinger
Purpose: User-facing quick start for the phylonames STEP_2 workflow.
History:
  2026-05-26  Updated for unified RUN-workflow.sh driver per §29
              (RUN-workflow.sbatch deprecated). Stale refs cleaned.
============================================================================ -->

# Phylonames Workflow — STEP_2 (apply user phylonames)

**STEP_2** applies your custom phylonames to override the NCBI-generated
phylonames from STEP_1.

## Prerequisites

1. Run STEP_1 first to generate initial phylonames
2. Review the STEP_1 taxonomy summary to identify species needing
   overrides (NOTINNCBI species, numbered clades, NCBI misclassifications)
3. Create `INPUT_user/user_phylonames.tsv` with your custom phylonames

## Quick Start

1. Copy the example:
   ```bash
   cp INPUT_user/user_phylonames_example.tsv INPUT_user/user_phylonames.tsv
   ```
2. Edit `INPUT_user/user_phylonames.tsv` with your custom phylonames
3. Edit `START_HERE-user_config.yaml` — set your project name (must
   match STEP_1) and `execution_mode` if running on SLURM
4. Run the workflow:
   ```bash
   bash RUN-workflow.sh
   ```
   The unified driver runs locally or self-submits to SLURM based on
   `execution_mode` in the YAML (per §29). There is no separate
   `RUN-workflow.sbatch`.

## User Phylonames Format

Tab-separated file with columns: `genus_species<TAB>custom_phyloname`

```
Monosiga_brevicollis_MX1	Holozoa_Choanozoa_Choanoflagellata_Craspedida_Salpingoecidae_Monosiga_brevicollis_MX1
Chromosphaera_perkinsii	Holozoa_Ichthyosporea_Ichthyophonida_Chromosphaeraceae_Chromosphaera_perkinsii
```

## Results

- **Final mapping** in `OUTPUT_pipeline/1-output/` symlinked to
  `../../output_to_input/STEP_2-apply_user_phylonames/maps/` and to
  `../../output_to_input/maps/` (convenience symlink)
- **Unofficial clades report** in `OUTPUT_pipeline/1-output/`
- **Updated taxonomy summary** (Markdown + HTML) in `OUTPUT_pipeline/2-output/`

## UNOFFICIAL Marking

By default, clades that differ from NCBI get an "UNOFFICIAL" suffix to
maintain transparency about data sources. Set `mark_unofficial: false`
in `START_HERE-user_config.yaml` to disable.

## Publishing to the data server

This workflow's `upload_manifest.tsv` (in this directory) describes
which outputs publish to the project data server. The actual publish is
triggered at the subproject level:
```bash
bash ../../RUN-update_upload_to_server.sh
```
which invokes the shared helper at
`gigantic_project-COPYME/server/ai/update_upload_to_server.py` and
assembles `phylonames/upload_to_server/STEP_2-apply_user_phylonames/...`
(per §38).

## Need Help?

Ask your AI assistant to read `ai/AI_GUIDE.md` for detailed guidance.
