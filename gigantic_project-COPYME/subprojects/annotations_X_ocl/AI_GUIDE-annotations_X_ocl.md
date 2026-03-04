# AI Guide: annotations_X_ocl Subproject

**AI**: Claude Code | Opus 4.6 | 2026 March 04
**Human**: Eric Edsinger

**For AI Assistants**: Read `../../AI_GUIDE-project.md` first for GIGANTIC overview,
directory structure, and general patterns. This guide covers annotations_X_ocl-specific
concepts and troubleshooting.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../AI_GUIDE-project.md` |
| annotations_X_ocl concepts, troubleshooting | This file |
| Running the workflow | `BLOCK_ocl_analysis/workflow-COPYME-ocl_analysis/ai/AI_GUIDE-ocl_analysis_workflow.md` |

---

## What This Subproject Does

Performs Origin-Conservation-Loss (OCL) analysis of **annotation groups** ("annogroups")
across phylogenetic tree structures. This is the annotation-centric counterpart to
`orthogroups_X_ocl` (which does OCL on orthogroups).

For each annogroup, determines:

- **Origin**: The most recent common ancestor (MRCA) where the annotation pattern first appeared
- **Conservation**: How often the annotation pattern is retained across descendant lineages
- **Loss**: How and when annotation patterns are lost, distinguishing first-time loss from continued absence

Uses the **TEMPLATE_03 dual-metric tracking** algorithm that separates "phylogenetically
inherited" (theoretical expectation) from "actually present in species" (genomic reality).

---

## Key Concepts

### Annogroups vs Orthogroups

Annogroups are the annotation analog to orthogroups. Both reflect conserved signal at some
level, but annogroups encompass a broader range of grouping logic:

- Some annotations are explicitly evolutionary (protein domain families)
- Others are functional but not evolutionary (subcellular localization)
- Others are structural features (transmembrane domains)

Annogroups are different ways of creating sets of sequences through their annotations,
whatever the rules of set formation.

### Annogroup ID Convention

**`annogroup_{db}_N`** where `{db}` is the annotation database name and `N` is a sequential
integer. The database name prevents collisions across independent COPYME runs and gives users
immediate context. All other information lives in the **annogroup map** (lookup table).

### The 3 Annogroup Subtypes

Each is a direct evaluation of an individual protein by an annotation tool:

| Subtype | What It Groups | Basis |
|---------|---------------|-------|
| `single` | Proteins with exactly one annotation, grouped by that accession | Tool reported one hit |
| `combo` | Proteins with identical multi-annotation architecture | Tool reported multiple hits |
| `zero` | Individual proteins with zero annotations (singletons) | Tool reported no hits |

**What is NOT an annogroup**: Higher-level groupings like "all proteins with PF00069",
clan/supergroup memberships, or cross-database integration. These are downstream processing.

### The Annogroup Map

Script 001 produces `1_ai-annogroup_map.tsv` with 8 columns linking every annogroup ID
to its full details (subtype, accessions, species, sequences). This is the Rosetta Stone
for all downstream analysis.

### TEMPLATE_03 Dual-Metric Tracking

Same core algorithm as orthogroups_X_ocl. For each phylogenetic block, classifies every
annogroup into one of four event types:

| Event | Parent Has It? | Child Has It? | Meaning |
|-------|---------------|---------------|---------|
| **Conservation** | Yes | Yes | Annotation pattern retained |
| **Loss at Origin** | Yes | No | First loss event |
| **Continued Absence** | No | No | Already lost upstream |
| **Loss Coverage** | - | No | Total absence (loss_origin + continued_absence) |

### COPYME Multi-Database Coexistence

Each COPYME copy explores one annotation database. The `run_label` provides namespacing:

```
workflow-RUN_01-ocl_analysis/  -> run_label: "Species71_pfam"
workflow-RUN_02-ocl_analysis/  -> run_label: "Species71_gene3d"
workflow-RUN_03-ocl_analysis/  -> run_label: "Species71_deeploc"
```

### Database Category Defaults

- **Domain databases** (pfam, gene3d, etc.): `single`, `combo`, `zero` (all 3 subtypes)
- **Simple databases** (deeploc, signalp, tmbed, metapredict): `single` only (each protein
  gets one prediction, no combos possible)

### Terminal Self-Loop Exclusion

Where parent_name == child_name at terminal tree nodes, these self-loops are excluded
from conservation/loss analysis because they represent the species itself, not a meaningful
evolutionary transition.

### Fail-Fast Validation

Script 005 runs 8 validation checks (one more than orthogroups_X_ocl) and exits with
code 1 on ANY failure. Check 8 validates annogroup subtype consistency, no duplicate IDs,
and ID format compliance.

---

## Directory Structure

```
annotations_X_ocl/
├── README.md
├── AI_GUIDE-annotations_X_ocl.md              # THIS FILE
├── RUN-clean_and_record_subproject.sh
├── user_research/
├── research_notebook/
│   └── ai_research/
├── output_to_input/                            # Downstream output
│   └── BLOCK_ocl_analysis/                     # Contains run_label subdirs
│       ├── Species71_pfam/                     # From RUN copy with that label
│       │   ├── structure_001/
│       │   │   └── 4_ai-annogroups-complete_ocl_summary-all_types.tsv
│       │   └── ...
│       ├── Species71_gene3d/                   # From another RUN copy
│       │   └── ...
│       └── Species71_deeploc/
│           └── ...
├── upload_to_server/
└── BLOCK_ocl_analysis/
    ├── AI_GUIDE-ocl_analysis.md
    └── workflow-COPYME-ocl_analysis/
        ├── RUN-workflow.sh
        ├── RUN-workflow.sbatch
        ├── ocl_config.yaml
        ├── INPUT_user/
        │   └── structure_manifest.tsv
        ├── OUTPUT_pipeline/
        └── ai/
            ├── AI_GUIDE-ocl_analysis_workflow.md
            ├── main.nf
            ├── nextflow.config
            └── scripts/
                ├── 001_ai-python-create_annogroups.py
                ├── 002_ai-python-determine_origins.py
                ├── 003_ai-python-quantify_conservation_loss.py
                ├── 004_ai-python-comprehensive_ocl_analysis.py
                └── 005_ai-python-validate_results.py
```

---

## Upstream Dependencies

| Subproject | What It Provides | Config Path |
|-----------|------------------|-------------|
| trees_species | Phylogenetic blocks, parent-child tables, phylogenetic paths | `inputs.trees_species_dir` |
| annotations_hmms | Per-species annotation files (7-column TSV) | `inputs.annotations_dir` |

---

## Downstream Dependencies

The primary downstream file is `4_ai-annogroups-complete_ocl_summary-all_types.tsv`,
which provides per-annogroup origin, subtype, conservation rate, loss rate, and species
composition across all subtypes in a single integrated file. Per-subtype summaries are
also available.

This is used by:
- Cross-database comparison analyses
- Integration with orthogroups_X_ocl for combined functional/orthology views
- Any analysis comparing conservation patterns across annotation types

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "Config file not found" | Missing ocl_config.yaml | Verify config file exists in workflow directory |
| "Structure manifest empty" | No structure IDs in manifest | Add structure IDs (001-105) to INPUT_user/structure_manifest.tsv |
| "Phylogenetic blocks file not found" | trees_species not run | Run trees_species subproject first |
| "Annotations directory not found" | annotations_hmms not run | Run annotations_hmms subproject with matching database |
| "No annotation files found" | Wrong database in config | Verify `annotation_database` matches directory contents |
| Script 005 exits with code 1 | Validation failures detected | Check 5-output/5_ai-validation_error_log.txt for details |
| "Duplicate annogroup IDs" | ID generation error | Check 1-output/1_ai-annogroup_map.tsv for duplicates |

---

## Key Files

| File | User Edits? | Purpose |
|------|------------|---------|
| `ocl_config.yaml` | Yes | All configuration: run_label, database, subtypes, paths |
| `INPUT_user/structure_manifest.tsv` | Yes | Which tree structures to analyze |
| `RUN-workflow.sh` | No | Launches pipeline, creates symlinks |
| `RUN-workflow.sbatch` | Yes (account/qos) | SLURM wrapper for cluster submission |
| `ai/main.nf` | No | NextFlow pipeline definition |
| `ai/nextflow.config` | Yes (SLURM settings) | NextFlow resource configuration |

---

## Questions to Ask

| Situation | Ask |
|-----------|-----|
| User wants to run OCL analysis | "Which annotation database should I use? (pfam, gene3d, deeploc, etc.)" |
| User wants a subset of structures | "Which structure IDs should I add to the manifest?" |
| User wants non-default subtypes | "Which annogroup subtypes? (single, combo, zero - defaults depend on database)" |
| Validation failures | "Would you like me to investigate the error log?" |
