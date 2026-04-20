# AI Guide: annotations_X_ocl Subproject

**AI**: Claude Code | Opus 4.6 | 2026 April 18
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

Performs Origin-Conservation-Loss (OCL) analysis of annotation groups (annogroups) across
phylogenetic species tree structures. For each annogroup, determines:

- **Origin**: The most recent common ancestor (MRCA) where the annogroup first appeared
- **Conservation**: How often the annogroup is retained across descendant lineages
- **Loss**: How and when annogroups are lost, distinguishing first-time loss from continued absence

Annogroups are the annotation analog to orthogroups -- sets of proteins grouped by their
annotation pattern from a specific database. Three subtypes capture different annotation
architectures:

- **single**: proteins with exactly one annotation from the database
- **combo**: proteins with identical multi-annotation architecture (domain databases only)
- **zero**: proteins with no annotations from the database (domain databases only)

---

## Directory Structure

```
annotations_X_ocl/
├── README.md
├── AI_GUIDE-annotations_X_ocl.md              # THIS FILE
├── RUN-clean_and_record_subproject.sh
├── research_notebook/
│   └── ai_research/
├── output_to_input/                            # Downstream output
│   └── BLOCK_ocl_analysis/                    # Contains run_label subdirs
│       ├── species70_pfam/                     # From RUN copy with that label
│       │   ├── structure_001/
│       │   │   └── 4_ai-structure_001_annogroups-complete_ocl_summary-all_types.tsv
│       │   └── ...
│       └── species70_gene3d/                   # From another RUN copy
│           └── ...
├── upload_to_server/
└── BLOCK_ocl_analysis/
    ├── AI_GUIDE-ocl_analysis.md
    └── workflow-COPYME-ocl_analysis/
        ├── RUN-workflow.sh                     # Self-submits to SLURM when execution_mode=slurm
        ├── START_HERE-user_config.yaml
        ├── INPUT_user/
        │   └── structure_manifest.tsv
        ├── OUTPUT_pipeline/
        └── ai/
            ├── AI_GUIDE-ocl_analysis_workflow.md
            ├── conda_environment.yml           # Per-BLOCK env spec (created on first run)
            ├── main.nf
            ├── nextflow.config
            └── scripts/
                ├── 001_ai-python-create_annogroups.py
                ├── 002_ai-python-determine_origins.py
                ├── 003_ai-python-quantify_conservation_loss.py
                ├── 004_ai-python-comprehensive_ocl_analysis.py
                ├── 005_ai-python-validate_results.py
                └── 006_ai-python-write_run_log.py
```

---

## Key Concepts

### Phylogenetic Blocks and Block-States (Rule 7)

OCL analysis operates on two related kinds of tree objects, defined in Rule 7
of `../../AI_GUIDE-project.md`:

- A **phylogenetic block** is a single parent-to-child edge of a species tree
  structure, containing both endpoint clades with no intervening nodes.
  Written `parent_clade_id_name::child_clade_id_name` (e.g.
  `C069_Holozoa::C082_Metazoa`). Feature-agnostic.

- A **phylogenetic block-state** is a block paired with a specific annogroup's
  state on that block, written `parent_clade_id_name::child_clade_id_name-LETTER`
  (e.g. `C069_Holozoa::C082_Metazoa-O`). The LETTER encodes one of five states
  refining classical Dollo:

| Letter | State | Parent has it? | Child has it? | Kind |
|---|---|---|---|---|
| **A** | Inherited Absence | No | No (pre-origin) | inheritance |
| **O** | Origin | No | Yes | event |
| **P** | Inherited Presence | Yes | Yes | inheritance |
| **L** | Loss | Yes | No | event |
| **X** | Inherited Loss | No (post-loss) | No | inheritance |

Event blocks carry state O or L (annogroup state changes between parent and
child); inheritance blocks carry state A, P, or X (state persists). The
distinction between A and X -- both have absent parent and child -- is
historical: A lives upstream of the origin (annogroup never arose in this
part of the tree), X lives downstream of a loss (annogroup was present
upstream and has been lost).

### Phylogenetic Paths and Path-States

A **phylogenetic path** is a chain of consecutive phylogenetic blocks -- the
walk from `C000_OOL` (Origin Of Life) down to one species. Every species in
the structure has exactly one phylogenetic path.

A **phylogenetic path-state** is a path paired with a specific annogroup's
state on each block of the path, written as the concatenated five-state
letters in OOL-end-to-species-end order (e.g. `AAAOPLXX`). Script 004 emits
one path-state per (annogroup, species) pair into
`4_ai-path_states-per_annogroup_per_species.tsv`.

Path-state letters follow the regular pattern `A* [O [P* [L X*]?]?]?`.
Script 005 CHECK 8 enforces this invariant across every row.

### Annogroups and Subtypes

An **annogroup** groups proteins by their annotation pattern from a specific
database. The annogroup ID format is `annogroup_{database}_{N}` (e.g.
`annogroup_pfam_1`). The **annogroup map** links each ID to its full details:
subtype, annotation accessions, species list, and sequence IDs.

Database-specific subtype defaults:

| Database Category | Databases | Subtypes |
|---|---|---|
| Domain databases | pfam, gene3d, superfamily, smart, cdd, prosite_profiles | single, combo, zero |
| Simple databases | deeploc, signalp, tmbed, metapredict | single only |

### COPYME Multi-Database Coexistence

This subproject supports running OCL analysis with different annotation databases.
Each exploration gets its own COPYME copy:

```
workflow-RUN_01-ocl_analysis/  -> run_label: "species70_pfam"
workflow-RUN_02-ocl_analysis/  -> run_label: "species70_gene3d"
```

The `run_label` in `START_HERE-user_config.yaml` determines the output_to_input
subdirectory name, so different runs coexist without overwriting each other.

### Terminal Self-Loop Exclusion

Where parent_name == child_name at terminal tree nodes, these self-loops are excluded
from conservation/loss analysis because they represent the species itself, not a meaningful
evolutionary transition.

### Fail-Fast Validation

Script 005 exits with code 1 on ANY validation failure. Edge cases like zero-transition
annogroups are handled explicitly in Scripts 003-004 (counts set to 0) so they never
appear as validation failures. If validation finds problems, the pipeline stops.

### Clade IDs -- Topologically-Structured Species Sets

Clade identifiers consumed here (e.g., `C082_Metazoa`) come from
`trees_species/BLOCK_permutations_and_features/` and identify
**topologically-structured species sets** -- unique combinations of species
content and branching arrangement. Same biological clade -> same
`clade_id_name` across every candidate species tree structure.

**Usage convention in OCL code**: treat `clade_id_name` as a single atomic
identifier -- never split into `clade_id` and `clade_name` for dict lookups
or cross-table joins.

For the full canonical definition, see Rule 6 in `../../AI_GUIDE-project.md`.

---

## Upstream Dependencies

| Subproject | What It Provides | Config Path |
|-----------|------------------|-------------|
| trees_species | Phylogenetic blocks, parent-child tables, phylogenetic paths | `inputs.trees_species_dir` |
| annotations_hmms | Per-species annotation files (7-column TSV per species per database) | `inputs.annotations_dir` |

---

## Downstream Dependencies

The primary downstream file is `4_ai-{structure}_annogroups-complete_ocl_summary-all_types.tsv`,
which provides per-annogroup origin, block-state counts, and species composition across all
subtypes. Per-subtype summaries are also available for focused analysis.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "Config file not found" | Missing START_HERE-user_config.yaml | Verify config file exists in workflow directory |
| "Structure manifest empty" | No structure IDs in manifest | Add structure IDs (001-105) to INPUT_user/structure_manifest.tsv |
| "Phylogenetic blocks file not found" | trees_species not run | Run trees_species subproject first |
| "No annotation files found" | annotations_hmms not run or wrong database path | Run annotations_hmms subproject; verify `annotations_dir` in config |
| Script 005 exits with code 1 | Validation failures detected | Check 5-output/5_ai-validation_error_log.txt for details |
| "No annogroups created" | Annotation files empty or wrong format | Verify annotation files are 7-column TSV with expected format |

---

## Key Files

| File | User Edits? | Purpose |
|------|------------|---------|
| `START_HERE-user_config.yaml` | Yes | All configuration: run_label, annotation_database, annogroup_subtypes, paths, `execution_mode` (local or slurm), SLURM account/qos, `resume` flag, `cpus` + `memory_gb` for SLURM sizing |
| `INPUT_user/structure_manifest.tsv` | Yes | Which tree structures to analyze (one structure_id per line) |
| `RUN-workflow.sh` | No | Single entry point: `bash RUN-workflow.sh`. If `execution_mode: "slurm"`, self-submits as a SLURM job via `sbatch` |
| `ai/conda_environment.yml` | No | Per-BLOCK conda env spec (name: `aiG-annotations_X_ocl-ocl_analysis`) |
| `ai/main.nf` | No | NextFlow pipeline definition |
| `ai/nextflow.config` | No | NextFlow executor settings |

---

## Questions to Ask

| Situation | Ask |
|-----------|-----|
| User wants to run annotations OCL | "Which annotation database should I use? (pfam, gene3d, deeploc, signalp, tmbed, metapredict)" |
| Domain vs simple database | "Domain databases support single/combo/zero subtypes; simple databases use single only" |
| User wants a subset of structures | "Which structure IDs should I add to the manifest?" |
| Validation failures | "Would you like me to investigate the error log?" |
