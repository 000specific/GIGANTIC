# AI Guide: OrthoFinder Tool

**For AI Assistants**: Read `../AI_GUIDE-orthogroups.md` first for orthogroups overview and concepts. This guide covers OrthoFinder-specific usage.

**Location**: `gigantic_project-COPYME/subprojects/orthogroups/orthofinder/`

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
| Running OrthoFinder workflow | `workflow-COPYME-*/ai/AI_GUIDE-orthofinder_workflow.md` |

---

## What OrthoFinder Does

**Purpose**: Identify orthologous gene groups across species using sequence similarity (all-vs-all BLAST/Diamond).

**Input**: Proteomes (FASTA files) from genomesDB

**Output**:
- Orthogroups.txt - Gene family assignments
- Species tree
- Gene trees
- Comparative genomics statistics

**When to use**: Standard ortholog detection for comparative genomics

---

## Directory Structure

```
orthofinder/
├── README.md                    # Human documentation
├── AI_GUIDE-orthofinder.md      # THIS FILE
│
├── user_research/               # Personal workspace
│
├── output_to_input/             # Outputs for downstream subprojects
│   └── Orthogroups/
│       └── Orthogroups.txt      # Main output
│
├── upload_to_server/            # Server sharing
│   └── upload_manifest.tsv
│
└── workflow-COPYME-run_orthofinder/
    ├── RUN_orthofinder.sh       # Main workflow runner
    ├── SLURM_orthofinder.sbatch # SLURM submission
    ├── INPUT_user/              # Input proteomes + species tree
    ├── OUTPUT_pipeline/         # Results
    └── ai/                      # Workflow guide
```

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `workflow-*/SLURM_orthofinder.sbatch` | SLURM account/qos/email | **YES** (SLURM) |
| `workflow-*/INPUT_user/` | Proteome FASTAs | **YES** |
| `output_to_input/Orthogroups/` | Output for downstream | No |

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "No FASTA files found" | Empty INPUT_user | Add proteomes from genomesDB |
| "Diamond not found" | Tool not installed | Load conda environment |
| Out of memory | Too many species | Increase SLURM memory request |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| Starting fresh | "Which species set are you using (e.g., species71)?" |
| Error occurred | "Which step failed? What error message?" |
| Slow performance | "How many species and how large are the proteomes?" |
