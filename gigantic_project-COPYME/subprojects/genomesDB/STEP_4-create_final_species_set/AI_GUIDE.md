# AI Guide: STEP_4-create_final_species_set (genomesDB)

**For AI Assistants**: This guide covers STEP_4 of the genomesDB subproject. For genomesDB overview and pipeline architecture, see `../AI_GUIDE.md`. For GIGANTIC overview, see `../../../AI_GUIDE.md`.

**Location**: `gigantic_project-COPYME/subprojects/genomesDB/STEP_4-create_final_species_set/`

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
| genomesDB concepts, pipeline architecture | `../AI_GUIDE.md` |
| STEP_2 (prerequisite — provides cleaned proteomes) | `../STEP_2-standardize_and_evaluate/AI_GUIDE.md` |
| STEP_3 (prerequisite — provides BLAST databases) | `../STEP_3-databases/AI_GUIDE.md` |
| STEP_4 concepts and troubleshooting (this file) | This file |
| Running the STEP_4 workflow | `workflow-COPYME-create_final_species_set/ai/AI_GUIDE.md` |

---

## Purpose of STEP_4

STEP_4 is the **final step** in the genomesDB pipeline. It creates the definitive species set that all downstream subprojects use.

**What it does**: Selects and copies proteomes (from STEP_2), BLAST databases (from STEP_3), and genome annotations (from STEP_2) based on user configuration. This is a **copy/filter** step, not a processing step.

**Why a separate step?** After STEP_2 evaluates genome/proteome quality, the user may want to exclude certain species (poor assembly quality, contamination, etc.). STEP_4 gives the user explicit control over which species enter the downstream analyses.

## Inputs (what STEP_4 reads)

| Source | What | Where |
|---|---|---|
| STEP_2 cleaned proteomes | `phyloname-proteome.aa` files | `../../output_to_input/STEP_2-standardize_and_evaluate/gigantic_proteomes_cleaned/` |
| STEP_3 per-species BLAST databases | `phyloname-proteome.aa.{phr,pin,psq,...}` | `../../output_to_input/STEP_3-databases/gigantic-T1-blastp/` |
| STEP_2 standardized genome annotations | `phyloname-genome_annotations.gff3` | `../../output_to_input/STEP_2-standardize_and_evaluate/gigantic_genome_annotations/` |
| User species selection (optional) | One species per line; defaults to ALL STEP_2 species if absent | `workflow-*/INPUT_user/selected_species.txt` |

## Outputs (what STEP_4 produces)

Output directory names embed the species count as `speciesN_` (e.g.
`species71_gigantic_T1_proteomes/`). N is computed automatically by
script 001.

| Output | Location | Consumed by |
|---|---|---|
| Final proteomes | `../../output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/` | `orthogroups`, `annotations_hmms`, `gene_sizes`, `secretome`, `hotspots`, `one_direction_homologs`, `dark_proteomes`, etc. |
| Final BLAST databases | `../../output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_blastp/` | `trees_gene_families` STEP_1, `trees_gene_groups` STEP_1 (homolog discovery) |
| Final genome annotations | `../../output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_genome_annotations/` | `gene_sizes`, anything reasoning about gene coordinates / introns |
| Per-species sequence tables | `../../output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_sequence_tables/` | `integrator/BLOCK_species_X_all_annotations` (per-protein spine), and anything needing id + amino acid sequence in one TSV |
| Copy manifest | `workflow-*/OUTPUT_pipeline/2-output/2_ai-copy_manifest.tsv` | Reproducibility audit |

## Downstream consumers (per §40)

**Every "real" GIGANTIC subproject reads from this STEP's
`output_to_input/`.** This is the final handoff from genomesDB to the
rest of the platform. See the subproject-level AI_GUIDE's "Downstream
consumers" section for the comprehensive list with per-subproject usage
patterns.

## Prerequisites

| Prerequisite | Why | How to verify |
|---|---|---|
| STEP_2 complete | Provides cleaned, standardized proteomes | `ls ../../output_to_input/STEP_2-standardize_and_evaluate/gigantic_proteomes_cleaned/` should be non-empty |
| STEP_3 complete | Provides BLAST databases | `ls ../../output_to_input/STEP_3-databases/gigantic-T1-blastp/` should be non-empty |
| User evaluation | User decides which species to keep (or accepts the default of all) | User reviews STEP_2 quality metrics (`6_ai-comprehensive_quality_summary.tsv`); optionally edits `INPUT_user/selected_species.txt` |

---

## Data Flow

```
STEP_2 (cleaned proteomes)  ──┐
                               ├──> STEP_4 (select + copy ──> output_to_input/
STEP_3 (BLAST databases)   ──┘       + build seq tables)        ├── speciesN_gigantic_T1_proteomes/
                                                                  ├── speciesN_gigantic_T1_blastp/
                                                                  ├── speciesN_gigantic_genome_annotations/
                                                                  └── speciesN_gigantic_T1_sequence_tables/
                                                                         │
                                                                         └──> downstream subprojects
                                                                              (orthogroups, gene_trees, integrator, etc.)
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `workflow-*/START_HERE-user_config.yaml` | Paths to STEP_2 and STEP_3 outputs | **YES** (required) |
| `workflow-*/INPUT_user/selected_species.txt` | Species selection list | **YES** (optional - defaults to all) |
| `workflow-*/RUN-workflow.sh` | Local execution script (unified driver §29) | No |
| `workflow-*/ai/scripts/001_ai-python-validate_species_selection.py` | Validates species selection against STEP_2 + STEP_3 | No (AI-generated) |
| `workflow-*/ai/scripts/002_ai-python-copy_selected_files.py` | Copies selected proteomes + BLAST DBs + annotations | No (AI-generated) |
| `workflow-*/ai/scripts/003_ai-python-build_per_species_sequence_tables.py` | Builds per-species (id + sequence) TSV tables into `3-output/speciesN_gigantic_T1_sequence_tables/` | No (AI-generated) |
| `workflow-*/ai/scripts/004_ai-python-write_run_log.py` | Per-run audit log (§45 canonical final) | No (AI-generated) |
| `output_to_input/STEP_4-create_final_species_set/` | Final species set for downstream subprojects | No (auto-populated) |
| `../RUN-update_upload_to_server.sh` (subproject-level) | Manage upload_to_server/ symlinks | No |

---

## The speciesN Naming Convention

STEP_4 outputs use a `speciesN_` prefix where N is the count of selected species:

- `species71_gigantic_T1_proteomes/` - 71 species were selected
- `species71_gigantic_T1_blastp/` - 71 species were selected

This convention makes it immediately clear how many species are in the final set, and downstream subprojects can reference the correct directory.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "STEP_2 proteomes not found" | Config path wrong or STEP_2 not run | Verify path in `START_HERE-user_config.yaml`; run STEP_2 first |
| "STEP_3 BLAST databases not found" | Config path wrong or STEP_3 not run | Verify path in `START_HERE-user_config.yaml`; run STEP_3 first |
| "Species X not found in STEP_2" | Species in selection file but not in STEP_2 output | Check spelling in `selected_species.txt`; verify STEP_2 processed this species |
| "Species X not found in STEP_3" | Species in STEP_2 but missing from STEP_3 | Run STEP_3 for missing species; or remove from selection |
| "No species selected" | Empty selection file | Delete the file (defaults to all species) or add species names |
| "Permission denied" during copy | Insufficient permissions on source or target | Check file permissions with `ls -la` |
| output_to_input/ empty after run | Workflow may not have completed | Check workflow logs; re-run if needed |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| User says "run STEP_4" | "Have STEP_2 and STEP_3 completed? Do you want all species or a subset?" |
| User mentions species filtering | "Do you want to create INPUT_user/selected_species.txt with specific species, or start with all and remove some?" |
| Species count mismatch | "STEP_2 has N proteomes but STEP_3 has M databases. Some species may be missing from one. Should we proceed with the intersection?" |
| User asks about downstream | "STEP_4 outputs go to output_to_input/. Which downstream subproject do you want to configure next?" |

---

## Path Depth

From this step directory, project root is at `../../../`:

| Location | Relative path to project root |
|----------|-------------------------------|
| `STEP_4-create_final_species_set/` | `../../../` |
| `STEP_4-create_final_species_set/workflow-COPYME-*/` | `../../../../` |

---

## Research Notebook Location

Workflow run logs are saved to each workflow's `ai/logs/` directory. AI sessions are extracted project-wide to `research_notebook/research_ai/sessions/`.

---

## Directory Structure

```
STEP_4-create_final_species_set/
├── README.md                              # Human-readable overview
├── AI_GUIDE.md   # THIS FILE
├── RUN-update_upload_to_server.sh         # Manage upload_to_server/ symlinks
├── output_to_input/                       # Final species set for downstream
│   ├── speciesN_gigantic_T1_proteomes/        # Created by workflow (2-output)
│   ├── speciesN_gigantic_T1_blastp/           # Created by workflow (2-output)
│   ├── speciesN_gigantic_genome_annotations/  # Created by workflow (2-output, subset)
│   └── speciesN_gigantic_T1_sequence_tables/  # Created by workflow (3-output)
├── upload_to_server/                      # Curated data for GIGANTIC server
└── workflow-COPYME-create_final_species_set/
    ├── README.md
    ├── RUN-workflow.sh
    ├── START_HERE-user_config.yaml
    ├── INPUT_user/
    │   └── selected_species.txt           # User species selection (optional)
    ├── OUTPUT_pipeline/
    │   ├── 1-output/                      # Validated species list
    │   ├── 2-output/                      # Copied species files (proteomes, blastp, annotations)
    │   └── 3-output/                      # Per-species sequence tables + summary
    └── ai/
        ├── AI_GUIDE.md
        ├── main.nf
        ├── nextflow.config
        ├── conda_environment.yml          # env: aiG-genomesDB (shared across all 4 STEPs)
        ├── logs/                          # Per-run audit logs from script 004
        └── scripts/
            ├── 001_ai-python-validate_species_selection.py
            ├── 002_ai-python-copy_selected_files.py
            ├── 003_ai-python-build_per_species_sequence_tables.py
            └── 004_ai-python-write_run_log.py
```
