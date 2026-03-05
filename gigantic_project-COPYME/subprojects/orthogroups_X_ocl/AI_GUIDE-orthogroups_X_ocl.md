# AI Guide: orthogroups_X_ocl Subproject

**AI**: Claude Code | Opus 4.6 | 2026 March 04
**Human**: Eric Edsinger

**For AI Assistants**: Read `../../AI_GUIDE-project.md` first for GIGANTIC overview,
directory structure, and general patterns. This guide covers orthogroups_X_ocl-specific
concepts and troubleshooting.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../AI_GUIDE-project.md` |
| orthogroups_X_ocl concepts, troubleshooting | This file |
| Running the workflow | `BLOCK_ocl_analysis/workflow-COPYME-ocl_analysis/ai/AI_GUIDE-ocl_analysis_workflow.md` |

---

## What This Subproject Does

Performs Origin-Conservation-Loss (OCL) analysis of orthogroups across phylogenetic tree
structures. For each orthogroup, determines:

- **Origin**: The most recent common ancestor (MRCA) where the orthogroup first appeared
- **Conservation**: How often the orthogroup is retained across descendant lineages
- **Loss**: How and when orthogroups are lost, distinguishing first-time loss from continued absence

Uses the **TEMPLATE_03 dual-metric tracking** algorithm that separates "phylogenetically
inherited" (theoretical expectation) from "actually present in species" (genomic reality).

---

## Directory Structure

```
orthogroups_X_ocl/
├── README.md
├── AI_GUIDE-orthogroups_X_ocl.md              # THIS FILE
├── RUN-clean_and_record_subproject.sh
├── user_research/
├── research_notebook/
│   └── ai_research/
├── output_to_input/                            # Downstream output
│   └── BLOCK_ocl_analysis/                     # Contains run_label subdirs
│       ├── Species71_X_OrthoFinder/            # From RUN copy with that label
│       │   ├── structure_001/
│       │   │   └── 4_ai-orthogroups-complete_ocl_summary.tsv
│       │   └── ...
│       └── Species71_X_OrthoHMM/               # From another RUN copy
│           └── ...
├── upload_to_server/
└── BLOCK_ocl_analysis/
    ├── AI_GUIDE-ocl_analysis.md
    └── workflow-COPYME-ocl_analysis/
        ├── RUN-workflow.sh
        ├── RUN-workflow.sbatch
        ├── START_HERE-user_config.yaml
        ├── INPUT_user/
        │   └── structure_manifest.tsv
        ├── OUTPUT_pipeline/
        └── ai/
            ├── AI_GUIDE-ocl_analysis_workflow.md
            ├── main.nf
            ├── nextflow.config
            └── scripts/
                ├── 001_ai-python-prepare_inputs.py
                ├── 002_ai-python-determine_origins.py
                ├── 003_ai-python-quantify_conservation_loss.py
                ├── 004_ai-python-comprehensive_ocl_analysis.py
                └── 005_ai-python-validate_results.py
```

---

## Key Concepts

### TEMPLATE_03 Dual-Metric Tracking

The core algorithm that makes OCL analysis scientifically meaningful. For each phylogenetic
block (parent-to-child transition), classifies every orthogroup into one of four event types:

| Event | Parent Has It? | Child Has It? | Meaning |
|-------|---------------|---------------|---------|
| **Conservation** | Yes | Yes | Gene family retained |
| **Loss at Origin** | Yes | No | First loss event |
| **Continued Absence** | No | No | Already lost upstream |
| **Loss Coverage** | - | No | Total absence (loss_origin + continued_absence) |

This distinguishes "the gene was lost in this lineage" from "the gene was already gone."

### COPYME Multi-Tool Coexistence

This subproject supports running OCL analysis with different orthogroup clustering tools
(OrthoFinder, OrthoHMM, Broccoli). Each exploration gets its own COPYME copy:

```
workflow-RUN_01-ocl_analysis/  → run_label: "Species71_X_OrthoFinder"
workflow-RUN_02-ocl_analysis/  → run_label: "Species71_X_OrthoHMM"
```

The `run_label` in `START_HERE-user_config.yaml` determines the output_to_input subdirectory name,
so different runs coexist without overwriting each other.

### Terminal Self-Loop Exclusion

Where parent_name == child_name at terminal tree nodes, these self-loops are excluded
from conservation/loss analysis because they represent the species itself, not a meaningful
evolutionary transition.

### Fail-Fast Validation

Script 005 exits with code 1 on ANY validation failure. Edge cases like zero-transition
orthogroups are handled explicitly in Scripts 003-004 (rates set to 0.0) so they never
appear as validation failures. If validation finds problems, the pipeline stops.

---

## Upstream Dependencies

| Subproject | What It Provides | Config Path |
|-----------|------------------|-------------|
| trees_species | Phylogenetic blocks, parent-child tables, phylogenetic paths | `inputs.trees_species_dir` |
| orthogroups | Orthogroup assignments (OrthoFinder/OrthoHMM/Broccoli) | `inputs.orthogroups_dir` |
| genomesDB | Species proteomes (for sequence loading) | `inputs.proteomes_dir` |

---

## Downstream Dependencies

The primary downstream file is `4_ai-orthogroups-complete_ocl_summary.tsv`, which
provides per-orthogroup origin, conservation rate, loss rate, and species composition.
This is used by:
- annotations_X_ocl (integrating annotations with OCL data)
- Any analysis comparing conservation patterns across gene families

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "Config file not found" | Missing START_HERE-user_config.yaml | Verify config file exists in workflow directory |
| "Structure manifest empty" | No structure IDs in manifest | Add structure IDs (001-105) to INPUT_user/structure_manifest.tsv |
| "Phylogenetic blocks file not found" | trees_species not run | Run trees_species subproject first |
| "Orthogroups file not found" | orthogroups not run | Run orthogroups subproject with matching tool |
| Script 005 exits with code 1 | Validation failures detected | Check 5-output/5_ai-validation_error_log.txt for details |
| "No species found for orthogroup" | ID mapping failure | Verify orthogroups use GIGANTIC IDs matching proteome files |

---

## Key Files

| File | User Edits? | Purpose |
|------|------------|---------|
| `START_HERE-user_config.yaml` | Yes | All configuration: run_label, tool, paths, FASTA flag |
| `INPUT_user/structure_manifest.tsv` | Yes | Which tree structures to analyze |
| `RUN-workflow.sh` | No | Launches pipeline, creates symlinks |
| `RUN-workflow.sbatch` | Yes (account/qos) | SLURM wrapper for cluster submission |
| `ai/main.nf` | No | NextFlow pipeline definition |
| `ai/nextflow.config` | Yes (SLURM settings) | NextFlow resource configuration |

---

## Questions to Ask

| Situation | Ask |
|-----------|-----|
| User wants to run OCL analysis | "Which orthogroup tool should I use? (OrthoFinder, OrthoHMM, Broccoli)" |
| User wants a subset of structures | "Which structure IDs should I add to the manifest?" |
| Large output files | "Should FASTA sequences be embedded in output tables? (default: no)" |
| Validation failures | "Would you like me to investigate the error log?" |
