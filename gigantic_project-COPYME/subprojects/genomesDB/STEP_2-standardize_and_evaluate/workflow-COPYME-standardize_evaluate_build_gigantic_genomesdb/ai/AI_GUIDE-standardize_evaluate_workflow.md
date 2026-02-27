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
| GIGANTIC overview, directory structure | `../../../../AI_GUIDE-project.md` |
| genomesDB subproject overview | `../../AI_GUIDE-standardize_and_evaluate.md` |
| Running this workflow | This file |

---

## Purpose

This workflow applies GIGANTIC phyloname conventions to data from STEP_1 and calculates quality metrics. It prepares data for STEP_3 database building.

---

## Workflow Scripts

| Script | Purpose | Required Inputs |
|--------|---------|-----------------|
| 001 | Standardize proteome filenames and FASTA headers | Phylonames mapping, T1 proteomes from STEP_1 |
| 002 | Create phyloname symlinks for genomes/annotations | Phylonames mapping, genomes, gene annotations from STEP_1 |
| 003 | Calculate genome assembly statistics (gfastats) | Phyloname-named genomes from script 002 |

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
# Edit SLURM-workflow.sbatch to set --account and --qos
sbatch SLURM-workflow.sbatch
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
| `OUTPUT_pipeline/2-output/gigantic_genomes/` | Phyloname symlinks to genomes |
| `OUTPUT_pipeline/2-output/gigantic_gene_annotations/` | Phyloname symlinks to annotations |
| `OUTPUT_pipeline/3-output/3_ai-genome_assembly_statistics.tsv` | Assembly quality metrics |

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
| `SLURM-workflow.sbatch` | Yes (account/qos) | SLURM job wrapper |
| `ai/scripts/001_*.py` | No | Proteome standardization |
| `ai/scripts/002_*.py` | No | Genome/annotation symlink creation |
| `ai/scripts/003_*.py` | No | Assembly statistics |

---

## Data Flow

```
STEP_1-sources/output_to_input/
├── T1_proteomes/         ──► Script 001 ──► 1-output/gigantic_proteomes/
├── genomes/              ──► Script 002 ──► 2-output/gigantic_genomes/ ──► Script 003 ──► 3-output/stats
└── gene_annotations/     ──► Script 002 ──► 2-output/gigantic_gene_annotations/

phylonames/output_to_input/maps/
└── species71_map*.tsv    ──► Scripts 001, 002, 003 (all need phylonames)
```

---

## Passing Data to STEP_3

After this workflow completes, STEP_3 will use:
- `OUTPUT_pipeline/1-output/gigantic_proteomes/` for building BLAST databases
