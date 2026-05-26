<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26
Human:   Eric Edsinger
Purpose: User-facing quick start for the phylonames STEP_1 workflow.
History:
  2026-05-26  Updated for unified RUN-workflow.sh driver per §29
              (RUN-workflow.sbatch deprecated). Stale refs cleaned.
============================================================================ -->

# Phylonames Workflow — STEP_1 (generate and evaluate)

Generate standardized phylogenetic names from NCBI taxonomy.

This is **STEP_1** of the 2-STEP phylonames architecture. It downloads
NCBI taxonomy, generates phylonames for all species, creates your
project-specific mapping, and produces a taxonomy summary for review.

## Quick Start

1. Edit `START_HERE-user_config.yaml` with your project name (and
   `execution_mode: "slurm"` + `slurm.*` settings if running on HPC).
2. Put your species list in `INPUT_user/species_list.txt` (one species
   per line, e.g., `Homo_sapiens`). If absent at runtime, the workflow
   copies in the project default from
   `gigantic_project-*/INPUT_user/species_set/species_list.txt`.
3. Run the workflow:
   ```bash
   bash RUN-workflow.sh
   ```
   The unified driver runs locally or self-submits to SLURM based on
   `execution_mode` in the YAML (per §29). There is no separate
   `RUN-workflow.sbatch`.

## Results

- **Project mapping** in `OUTPUT_pipeline/3-output/` is symlinked to:
  - `../../output_to_input/STEP_1-generate_and_evaluate/maps/`
    (canonical STEP_1 location consumed by downstream subprojects)
  - `../../output_to_input/maps/` (convenience symlink pointing at the
    most recent STEP's output)
- **Taxonomy summary** (Markdown + HTML) in `OUTPUT_pipeline/4-output/`
  shows:
  - Taxonomic distribution (species counts by kingdom/phylum)
  - NOTINNCBI species (species missing from NCBI)
  - Numbered clades (NCBI taxonomy gaps you may want to override)

## After Running

Review the taxonomy summary to identify species that received NOTINNCBI
placeholders or numbered clades. If overrides are needed, run **STEP_2**
to apply user-defined phylonames on top of the STEP_1 output.

## Publishing to the data server

This workflow's `upload_manifest.tsv` (in this directory) describes which
outputs publish to the project data server. The actual publish is
triggered at the subproject level:
```bash
bash ../../RUN-update_upload_to_server.sh
```
which invokes the shared helper at
`gigantic_project-COPYME/server/ai/update_upload_to_server.py` and
assembles `phylonames/upload_to_server/STEP_1-generate_and_evaluate/...`
(per §38).

## Need Help?

Ask your AI assistant to read `ai/AI_GUIDE.md` for detailed guidance.
