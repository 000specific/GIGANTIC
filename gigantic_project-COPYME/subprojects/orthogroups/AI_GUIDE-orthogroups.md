# AI Guide: Orthogroups Subproject

**For AI Assistants**: Read `../../AI_GUIDE-project.md` first for GIGANTIC overview, directory structure, and general patterns. This guide covers orthogroups-specific concepts.

**Location**: `gigantic_project-COPYME/subprojects/orthogroups/`

---

## CRITICAL: Surface Discrepancies - No Silent Changes

- NEVER silently do something different than requested
- ALWAYS stop and explain any discrepancy before proceeding

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../AI_GUIDE-project.md` |
| Orthogroups concepts, tool comparison | This file |
| OrthoFinder details | `orthofinder/AI_GUIDE-orthofinder.md` |
| OrthoHMM details | `orthohmm/AI_GUIDE-orthohmm.md` |
| Broccoli details | `broccoli/AI_GUIDE-broccoli.md` |

---

## What This Subproject Does

**Purpose**: Identify orthologous gene groups (orthogroups) across species.

**Input**: Proteomes from genomesDB (`genomesDB/output_to_input/speciesN_gigantic_T1_proteomes/`)

**Output**: Gene family assignments - which genes from different species belong to the same gene family.

**Three Tools Available**:
1. **OrthoFinder** - Sequence similarity based (all-vs-all Diamond/BLAST)
2. **OrthoHMM** - Profile HMM based (better for divergent sequences)
3. **Broccoli** - Phylogeny-network based (fast phylogenies + label propagation)

---

## Tool Comparison

| Feature | OrthoFinder | OrthoHMM | Broccoli |
|---------|-------------|----------|----------|
| Method | All-vs-all Diamond | Profile HMM | Phylogeny + network |
| Speed | Fast | Slower (O(n^2)) | Moderate |
| Sensitivity | Good for close relatives | Better for divergent sequences | Phylogeny-aware |
| Extra output | Species tree, gene trees, HOGs | HMM profiles | Chimeric protein detection |
| When to use | Standard comparative genomics | Divergent species, HMM annotation | Gene-fusion detection |
| Implementation | Bash wrapper | NextFlow (6 scripts) | Pending |

**All three can be run** - comparing results gives higher confidence.

---

## Directory Structure

```
orthogroups/
├── README.md                    # Human documentation
├── AI_GUIDE-orthogroups.md      # THIS FILE
├── TODO.md                      # Subproject tracking
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
├── orthohmm/                    # OrthoHMM tool workspace
│   ├── README.md
│   ├── AI_GUIDE-orthohmm.md
│   ├── user_research/
│   ├── output_to_input/
│   ├── upload_to_server/
│   └── workflow-COPYME-run_orthohmm/
│
└── broccoli/                    # Broccoli tool workspace (pending implementation)
    ├── README.md
    ├── AI_GUIDE-broccoli.md
    ├── user_research/
    ├── output_to_input/
    ├── upload_to_server/
    └── workflow-COPYME-run_broccoli/
```

---

## Prerequisites

1. **genomesDB complete**: `genomesDB/output_to_input/speciesN_gigantic_T1_proteomes/`
2. **Species selection**: Know which species set you're analyzing
3. **Conda environment**: `ai_gigantic_orthogroups`

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "No proteomes found" | genomesDB incomplete | Complete genomesDB first |
| Tool not found | Environment not loaded | `conda activate ai_gigantic_orthogroups` |
| Slow performance | Many species | Use SLURM with more resources |
| OrthoHMM timeout | O(n^2) scaling | Increase SLURM time limit |
| OrthoFinder memory | Large all-vs-all | Increase SLURM memory |

---

## Key Files (Subproject Level)

| File | Purpose | User Edits? |
|------|---------|-------------|
| `orthofinder/workflow-*/INPUT_user/` | OrthoFinder inputs (proteomes + species tree) | **YES** |
| `orthofinder/workflow-*/SLURM_orthofinder.sbatch` | OrthoFinder SLURM settings | **YES** (SLURM) |
| `orthohmm/workflow-*/orthohmm_config.yaml` | OrthoHMM configuration | **YES** |
| `orthohmm/workflow-*/RUN-orthohmm.sbatch` | OrthoHMM SLURM settings | **YES** (SLURM) |
| `broccoli/workflow-*/` | Broccoli (pending implementation) | **YES** |
| `RUN-clean_and_record_subproject.sh` | Cleanup utility | No |
| `TODO.md` | Open items tracking | Review |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| Choosing tool | "Do you need HMM profiles for downstream annotation? (OrthoHMM)" |
| Choosing tool | "Do you need chimeric protein detection? (Broccoli)" |
| Choosing tool | "Do you need species tree and HOGs? (OrthoFinder)" |
| Starting | "Which species set? Have you completed genomesDB?" |
| Both tools | "Do you want to compare results from multiple tools?" |
| Performance | "How many species? This affects runtime and memory needs." |
