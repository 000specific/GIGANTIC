# AI Guide: OrthoHMM Tool

**For AI Assistants**: Read `../AI_GUIDE-orthogroups.md` first for orthogroups overview and concepts. This guide covers OrthoHMM-specific usage.

**Location**: `gigantic_project-COPYME/subprojects/orthogroups/broccoli/`

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

**Input**: Proteomes (FASTA files) from genomesDB

**Output**:
- orthohmm_orthogroups.txt - Gene family assignments
- orthohmm_gene_count.txt - Gene counts per orthogroup per species
- HMM profiles for each orthogroup

**When to use**: When you need better sensitivity for divergent sequences or want HMM profiles for downstream annotation

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
│   └── OrthoHMM/
│       ├── orthohmm_orthogroups.txt
│       └── orthohmm_gene_count.txt
│
├── upload_to_server/            # Server sharing
│   └── upload_manifest.tsv
│
└── workflow-COPYME-run_orthohmm/
    ├── RUN-orthohmm.sh          # Local execution
    ├── RUN-orthohmm.sbatch      # SLURM execution
    ├── orthohmm_config.yaml     # User configuration
    ├── INPUT_user/              # Input proteomes
    ├── OUTPUT_pipeline/         # Results
    └── ai/                      # Internal scripts
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `workflow-*/orthohmm_config.yaml` | Project name, threads | **YES** |
| `workflow-*/RUN-orthohmm.sbatch` | SLURM account/qos | **YES** (SLURM) |
| `workflow-*/INPUT_user/` | Proteome FASTAs | **YES** |
| `output_to_input/OrthoHMM/` | Output for downstream | No |

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "No FASTA files found" | Empty INPUT_user | Add proteomes from genomesDB |
| "HMMER not found" | Tool not installed | Load conda environment |
| Out of memory | Large HMM profiles | Increase SLURM memory request |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| Starting fresh | "Which species set are you using (e.g., species71)?" |
| Error occurred | "Which step failed? What error message?" |
| Choosing tool | "Do you need HMM profiles for downstream use?" |
