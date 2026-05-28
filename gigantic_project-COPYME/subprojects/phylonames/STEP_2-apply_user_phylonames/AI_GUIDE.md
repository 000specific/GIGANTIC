# AI_GUIDE.md — phylonames STEP_2 (apply_user_phylonames)

**For AI Assistants**: Read `../AI_GUIDE.md` first for subproject overview
and phylonames concepts. This guide covers STEP_2.

| User needs... | Go to... |
|---|---|
| GIGANTIC overview | `../../../AI_GUIDE.md` (project root) |
| Phylonames concepts, numbered clades, user phylonames | `../AI_GUIDE.md` |
| STEP_1 (must run first) | `../STEP_1-generate_and_evaluate/AI_GUIDE.md` |
| STEP_2 overview (this file) | This file |
| Running the STEP_2 workflow | `workflow-COPYME-apply_user_phylonames/ai/AI_GUIDE.md` |
| INPUT_user staging arena for `user_phylonames.tsv` | `../../../INPUT_user/phylonames/README.md` |

---

## STEP_2: Apply User Phylonames

Applies user-provided custom phylonames to override the NCBI-generated phylonames from STEP_1. Clades that differ from NCBI are marked `UNOFFICIAL` for transparency.

**This is STEP_2 of a 2-STEP workflow:**
- **STEP_1**: Generate phylonames from NCBI taxonomy. User reviews output.
- **STEP_2 (this)**: Apply user-provided custom phylonames after review.

## Inputs (what STEP_2 reads)

| Source | What | Where |
|---|---|---|
| STEP_1 mapping (prerequisite) | 5 columns: `genus_species`, `phyloname`, `phyloname_taxonid`, `source` (always `NCBI` from STEP_1), `original_ncbi_phyloname` (same as `phyloname` from STEP_1) — uniform schema with STEP_2's own output | `../../output_to_input/STEP_1-generate_and_evaluate/maps/[project]_map-*.tsv` (per §2: read from the subproject's output_to_input, NOT another STEP's OUTPUT_pipeline) |
| User overrides | TSV of `genus_species` ↔ `custom_phyloname` | Canonical: stage at `../../../INPUT_user/phylonames/user_phylonames.tsv` (symlink into the user sandbox). Workflow-local: `workflow-COPYME-apply_user_phylonames/INPUT_user/user_phylonames.tsv`. |

## Outputs (what STEP_2 produces)

| Output | Location | Consumed by |
|---|---|---|
| Final project mapping (NCBI + user overrides + UNOFFICIAL marking) | `OUTPUT_pipeline/1-output/final_project_mapping.tsv` | **Symlinked into** `../../output_to_input/STEP_2-apply_user_phylonames/maps/` AND the convenience handle `../../output_to_input/maps/` (which now overrides STEP_1's contribution to the convenience symlink). |
| UNOFFICIAL clades report | `OUTPUT_pipeline/1-output/*_unofficial_clades_report.tsv` | User review — shows exactly which clades the user changed away from NCBI. |
| Updated taxonomy summary (Markdown + HTML) | `OUTPUT_pipeline/2-output/[project]_taxonomy_summary.{md,html}` | User review — reflects the post-override taxonomy. |
| Per-run audit log | `workflow-COPYME-apply_user_phylonames/ai/logs/run_*.log` | AI lab notebook (per-run); not consumed by downstream subprojects. |

## Pipeline Scripts (3)

| # | Script | Output dir | Purpose |
|---|---|---|---|
| 001 | `001_ai-python-apply_user_phylonames.py` | `OUTPUT_pipeline/1-output/` | Apply user phylonames; mark UNOFFICIAL where divergent |
| 002 | `002_ai-python-generate_taxonomy_summary.py` | `OUTPUT_pipeline/2-output/` | Generate updated taxonomy summary (MD + HTML) |
| 003 | `003_ai-python-write_run_log.py` | `ai/logs/` | Write run log to AI lab notebook |

## Configuration

Edit `workflow-COPYME-apply_user_phylonames/START_HERE-user_config.yaml`:

| Key | Default | Notes |
|---|---|---|
| `project.name` | `"my_project"` | **Must match STEP_1** |
| `project.step1_mapping` | `../../output_to_input/STEP_1-generate_and_evaluate/maps` | Usually no need to change |
| `project.user_phylonames` | `INPUT_user/user_phylonames.tsv` | Path within the workflow dir |
| `project.mark_unofficial` | `true` | Set `false` to suppress UNOFFICIAL marking |
| `execution_mode` | `"local"` | Set to `"slurm"` to self-submit (§29) |
| `slurm_account`, `slurm_qos` | placeholders | Required when execution_mode is slurm |

## Inter-STEP convention

Between STEPs, GIGANTIC reads from the subproject-level
`output_to_input/`, NOT from another STEP's `OUTPUT_pipeline/` (§2). That
keeps STEP boundaries clean: STEP_2 cannot accidentally couple to
STEP_1's internal layout.

## After Running STEP_2

The convenience symlink at `../../output_to_input/maps/` now points at
STEP_2's mapping, so downstream subprojects (genomesDB, orthogroups,
annotations_hmms, trees_species, etc.) automatically pick up the
user-overridden version with no further action.
