# AI Guide: STEP_3-databases (genomesDB)

**For AI Assistants**: This guide covers STEP_3 of the genomesDB subproject. For genomesDB overview and four-step architecture, see `../AI_GUIDE.md`. For GIGANTIC overview, see `../../../AI_GUIDE.md`.

**Location**: `gigantic_project-COPYME/subprojects/genomesDB/STEP_3-databases/`

---

## CRITICAL: Surface Discrepancies - No Silent Changes

**The user is managing this project - you must surface discrepancies so the user can make decisions. Silent changes undermine project management.**

- NEVER silently do something different than requested
- NEVER assume you know better and proceed without asking
- ALWAYS stop and explain the discrepancy
- ALWAYS ask for clarification before proceeding

---

## Quick Reference

| User needs... | Go to... |
|---|---|
| GIGANTIC overview, directory structure | `../../../AI_GUIDE.md` |
| genomesDB concepts, four-step structure | `../AI_GUIDE.md` |
| STEP_2 (prerequisite — provides proteomes) | `../STEP_2-standardize_and_evaluate/AI_GUIDE.md` |
| STEP_3 databases concepts (this file) | This file |
| Running the STEP_3 workflow | `workflow-COPYME-build_gigantic_genomesDB/ai/AI_GUIDE.md` |
| STEP_4 (next — assembles final species set) | `../STEP_4-create_final_species_set/AI_GUIDE.md` |

---

## What This Step Does

**Purpose**: Build per-species BLAST protein databases from STEP_2's cleaned, phyloname-standardized proteomes. Every species that passed STEP_2 gets its own individual BLAST database — flexible per-species searching, no all-vs-all merge.

## Inputs (what STEP_3 reads)

| Source | What | Where |
|---|---|---|
| STEP_2 standardized + cleaned proteomes | `phyloname-proteome.aa` FASTA files | `../../output_to_input/STEP_2-standardize_and_evaluate/gigantic_proteomes_cleaned/` |
| STEP_2 species selection manifest (optional) | Per-species `Include=YES/NO` flag from quality summary | `../../output_to_input/STEP_2-standardize_and_evaluate/6_ai-species_selection_manifest.tsv` |

## Outputs (what STEP_3 produces)

| Output | Location | Consumed by |
|---|---|---|
| Per-species BLAST databases (`.phr`, `.pin`, `.psq` etc., plus the `.aa` next to them) | `workflow-*/OUTPUT_pipeline/2-output/gigantic-T1-blastp/` | Published to `../../output_to_input/STEP_3-databases/gigantic-T1-blastp/` for STEP_4 to subset and copy |
| Filtered species manifest | `workflow-*/OUTPUT_pipeline/1-output/1_ai-filtered_species_manifest.tsv` | STEP_3 internal (script 002); audit trail |
| `makeblastdb` commands log | `workflow-*/OUTPUT_pipeline/2-output/2_ai-makeblastdb_commands.sh` | Reproducibility audit |

## Downstream consumers (per §40)

The per-species BLAST databases produced here flow through STEP_4 to:

- **trees_gene_families** STEP_1 — homolog discovery via RBH/RBF BLAST searches
- **trees_gene_groups** STEP_1 — same dependency

These are the main BLAST consumers; everyone else uses the standardized
proteomes from STEP_2 directly via STEP_4.

---

## Path Depth

From this step directory, project root is at `../../../`:

| Location | Relative path to project root |
|----------|-------------------------------|
| `STEP_3-databases/` | `../../../` |
| `STEP_3-databases/workflow-COPYME-*/` | `../../../../` |

---

## Research Notebook Location

Workflow run logs are saved to each workflow's `ai/logs/` directory. AI sessions are extracted project-wide to `research_notebook/research_ai/sessions/`.

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `workflow-*/START_HERE-user_config.yaml` | Workflow configuration | Optional |
| `output_to_input/` | BLAST databases | No |
| `../output_to_input/` | Shared with other subprojects | No |

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| No input files | STEP_2 not run | Run STEP_2-standardize_and_evaluate first |
| makeblastdb failed | BLAST+ not installed | Install BLAST+ tools |
| Empty database | No proteomes passed QC | Check STEP_2 evaluation reports |
| Disk full | Large database | Free disk space |

---

## Dependencies

- STEP_2-standardize_and_evaluate must complete first
- BLAST+ tools must be installed (available in `aiG-genomesDB` conda environment)

---

## Next Step

After STEP_3 completes, proceed to **STEP_4-create_final_species_set** to select and copy the final species set for downstream subprojects.
