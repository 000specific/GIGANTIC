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
| GIGANTIC overview, directory structure | `../../../../../AI_GUIDE.md` |
| genomesDB subproject overview | `../../../AI_GUIDE.md` |
| STEP_2 concepts, troubleshooting | `../../AI_GUIDE.md` |
| Running this workflow | This file |

---

## Purpose

This workflow applies GIGANTIC phyloname conventions to data from STEP_1 and calculates quality metrics. It prepares data for STEP_3 database building.

---

## Workflow Scripts (7)

| Script | Purpose | Required Inputs |
|---|---|---|
| 001 | Standardize proteome filenames and FASTA headers | Phylonames mapping, T1 proteomes from STEP_1 |
| 002 | Clean proteome invalid residues ('.' to 'X') | Standardized proteomes from script 001 |
| 003 | Create phyloname symlinks for genomes/annotations | Phylonames mapping, genomes, genome annotations from STEP_1 |
| 004 | Calculate genome assembly statistics (gfastats) | Phyloname-named genomes from script 003 |
| 005 | Run BUSCO proteome evaluation (skipped if `busco.enabled: false` in YAML) | Cleaned proteomes from script 002, lineage assignments |
| 006 | Comprehensive quality summary (BUSCO + gfastats + proteome counts merged) | Outputs from 001, 004, 005 |
| 007 | Per-run audit log | n/a |

**Note**: Earlier docs claimed script 006 also generated a
"species selection manifest" — it does not. STEP_2 produces only the
comprehensive quality summary. Species selection is the user's call in
STEP_4 (`INPUT_user/selected_species.txt`). STEP_3 builds BLAST DBs
for every species; filtering happens only in STEP_4.

---

## Prerequisites

**Required before running:**

1. **STEP_1-sources** must be complete
   - Check: `../../output_to_input/STEP_1-sources/T1_proteomes/` has proteome files

2. **phylonames subproject** must be complete
   - Check: `../../phylonames/output_to_input/maps/{project_name}_map-genus_species_X_phylonames.tsv` exists

3. **Conda environment** (for script 003):
   - Environment: `aiG-genomesDB`
   - Required tool: `gfastats`

---

## Running the Workflow

**Local execution:**
```bash
cd workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/
bash RUN-workflow.sh
```

**SLURM execution:** Edit `START_HERE-user_config.yaml`, set `execution_mode: "slurm"` and fill in `slurm_account` / `slurm_qos`, then:
```bash
cd workflow-COPYME-standardize_evaluate_build_gigantic_genomesdb/
bash RUN-workflow.sh   # self-submits to SLURM
```

---

## Inputs

This workflow does NOT require direct user inputs in `INPUT_user/`. All inputs come from:

| Input | Source |
|-------|--------|
| Phylonames mapping | `../../phylonames/output_to_input/maps/` |
| T1 proteomes | `../../output_to_input/STEP_1-sources/T1_proteomes/` |
| Genomes | `../../output_to_input/STEP_1-sources/genomes/` |
| Genome annotations | `../../output_to_input/STEP_1-sources/genome_annotations/` |

---

## Outputs

| Location | Contents |
|---|---|
| `OUTPUT_pipeline/1-output/gigantic_proteomes/` | Phyloname-standardized proteome files |
| `OUTPUT_pipeline/1-output/1_ai-standardization_manifest.tsv` | Proteome transformation log |
| `OUTPUT_pipeline/2-output/gigantic_proteomes_cleaned/` | Cleaned proteomes (ready for BLAST/BUSCO) |
| `OUTPUT_pipeline/2-output/2_ai-proteome_cleaning_summary.tsv` + `2_ai-proteome_residue_corrections.tsv` | Audit of '.' → 'X' substitutions |
| `OUTPUT_pipeline/3-output/gigantic_genomes/` | Phyloname symlinks to genomes |
| `OUTPUT_pipeline/3-output/gigantic_genome_annotations/` | Phyloname symlinks to annotations |
| `OUTPUT_pipeline/4-output/4_ai-genome_assembly_statistics.tsv` | Assembly quality metrics |
| `OUTPUT_pipeline/5-output/5_ai-busco_summary.tsv` (+ `5-output/busco_results/`) | Proteome completeness scores; skip-stub if `busco.enabled: false` |
| `OUTPUT_pipeline/6-output/6_ai-comprehensive_quality_summary.tsv` | Comprehensive quality summary (BUSCO + gfastats merged) |
| `ai/logs/run_*.log` | Per-run audit log from script 007 |

**Removed**: no `6_ai-species_selection_manifest.tsv` — earlier docs
claimed STEP_2 generated one; it doesn't. Species selection happens in
STEP_4 via `INPUT_user/selected_species.txt`.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "Phylonames mapping not found" | phylonames subproject not run | Run phylonames first |
| "Input proteomes directory not found" | STEP_1-sources not run | Run STEP_1 first |
| "genus_species not found in phylonames mapping" | Species mismatch | Check spelling in STEP_1 sources vs phylonames |
| gfastats command not found | Conda environment not activated | `conda activate aiG-genomesDB` |

---

## Key Files

| File | User Edits? | Description |
|------|-------------|-------------|
| `RUN-workflow.sh` | No | Main workflow script |
| `RUN-workflow.sh` (with execution_mode: slurm) | Yes (slurm_account/slurm_qos in YAML) | Unified runner that self-submits to SLURM |
| `START_HERE-user_config.yaml` | Yes (project settings) | User-editable configuration |
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
output_to_input/STEP_1-sources/
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
└── genome_annotations/     ──► Script 003 ──► 3-output/gigantic_genome_annotations/

phylonames/output_to_input/maps/
└── {project_name}_map*.tsv  ──► Scripts 001, 003 (need phylonames)

All quality data ──► Script 006 ──► 6-output/6_ai-comprehensive_quality_summary.tsv
Script 007 ──► ai/logs/run_*.log (per-run audit)
```

---

## Passing Data to STEP_3 and STEP_4

After this workflow completes:
- **STEP_3** uses cleaned proteomes from `OUTPUT_pipeline/2-output/gigantic_proteomes_cleaned/` (published into `../../output_to_input/STEP_2-standardize_and_evaluate/gigantic_proteomes_cleaned/`) to build BLAST databases for **all** species — no filtering.
- **STEP_4** reads the user's species selection from its own `INPUT_user/selected_species.txt` (defaults to all species if absent), validates against STEP_2 + STEP_3 outputs, and copies only the selected species into the final `speciesN_*` directories. The quality summary at `6_ai-comprehensive_quality_summary.tsv` is what the user reviews to decide which species to drop — but it is NOT a manifest STEP_4 reads programmatically.
