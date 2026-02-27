# AI Guide: OrthoHMM Tool

**For AI Assistants**: Read `../AI_GUIDE-orthogroups.md` first for orthogroups overview and concepts. This guide covers OrthoHMM-specific usage.

**Location**: `gigantic_project-COPYME/subprojects/orthogroups/orthohmm/`

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
| GIGANTIC overview, directory structure | `../../../AI_GUIDE-project.md` |
| Orthogroups concepts (OrthoFinder vs OrthoHMM) | `../AI_GUIDE-orthogroups.md` |
| Running OrthoHMM workflow | `workflow-COPYME-*/ai/AI_GUIDE-orthohmm_workflow.md` |

---

## What OrthoHMM Does

**Purpose**: Identify orthologs using profile HMM (Hidden Markov Model) searches for improved sensitivity.

**Input**: Proteomes (FASTA files) from genomesDB STEP_2 output_to_input

**Output**:
- Orthogroups with full GIGANTIC identifiers
- Gene counts per orthogroup per species
- Per-species QC summaries
- Header mapping (short ID to GIGANTIC ID)

**When to use**: When you need better sensitivity for divergent sequences or want HMM profiles for downstream annotation

---

## Workflow Overview

The OrthoHMM workflow consists of six scripts:

| Script | Purpose |
|--------|---------|
| 001 | Validate proteomes from genomesDB and create inventory |
| 002 | Convert FASTA headers to short IDs (Genus_species-N format) |
| 003 | Run OrthoHMM clustering (main compute-intensive step) |
| 004 | Generate summary statistics (coverage, sizes, etc.) |
| 005 | Per-species QC analysis (identify unassigned sequences) |
| 006 | Restore full GIGANTIC identifiers in output files |

---

## Directory Structure

```
orthohmm/
├── README.md                    # Human documentation
├── AI_GUIDE-orthohmm.md         # THIS FILE
│
├── user_research/               # Personal workspace
│
├── output_to_input/             # Outputs for downstream subprojects
│   ├── 6_ai-orthogroups_gigantic_ids.txt
│   ├── 2_ai-header_mapping.tsv
│   └── 4_ai-orthohmm_summary_statistics.tsv
│
├── upload_to_server/            # Server sharing
│
└── workflow-COPYME-run_orthohmm/
    ├── RUN-workflow.sh          # Local execution
    ├── RUN-workflow.sbatch      # SLURM execution
    ├── OUTPUT_pipeline/         # Results by script
    │   ├── 1-output/
    │   ├── 2-output/
    │   ├── 3-output/
    │   ├── 4-output/
    │   ├── 5-output/
    │   └── 6-output/
    └── ai/scripts/              # Processing scripts
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `workflow-*/RUN-workflow.sh` | Main workflow | No (just run it) |
| `workflow-*/RUN-workflow.sbatch` | SLURM account/qos | **YES** (SLURM) |
| `output_to_input/` | Output for downstream | No (auto-populated) |

---

## Input Requirements

The workflow automatically reads proteomes from:
```
../../../genomesDB/STEP_2-standardize_and_evaluate/output_to_input/gigantic_proteomes/
```

No manual INPUT_user setup required - the workflow uses proteomes directly from genomesDB output.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "proteomes directory not found" | genomesDB incomplete | Run genomesDB STEP_2 first |
| "orthohmm command not found" | Wrong environment | `conda activate ai_gigantic_orthogroups` |
| "No proteome files found" | Empty gigantic_proteomes | Check genomesDB output_to_input |
| Out of memory | Large dataset | Increase SLURM memory (200GB+) |
| Timeout | Many species | Increase SLURM time (200 hours) |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| Starting fresh | "Has genomesDB STEP_2 completed? Are proteomes in output_to_input?" |
| Error occurred | "Which script failed? Check slurm_logs/ or OUTPUT_pipeline/N-output/" |
| Slow progress | "How many species? OrthoHMM is O(n²) - 70 species takes ~100 hours" |

---

## Conda Environment

**Environment name**: `ai_gigantic_orthogroups`

**Key packages**:
- orthohmm (via pip)
- hmmer
- mcl

**Installation**:
```bash
cd gigantic_project-COPYME/
mamba env create -f conda_environments/ai_gigantic_orthogroups.yml
```
