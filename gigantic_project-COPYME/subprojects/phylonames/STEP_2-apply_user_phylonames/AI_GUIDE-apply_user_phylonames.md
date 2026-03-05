# AI_GUIDE-apply_user_phylonames.md (Level 2: STEP Guide)

**For AI Assistants**: Read `../AI_GUIDE-phylonames.md` first for subproject overview and phylonames concepts. This guide covers the STEP 2 workflow.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE-project.md` |
| Phylonames concepts, numbered clades, user phylonames | `../AI_GUIDE-phylonames.md` |
| STEP 2 overview | This file |
| Running the workflow | `workflow-COPYME-apply_user_phylonames/ai/AI_GUIDE-apply_user_phylonames_workflow.md` |

## STEP 2: Apply User Phylonames

Applies user-provided custom phylonames to override the NCBI-generated phylonames from STEP 1. Clades that differ from NCBI are marked UNOFFICIAL for transparency.

**This is STEP 2 of a 2-STEP workflow:**
- **STEP 1**: Generate phylonames from NCBI taxonomy. User reviews output.
- **STEP 2 (this)**: Apply user-provided custom phylonames after review.

**Input**: STEP 1 mapping (from `output_to_input/STEP_1-generate_and_evaluate/maps/`) + user phylonames TSV

**Output**: Updated mapping with user overrides and UNOFFICIAL marking

## Pipeline Scripts (3 steps)

| # | Script | Purpose |
|---|--------|---------|
| 001 | `001_ai-python-apply_user_phylonames.py` | Apply user phylonames with UNOFFICIAL marking |
| 002 | `002_ai-python-generate_taxonomy_summary.py` | Generate updated taxonomy summary (MD + HTML) |
| 003 | `003_ai-python-write_run_log.py` | Write run log to research notebook |

## Configuration

Edit `workflow-COPYME-apply_user_phylonames/phylonames_config.yaml`:
- `project_name`: Must match STEP 1 project name
- `user_phylonames`: Path to your custom phylonames TSV
- `mark_unofficial`: Whether to mark user clades as UNOFFICIAL (default: true)

## Inter-STEP Data Flow

STEP 2 reads from `output_to_input/STEP_1-generate_and_evaluate/maps/` (GIGANTIC convention: between STEPs, read from subproject-level output_to_input, not from another STEP's OUTPUT_pipeline).
