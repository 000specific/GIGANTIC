# AI Guide: orthogroups_X_ocl Subproject

**AI**: Claude Code | Opus 4.6 | 2026 April 13
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

Performs Origin-Conservation-Loss (OCL) analysis of orthogroups across phylogenetic
species tree structures. For each orthogroup, determines:

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
├── research_notebook/
│   └── ai_research/
├── output_to_input/                            # Downstream output
│   └── BLOCK_ocl_analysis/                    # Contains run_label subdirs
│       ├── species70_X_OrthoHMM/               # From RUN copy with that label
│       │   ├── structure_001/
│       │   │   └── 4_ai-orthogroups-complete_ocl_summary.tsv
│       │   └── ...
│       └── species70_X_OrthoFinder/            # From another RUN copy
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
                ├── 001_ai-python-prepare_inputs.py
                ├── 002_ai-python-determine_origins.py
                ├── 003_ai-python-quantify_conservation_loss.py
                ├── 004_ai-python-comprehensive_ocl_analysis.py
                ├── 005_ai-python-validate_results.py
                └── 006_ai-python-write_run_log.py
```

### Planned STEP_2

A second step is planned to aggregate across structures and rank candidate
species trees by total-loss minimization (an Occam's-razor-style scoring):

```
└── STEP_2-occams_tree/   # PLANNED
    └── workflow-COPYME-.../
        Reads: STEP_1's per-structure OCL summaries
        Outputs: cross-structure comparison table + structure ranking
```

**Note on structure_001**: Script 002 in trees_species always assigns
`structure_001` to the user-provided species tree. So STEP_2's ranking will
directly tell us how the user's input tree compares to alternative topologies.

---

## Key Concepts

### Phylogenetic Blocks and Block-States (Rule 7)

OCL analysis operates on two related kinds of tree objects, defined in Rule 7
of `../../AI_GUIDE-project.md`:

- A **phylogenetic block** is a single parent-to-child edge of a species tree
  structure, containing both endpoint clades with no intervening nodes.
  Written `parent_clade_id_name::child_clade_id_name` (e.g.
  `C069_Holozoa::C082_Metazoa`). Feature-agnostic.

- A **phylogenetic block-state** is a block paired with a specific orthogroup's
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

Event blocks carry state O or L (orthogroup state changes between parent and
child); inheritance blocks carry state A, P, or X (state persists). The
distinction between A and X — both have absent parent and child — is
historical: A lives upstream of the origin (orthogroup never arose in this
part of the tree), X lives downstream of a loss (orthogroup was present
upstream and has been lost).

Full specification with mathematical definitions, identifier hierarchy, prose
conventions, and implementation notes:
`research_notebook/ai_research/planning-phylogenetic_blocks_and_locks/whitepaper.md`.

### TEMPLATE_03 Dual-Metric Tracking

Script 003's TEMPLATE_03 algorithm classifies each (block, orthogroup) pair
into states P, L, and the combined-absence category (A ∪ X). Origin (state O)
is emitted separately by Script 002. The per-event counts (conservation,
loss_at_origin, continued_absence, loss_coverage) map onto the five-state
vocabulary as:

| TEMPLATE_03 event | Five-state letter | Parent | Child |
|---|---|---|---|
| Conservation | P | Yes | Yes |
| Loss at Origin | L | Yes | No |
| Continued Absence | X (post-loss) or A (pre-origin) | No | No |
| Loss Coverage | L + (A ∪ X); total absent-child | — | No |
| (Origin event, from Script 002) | O | No | Yes |

TEMPLATE_03's "actually present in species" is a descendant-intersection
test (at least one descendant species of the clade carries the orthogroup),
distinguishing it from purely phylogenetic inheritance (orthogroup's origin
lies on this clade's root-to-node path).

### COPYME Multi-Tool Coexistence

This subproject supports running OCL analysis with different orthogroup clustering tools
(OrthoFinder, OrthoHMM, Broccoli). Each exploration gets its own COPYME copy:

```
workflow-RUN_01-ocl_analysis/  → run_label: "species70_X_OrthoHMM"
workflow-RUN_02-ocl_analysis/  → run_label: "species70_X_OrthoFinder"
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

### Clade IDs — Topologically-Structured Species Sets

Clade identifiers consumed here (e.g., `C082_Metazoa`) come from
`trees_species/BLOCK_permutations_and_features/` and identify
**topologically-structured species sets** — unique combinations of species
content and branching arrangement. Same biological clade → same
`clade_id_name` across every candidate species tree structure.

**Usage convention in OCL code**: treat `clade_id_name` as a single atomic
identifier — never split into `clade_id` and `clade_name` for dict lookups
or cross-table joins. Separate `clade_id` and `clade_name` columns appear in
TSV outputs for human-readable display, but the code path uses
`clade_id_name` consistently to avoid the ambiguity of mixing
representations (which has caused bugs in the past).

Future cross-structure aggregation (e.g., the planned `occams_tree`
subproject) will use `clade_id_name` as a global key across structures — no
structure-prefixed composite is needed because the upstream clade assignment
policy already makes the same biological clade share an ID across structures.

For the full canonical definition, see Rule 6 in
`../../AI_GUIDE-project.md` or `../trees_species/README.md` (Terminology
section).

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
| `START_HERE-user_config.yaml` | Yes | All configuration: run_label, tool, paths, FASTA flag, `execution_mode` (local or slurm), SLURM account/qos, `resume` flag, `cpus` + `memory_gb` for SLURM sizing. For parallel per-structure runs: `cpus = N_structures + 1`, `memory_gb = cpus × 7.5` (HiPerGator ratio) — see "CPU and Memory Configuration" in `../../AI_GUIDE-project.md` for full rationale |
| `INPUT_user/structure_manifest.tsv` | Yes | Which tree structures to analyze (one structure_id per line) |
| `RUN-workflow.sh` | No | Single entry point: `bash RUN-workflow.sh`. If `execution_mode: "slurm"`, self-submits as a SLURM job via `sbatch`. Also creates per-STEP conda env on first run from `ai/conda_environment.yml` |
| `ai/conda_environment.yml` | No | Per-BLOCK conda env spec (name: `aiG-orthogroups_X_ocl-ocl_analysis`) |
| `ai/main.nf` | No | NextFlow pipeline definition |
| `ai/nextflow.config` | No | NextFlow executor settings; RUN-workflow.sh passes `-profile local` so processes run within the outer SLURM job |

---

## Questions to Ask

| Situation | Ask |
|-----------|-----|
| User wants to run OCL analysis | "Which orthogroup tool should I use? (OrthoFinder, OrthoHMM, Broccoli)" |
| User wants a subset of structures | "Which structure IDs should I add to the manifest?" |
| Large output files | "Should FASTA sequences be embedded in output tables? (default: no)" |
| Validation failures | "Would you like me to investigate the error log?" |
