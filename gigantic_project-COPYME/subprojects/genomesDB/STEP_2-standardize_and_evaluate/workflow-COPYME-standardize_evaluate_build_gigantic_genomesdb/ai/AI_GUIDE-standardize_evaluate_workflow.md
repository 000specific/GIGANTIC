# AI_GUIDE - STEP_2 Standardize and Evaluate Workflow

**AI**: Claude Code | Opus 4.5 | 2026 February 26
**Human**: Eric Edsinger

---

## ⚠️ CRITICAL: Surface Discrepancies - No Silent Changes

**The user is managing this project - you must surface discrepancies so the user can make decisions. Silent changes undermine project management.**

- ❌ **NEVER** silently do something different than requested
- ❌ **NEVER** assume you know better and proceed without asking
- ✅ **ALWAYS** stop and explain the discrepancy
- ✅ **ALWAYS** ask for clarification before proceeding

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../../../../AI_GUIDE-project.md` |
| genomesDB subproject overview | `../../../AI_GUIDE-genomesDB.md` |
| STEP_2 concepts, troubleshooting | `../../AI_GUIDE-standardize_and_evaluate.md` |
| Running this workflow | This file |

---

## Purpose

This workflow applies GIGANTIC phyloname conventions to data from STEP_1 and calculates quality metrics. It prepares data for STEP_3 database building.

---

## Workflow Scripts

| Script | Purpose | Required Inputs |
|--------|---------|-----------------|
| 001 | Standardize proteome filenames and FASTA headers | Phylonames mapping, T1 proteomes from STEP_1 |
| 002 | Clean proteome invalid residues ('.' to 'X') | Standardized proteomes from script 001 |
| 003 | Create phyloname symlinks for genomes/annotations | Phylonames mapping, genomes, gene annotations from STEP_1 |
| 004 | Calculate genome assembly statistics (gfastats) | Phyloname-named genomes from script 003 |
| 005 | Run BUSCO proteome evaluation | Cleaned proteomes from script 002, lineage assignments |
| 006 | Summarize quality and generate species manifest | All quality data from scripts 001-005 |

---

## Prerequisites

**Required before running:**

1. **STEP_1-sources** must be complete
   - Check: `../../STEP_1-sources/output_to_input/T1_proteomes/` has proteome files

2. **phylonames subproject** must be complete
   - Check: `../../phylonames/output_to_input/maps/species71_map-genus_species_X_phylonames.tsv` exists

3. **Conda environment** (for script 003):
   - Environment: `ai_gigantic_genomesdb`
   - Required tool: `gfastats`

---

## Running the Workflow

**Local execution:**
```bash
cd workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/
bash RUN-workflow.sh
```

**SLURM execution:**
```bash
cd workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/
# Edit RUN-workflow.sbatch to set --account and --qos
sbatch RUN-workflow.sbatch
```

---

## Inputs

This workflow does NOT require direct user inputs in `INPUT_user/`. All inputs come from:

| Input | Source |
|-------|--------|
| Phylonames mapping | `../../phylonames/output_to_input/maps/` |
| T1 proteomes | `../../STEP_1-sources/output_to_input/T1_proteomes/` |
| Genomes | `../../STEP_1-sources/output_to_input/genomes/` |
| Gene annotations | `../../STEP_1-sources/output_to_input/gene_annotations/` |

---

## Outputs

| Location | Contents |
|----------|----------|
| `OUTPUT_pipeline/1-output/gigantic_proteomes/` | Phyloname-standardized proteome files |
| `OUTPUT_pipeline/1-output/1_ai-standardization_manifest.tsv` | Proteome transformation log |
| `OUTPUT_pipeline/2-output/gigantic_proteomes_cleaned/` | Cleaned proteomes (ready for BLAST/BUSCO) |
| `OUTPUT_pipeline/3-output/gigantic_genomes/` | Phyloname symlinks to genomes |
| `OUTPUT_pipeline/3-output/gigantic_gene_annotations/` | Phyloname symlinks to annotations |
| `OUTPUT_pipeline/4-output/4_ai-genome_assembly_statistics.tsv` | Assembly quality metrics |
| `OUTPUT_pipeline/5-output/5_ai-busco_summary.tsv` | Proteome completeness scores |
| `OUTPUT_pipeline/6-output/6_ai-quality_summary.tsv` | Combined quality metrics |
| `OUTPUT_pipeline/6-output/6_ai-species_selection_manifest.tsv` | Species selection for STEP_3/STEP_4 |

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "Phylonames mapping not found" | phylonames subproject not run | Run phylonames first |
| "Input proteomes directory not found" | STEP_1-sources not run | Run STEP_1 first |
| "genus_species not found in phylonames mapping" | Species mismatch | Check spelling in STEP_1 sources vs phylonames |
| gfastats command not found | Conda environment not activated | `conda activate ai_gigantic_genomesdb` |

---

## Key Files

| File | User Edits? | Description |
|------|-------------|-------------|
| `RUN-workflow.sh` | No | Main workflow script |
| `RUN-workflow.sbatch` | Yes (account/qos) | SLURM job wrapper |
| `standardize_evaluate_config.yaml` | Yes (project settings) | User-editable configuration |
| `INPUT_user/busco_lineages.txt` | Yes (lineage assignments) | BUSCO lineage per species |
| `ai/scripts/001_*.py` | No | Proteome standardization |
| `ai/scripts/002_*.py` | No | Proteome cleaning |
| `ai/scripts/003_*.py` | No | Genome/annotation symlink creation |
| `ai/scripts/004_*.py` | No | Assembly statistics (gfastats) |
| `ai/scripts/005_*.py` | No | BUSCO proteome evaluation |
| `ai/scripts/006_*.py` | No | Quality summary and species manifest |

---

## Data Flow

```
STEP_1-sources/output_to_input/
├── T1_proteomes/         ──► Script 001 ──► 1-output/gigantic_proteomes/
│                                                      │
│                                            Script 002 ──► 2-output/gigantic_proteomes_cleaned/
│                                                                    │
│                                                          Script 005 ──► 5-output/busco_summary
│
├── genomes/              ──► Script 003 ──► 3-output/gigantic_genomes/
│                                                      │
│                                            Script 004 ──► 4-output/assembly_stats
│
└── gene_annotations/     ──► Script 003 ──► 3-output/gigantic_gene_annotations/

phylonames/output_to_input/maps/
└── species71_map*.tsv    ──► Scripts 001, 003 (need phylonames)

All quality data ──► Script 006 ──► 6-output/quality_summary + species_manifest
```

---

## Passing Data to STEP_3 and STEP_4

After this workflow completes:
- **STEP_3** will use cleaned proteomes from `OUTPUT_pipeline/2-output/gigantic_proteomes_cleaned/` for building BLAST databases
- **STEP_4** will use the species selection manifest from `OUTPUT_pipeline/6-output/6_ai-species_selection_manifest.tsv` and cleaned proteomes
