# AI_GUIDE-generate_and_evaluate.md (Level 2: STEP Guide)

**For AI Assistants**: Read `../AI_GUIDE-phylonames.md` first for subproject overview and phylonames concepts. This guide covers the STEP 1 workflow.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE-project.md` |
| Phylonames concepts, numbered clades, user phylonames | `../AI_GUIDE-phylonames.md` |
| STEP 1 overview | This file |
| Running the workflow | `workflow-COPYME-generate_phylonames/ai/AI_GUIDE-phylonames_workflow.md` |

## STEP 1: Generate and Evaluate

Downloads the NCBI taxonomy database and generates phylogenetically-informative species identifiers that encode the complete taxonomic lineage.

**This is STEP 1 of a 2-STEP workflow:**
- **STEP 1 (this)**: Generate phylonames from NCBI taxonomy. User reviews output.
- **STEP 2**: Apply user-provided custom phylonames (after reviewing STEP 1 output).

**Input**: Species list (e.g., `Homo_sapiens`, `Octopus_bimaculoides`)

**Output**: Mapping of `genus_species` to `phyloname` to `phyloname_taxonid`

## Pipeline Scripts (5 steps)

| # | Script | Purpose |
|---|--------|---------|
| 001 | `001_ai-bash-download_ncbi_taxonomy.sh` | Download NCBI taxonomy database |
| 002 | `002_ai-python-generate_phylonames.py` | Generate phylonames for all NCBI species |
| 003 | `003_ai-python-create_species_mapping.py` | Create project-specific mapping |
| 004 | `004_ai-python-generate_taxonomy_summary.py` | Generate taxonomy summary (MD + HTML) |
| 005 | `005_ai-python-write_run_log.py` | Write run log to research notebook |

## Configuration

Edit `workflow-COPYME-generate_phylonames/phylonames_config.yaml`:
- `project_name`: Your project name (used in output filenames)

## After Running STEP 1

Review the taxonomy summary in `OUTPUT_pipeline/4-output/` for:
- **NOTINNCBI species**: Not found in NCBI taxonomy (need custom phylonames)
- **Numbered clades**: e.g., Kingdom6555 (could use meaningful names)

If changes are needed, proceed to STEP 2: `../STEP_2-apply_user_phylonames/`
