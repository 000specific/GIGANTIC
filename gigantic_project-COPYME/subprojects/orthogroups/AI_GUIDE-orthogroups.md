# AI Guide: Orthogroups Subproject

**For AI Assistants**: Read `../../AI_GUIDE-project.md` first for GIGANTIC overview, directory structure, and general patterns. This guide covers orthogroups-specific concepts.

**Location**: `gigantic_project-COPYME/subprojects/orthogroups/`

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
| GIGANTIC overview, directory structure | `../../AI_GUIDE-project.md` |
| Orthogroups concepts, comparison | This file |
| OrthoFinder workflow | `orthofinder/AI_GUIDE-orthofinder.md` |
| OrthoHMM workflow | `orthohmm/AI_GUIDE-orthohmm.md` |

---

## What This Subproject Does

**Purpose**: Identify orthologous gene groups (orthogroups) across species.

**Input**: Proteomes from genomesDB (standardized T1 proteomes)

**Output**: Gene family assignments - which genes from different species belong to the same gene family.

**Two Tools Available**:
1. **OrthoFinder** - Sequence similarity based (all-vs-all Diamond/BLAST)
2. **OrthoHMM** - Profile HMM based (better for divergent sequences)

---

## Directory Structure

```
orthogroups/
├── README.md                    # Human documentation
├── AI_GUIDE-orthogroups.md      # THIS FILE
├── RUN-clean_and_record_subproject.sh  # Cleanup utility
├── RUN-update_upload_to_server.sh      # Server update utility
│
├── orthofinder/                 # OrthoFinder tool workspace
│   ├── README.md
│   ├── AI_GUIDE-orthofinder.md
│   ├── user_research/
│   ├── output_to_input/
│   ├── upload_to_server/
│   └── workflow-COPYME-run_orthofinder/
│
└── orthohmm/                    # OrthoHMM tool workspace
    ├── README.md
    ├── AI_GUIDE-orthohmm.md
    ├── user_research/
    ├── output_to_input/
    ├── upload_to_server/
    └── workflow-COPYME-run_orthohmm/
```

---

## OrthoFinder vs OrthoHMM

| Feature | OrthoFinder | OrthoHMM |
|---------|-------------|----------|
| Method | All-vs-all BLAST/Diamond | Profile HMM search |
| Speed | Fast | Slower |
| Sensitivity | Good for close relatives | Better for divergent sequences |
| Extra output | Species tree, gene trees | HMM profiles for annotation |
| When to use | Standard comparative genomics | Divergent species, HMM annotation |

**Both can be run** - they provide complementary information.

---

## Prerequisites

1. **genomesDB complete**: `genomesDB/STEP_2.../output_to_input/gigantic_proteomes/`
2. **Species selection**: Know which species set you're analyzing

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "No proteomes found" | genomesDB incomplete | Complete genomesDB first |
| Tool not found | Environment not loaded | `conda activate ai_gigantic_orthogroups` |
| Slow performance | Many species | Use SLURM with more resources |

---

## Key Files (Subproject Level)

| File | Purpose | User Edits? |
|------|---------|-------------|
| `orthofinder/workflow-*/INPUT_user/` | OrthoFinder proteomes | **YES** |
| `orthohmm/workflow-*/INPUT_user/` | OrthoHMM proteomes | **YES** |
| `RUN-clean_and_record_subproject.sh` | Cleanup utility | No |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| Choosing tool | "Do you need HMM profiles for downstream annotation?" |
| Starting | "Which species set? Have you completed genomesDB?" |
| Both tools | "Do you want to compare results from both tools?" |
