# AI Guide: BLOCK_annotations_X_ocl

**AI**: Claude Code | Opus 4.6 | 2026 April 18 (initial)
**AI**: Claude Code | Opus 4.7 (1M context) | 2026 May 29 (OCL reorg Phase 1: depth + cross-ref fixes)
**Human**: Eric Edsinger

<!-- ============================================================================
History: this BLOCK was the standalone subproject `annotations_X_ocl/` before
the 2026-05-29 OCL reorg. Phase 1 migrated it under the new parent subproject
`ocl_phylogenetic_structures/`. The body below is the original subproject
AI guide with path/title cross-references corrected for the new depth.
Phase 5 will harvest content into the parent AI_GUIDE and trim this file to
BLOCK-specific concerns.
============================================================================ -->

**For AI Assistants**: Read `../../../AI_GUIDE.md` first for GIGANTIC overview,
directory structure, and general patterns. Then read `../README.md` (parent
subproject) and `../AI_GUIDE.md` (parent guide). This file covers
BLOCK_annotations_X_ocl-specific concepts and troubleshooting.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../../AI_GUIDE.md` |
| Parent subproject (phylogenetic-axis OCL) | `../README.md` and `../AI_GUIDE.md` |
| BLOCK_annotations_X_ocl concepts, troubleshooting | This file |
| Running the workflow | `workflow-COPYME-ocl_analysis/ai/AI_GUIDE.md` |

---

## What This BLOCK Does

Performs Origin-Conservation-Loss (OCL) analysis of annotation groups (annogroups) across
phylogenetic species tree structures. For each annogroup, determines:

- **Origin**: The most recent common ancestor (MRCA) where the annogroup first appeared
- **Conservation**: How often the annogroup is retained across descendant lineages
- **Loss**: How and when annogroups are lost, distinguishing first-time loss from continued absence

Annogroups are sequences grouped by shared annotation features, produced ONCE
(structure-independent) by the **`annogroups` subproject** and IMPORTED here — this
BLOCK does not compute them. The four canonical types (defined in the annogroups
subproject) are:

- **feature**: sequences sharing one feature (e.g. one pfam domain)
- **combination**: sequences sharing the same distinct set of features
- **architecture**: sequences sharing the same ordered arrangement of positional features
- **absent**: sequences with no feature from the source — **excluded from OCL** (no single origin)

OCL maps the origin-bearing types (feature, combination, architecture) onto each structure.

---

## Directory Structure

```
ocl_phylogenetic_structures/                   # parent subproject
├── README.md, AI_GUIDE.md                     # parent docs
├── output_to_input/                           # parent-level shared output (per §2 mirrors producer paths)
│   ├── BLOCK_annotations_X_ocl/               # this BLOCK's downstream symlinks
│   │   ├── species70_pfam/                    # From RUN copy with that label
│   │   │   ├── structure_001/
│   │   │   │   └── 4_ai-structure_001_annogroups-complete_ocl_summary-all_types.tsv
│   │   │   └── ...
│   │   └── species70_gene3d/                  # From another RUN copy
│   └── BLOCK_orthogroups_X_ocl/               # sibling BLOCK's downstream symlinks
├── upload_to_server/                          # parent-level publishing
├── RUN-update_upload_to_server.sh             # parent-level publisher (§38)
# (no per-subproject research_notebook/ per §1; sandbox at
#  ../../research_notebook/research_ai/subproject-ocl_phylogenetic_structures/)
│
└── BLOCK_annotations_X_ocl/                   # THIS BLOCK
    ├── README.md                              # BLOCK README
    ├── AI_GUIDE.md                            # THIS FILE (consolidated per §3)
    └── workflow-COPYME-ocl_analysis/
        ├── RUN-workflow.sh                    # Self-submits to SLURM when execution_mode=slurm
        ├── START_HERE-user_config.yaml
        ├── INPUT_user/
        │   └── structure_manifest.tsv
        ├── OUTPUT_pipeline/
        └── ai/
            ├── AI_GUIDE.md                    # workflow-level guide (renamed from AI_GUIDE-ocl_analysis_workflow.md per §3)
            ├── conda_environment.yml          # Per-BLOCK env spec (created on first run)
            ├── main.nf
            ├── nextflow.config
            └── scripts/
                ├── 001_ai-python-load_annogroups.py
                ├── 002_ai-python-determine_origins.py
                ├── 003_ai-python-quantify_conservation_loss.py
                ├── 004_ai-python-comprehensive_ocl_analysis.py
                ├── 005_ai-python-validate_results.py
                ├── 006_ai-python-write_run_log.py
                ├── 007_ai-python-aggregate_run_summary.py
                └── utils_run_summary.py
```

---

## Key Concepts

### Phylogenetic Blocks and Block-States (Rule 7)

OCL analysis operates on two related kinds of tree objects, defined in Rule 7
of `../../../AI_GUIDE.md`:

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

### Annogroups and Types (imported, not computed)

An **annogroup** groups sequences by shared annotation features from a specific
source. Annogroups are produced by the **`annogroups` subproject** and IMPORTED
here; Script 001 reads its per-source map
(`<annogroups_dir>/<species_set>/<source>/2_ai-<source>-annogroup_map.tsv`) and
writes the OCL-standardized `annogroups-species_identifiers.tsv` + `annogroup_map.tsv`.

Canonical IDs come from the annogroups subproject:
`annogroup_<source>_<accession>` (feature, e.g. `annogroup_pfam_PF00069`),
`annogroup_<source>_combination<NNNNN>`, `annogroup_<source>_architecture<NNNNN>`.

OCL maps the **origin-bearing** types onto the structures; `absent` is excluded
(no single evolutionary origin). The selected types are set in
`START_HERE-user_config.yaml` (`annogroup_types`, default feature + combination +
architecture). Which types a source yields is data-determined in the annogroups
subproject (whole-protein sources like deeploc have no `architecture`).

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

For the full canonical definition, see Rule 6 in `../../../AI_GUIDE.md`.

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

### Exposed in `output_to_input/BLOCK_annotations_X_ocl/{run_label}/structure_NNN/`

| File | Carries | Notes |
|------|---------|-------|
| `4_ai-{structure}_annogroups-complete_ocl_summary-all_types.tsv` | per-annogroup origin, OCL block-state counts, species composition, annotation accessions/definitions | the OCL spine; does **not** carry member `Sequence_IDs` |
| `1_ai-{structure}_annogroups-single.tsv` | per-annogroup member `Sequence_IDs` (single subtype) | annogroup membership; **structure-invariant** (annotation-derived) |
| `1_ai-{structure}_annogroups-combo.tsv` | per-annogroup member `Sequence_IDs` (combo subtype) | annogroup membership; **structure-invariant** |

The membership files (added 2026-06-09) are exposed because the OCL summary lacks
the per-protein member IDs needed for cross-feature joins. Because annogroup
membership does not depend on tree topology, a consumer needs only one structure's
copy (e.g. `structure_001`).

### Downstream consumers (per §40)

- **`integrator/BLOCK_annotations_X_orthogroups`** — joins the annogroup membership
  `Sequence_IDs` (single + combo) against orthogroup membership to find annogroups
  touching non-bilaterian-only orthogroups. Reads the `1_ai-...annogroups-{single,combo}.tsv`
  membership files exposed above (and the all-types summary for pfam
  accessions/definitions). See `../../integrator/BLOCK_annotations_X_orthogroups/AI_GUIDE.md`.

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
| `ai/conda_environment.yml` | No | Per-BLOCK conda env spec (name: `aiG-ocl_phylogenetic_structures-annotations_X_ocl`) |
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

---

## Workflow Execution Quick Reference

(Folded in from the previously-separate `AI_GUIDE-ocl_analysis.md` per
§3 — one `AI_GUIDE.md` per directory.)

### COPYME Pattern

```
BLOCK_annotations_X_ocl/             # this BLOCK
├── workflow-COPYME-ocl_analysis/    # Template (never run directly)
├── workflow-RUN_01-ocl_analysis/    # Copy for species70 pfam
├── workflow-RUN_02-ocl_analysis/    # Copy for species70 gene3d
└── workflow-RUN_03-ocl_analysis/    # Copy for species70 deeploc
```

Each copy has its own `START_HERE-user_config.yaml` with a unique
`run_label`, and outputs are symlinked into separate run_label
subdirectories at `../output_to_input/BLOCK_annotations_X_ocl/{run_label}/`
at the parent subproject level.

### Creating a New Run

```bash
# 1. Copy the template
cp -r workflow-COPYME-ocl_analysis workflow-RUN_01-ocl_analysis

# 2. Edit config for this specific run
cd workflow-RUN_01-ocl_analysis
nano START_HERE-user_config.yaml
# Set: run_label, species_set_name, annotation_database,
#      annogroup_subtypes, input paths,
#      execution_mode ("local" or "slurm"), and if slurm:
#      slurm_account/slurm_qos

# 3. Edit structure manifest (one structure_id per line)
nano INPUT_user/structure_manifest.tsv

# 4. Run — single entry point for both local and SLURM
bash RUN-workflow.sh
```

The conda environment (`aiG-ocl_phylogenetic_structures-annotations_X_ocl`,
per §28 — renamed from the legacy `aiG-ocl_phylogenetic_structures-annotations_X_ocl`
during the OCL reorg) is created on-demand from
`ai/conda_environment.yml` on first run.

### The 7-Script Pipeline (workflow-COPYME-ocl_analysis/ai/scripts/)

| Script | Purpose | Key Output |
|--------|---------|------------|
| 001 | Create annogroups from per-species annotation files | Annogroup catalog with single/combo/zero subtypes |
| 002 | Determine MRCA origin of each annogroup | Annogroup origins with `Origin_Phylogenetic_Block` and `Origin_Phylogenetic_Block_State` |
| 003 | Classify each (block, annogroup) pair into the five-state vocabulary (A/O/P/L/X) | Per-block stats, per-annogroup patterns |
| 004 | Generate comprehensive summaries per subtype + all-types | Complete OCL summary tables |
| 005 | Validate all results (fail-fast per §36) | Validation report, error log, QC metrics |
| 006 | Write run log (per §45) | Timestamped log of this run |
| 007 | Aggregate run summary across structures | Per-RUN aggregate `RUN_SUMMARY.md` |

Scripts are sequential per structure but parallel across structures
(NextFlow manages this).

### Output Per Structure

```
OUTPUT_pipeline/structure_NNN/
├── 1-output/    Annogroups built from per-species annotations
├── 2-output/    Annogroup origins + per-clade files
├── 3-output/    Conservation/loss per block + per annogroup
├── 4-output/    Comprehensive summaries (primary downstream files,
│                including 4_ai-structure_NNN_annogroups-complete_ocl_summary-all_types.tsv)
├── 5-output/    Validation report + QC metrics
└── logs/        Per-script log files
```
