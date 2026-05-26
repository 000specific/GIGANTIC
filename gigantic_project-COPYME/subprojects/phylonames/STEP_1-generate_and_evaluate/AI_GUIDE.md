# AI_GUIDE.md — phylonames STEP_1 (generate_and_evaluate)

**For AI Assistants**: Read `../AI_GUIDE.md` first for subproject overview
and phylonames concepts. This guide covers STEP_1.

| User needs... | Go to... |
|---|---|
| GIGANTIC overview | `../../../AI_GUIDE.md` (project root) |
| Phylonames concepts, numbered clades, user phylonames | `../AI_GUIDE.md` |
| STEP_1 overview (this file) | This file |
| Running the STEP_1 workflow | `workflow-COPYME-generate_phylonames/ai/AI_GUIDE.md` |
| STEP_2 (optional, follow-on) | `../STEP_2-apply_user_phylonames/AI_GUIDE.md` |

---

## STEP_1: Generate and Evaluate

Downloads the NCBI taxonomy database and generates phylogenetically-informative species identifiers that encode the complete taxonomic lineage.

**This is STEP_1 of a 2-STEP workflow:**
- **STEP_1 (this)**: Generate phylonames from NCBI taxonomy. User reviews output.
- **STEP_2** (optional): Apply user-provided custom phylonames (after reviewing STEP_1 output).

## Inputs (what STEP_1 reads)

| Source | What | Where |
|---|---|---|
| User species list | One species per line (`Genus_species`) | `../../INPUT_user/species_set/species_list.txt` (project default) OR workflow-local `workflow-COPYME-generate_phylonames/INPUT_user/species_list.txt` (override). RUN-workflow.sh prefers the workflow-local override; falls back to the project default. |
| NCBI taxonomy | `new_taxdump.tar.gz` | Downloaded fresh by script 001 from `ftp.ncbi.nih.gov` into `OUTPUT_pipeline/1-output/database-ncbi_taxonomy_YYYYMMDD_HHMMSS/`. Set `ncbi_taxonomy.force_download: false` in YAML to reuse an existing download. |

## Outputs (what STEP_1 produces)

| Output | Location | Consumed by |
|---|---|---|
| Master phylonames (all NCBI species) | `OUTPUT_pipeline/2-output/phylonames`, `phylonames_taxonid` | Generally just an intermediate; useful for inspection. |
| Project mapping (`genus_species` → `phyloname` → `phyloname_taxonid`) | `OUTPUT_pipeline/3-output/[project]_map-genus_species_X_phylonames.tsv` | **Symlinked into** `../../output_to_input/STEP_1-generate_and_evaluate/maps/` AND the convenience handle `../../output_to_input/maps/` (until STEP_2 runs and overtakes the convenience symlink). |
| Taxonomy summary (Markdown + HTML) | `OUTPUT_pipeline/4-output/[project]_taxonomy_summary.{md,html}` | Read by the user to decide whether to run STEP_2 (look for NOTINNCBI species and numbered clades). |
| Per-run audit log | `workflow-COPYME-generate_phylonames/ai/logs/run_*.log` | AI lab notebook (per-run); not consumed by downstream subprojects. |

## Pipeline Scripts (5)

| # | Script | Output dir | Purpose |
|---|---|---|---|
| 001 | `001_ai-bash-download_ncbi_taxonomy.sh` | `1-output/` | Download + extract NCBI taxonomy database |
| 002 | `002_ai-python-generate_phylonames.py` | `2-output/` | Generate phylonames for all NCBI species |
| 003 | `003_ai-python-create_species_mapping.py` | `3-output/` | Create project-specific mapping |
| 004 | `004_ai-python-generate_taxonomy_summary.py` | `4-output/` | Generate taxonomy summary (MD + HTML) |
| 005 | `005_ai-python-write_run_log.py` | `ai/logs/` | Write run log to AI lab notebook |

## Configuration

Edit `workflow-COPYME-generate_phylonames/START_HERE-user_config.yaml`:

| Key | Default | Notes |
|---|---|---|
| `project.name` | `"my_project"` | Used in output filenames; **STEP_2 must match this** |
| `project.species_list` | `INPUT_user/species_list.txt` | Path within the workflow dir |
| `ncbi_taxonomy.force_download` | `false` | Set to `true` to always re-download NCBI |
| `execution_mode` | `"local"` | Set to `"slurm"` to self-submit (§29) |
| `slurm_account`, `slurm_qos` | placeholders | Required when execution_mode is slurm |

## After Running STEP_1

Review the taxonomy summary in `OUTPUT_pipeline/4-output/` for:
- **NOTINNCBI species** — species missing from NCBI taxonomy entirely (placeholder phylonames)
- **Numbered clades** — e.g. `Kingdom6555` (NCBI gaps; meaningful names available from literature?)

If overrides are needed, proceed to STEP_2 (`../STEP_2-apply_user_phylonames/`).
Otherwise STEP_1's mapping is the final one and downstream subprojects
(genomesDB first, then orthogroups / annotations_hmms / trees_species / etc.)
can read it directly via `../../output_to_input/maps/`.
