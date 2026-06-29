# BLOCK_annotations_X_ocl

<!-- ============================================================================
History: this BLOCK is what used to be the `annotations_X_ocl/` subproject.
Migrated 2026-05-29 (OCL reorg Phase 1, Commit 3/6) under the new parent
`ocl_phylogenetic_structures/`. The body below is largely the original
subproject documentation with path/title cross-references corrected for
the new depth. Phase 5 will harvest the methodology content into the
parent README and slim this BLOCK README to BLOCK-specific concerns.
============================================================================ -->

Origin-Conservation-Loss (OCL) analysis of annotation groups (annogroups) across species tree topologies.

## What This BLOCK Does

**Annogroups are NOT computed here.** They are produced once, structure-independent,
by the **`annogroups` subproject** (`BLOCK_build_annogroups`). This BLOCK *imports*
them and **maps them onto each species tree structure** to determine:

1. **Origin**: The most recent common ancestor (MRCA) clade where each annogroup first appeared
2. **Conservation**: Tracking which phylogenetic blocks retain the annogroup
3. **Loss**: Distinguishing first-loss events from downstream absences using the five-state block-state vocabulary (A/O/P/L/X)

Annogroups are sequences grouped by shared annotation features, per source. The
annogroups subproject defines four canonical types (`feature`, `combination`,
`architecture`, `absent`). This BLOCK maps the **origin-bearing** types
(`feature`, `combination`, `architecture`) onto the structures.

**`absent` is excluded by design**: OCL is an origin engine, and `absent`
(sequences sharing no feature) has no single evolutionary origin — its MRCA would
resolve to the root, present everywhere, a meaningless inference. The selected
types are set in `START_HERE-user_config.yaml` (`annogroup_types`).

Processes all selected annogroups across user-selected species tree topologies in parallel.

## Terminology

- **Phylogenetic block**: A single parent-to-child edge of a species tree
  structure -- the parent clade, the child clade, and the edge joining them,
  with no intervening nodes. Written `parent_clade_id_name::child_clade_id_name`
  (e.g. `C069_Holozoa::C082_Metazoa`). Feature-agnostic: the block is a
  structural fact about the tree, independent of any annogroup. This is the
  computational atom on which OCL origins, conservation, and losses are
  resolved.

- **Phylogenetic block-state**: A phylogenetic block paired with a specific
  annogroup's state on that block, written
  `parent_clade_id_name::child_clade_id_name-LETTER` (e.g.
  `C069_Holozoa::C082_Metazoa-O`). The LETTER is one of five codes refining
  classical Dollo: **A** Inherited Absence (pre-origin), **O** Origin,
  **P** Inherited Presence (conservation), **L** Loss, **X** Inherited Loss
  (post-loss). Event blocks carry state O or L (evolutionary change);
  inheritance blocks carry state A, P, or X (state persists across the block).

- **Phylogenetic path**: The path on a given phylogenetic species tree from
  `C000_OOL` (Origin Of Life) down to a species leaf.

- **Phylogenetic path-state**: A path paired with a specific annogroup's state
  along each block of the path, written as concatenated five-state letters in
  OOL-end-to-species-end order (e.g. `AAAOPLXX`). The compact fingerprint of
  an annogroup's inferred evolutionary history along one species's lineage.

- **Clade ID (`clade_id_name`)**: identifies a **topologically-structured
  species set** -- a unique combination of descendant species and their
  branching arrangement. Produced upstream by
  `trees_species/BLOCK_permutations_and_features/`. Same biological clade
  receives the same `clade_id_name` across every candidate species tree
  structure. Used as the canonical atomic identifier throughout this subproject
  (never split into `clade_id` and `clade_name` for lookups).

For full canonical definitions of Rules 1-7, see `../../../AI_GUIDE.md`.

## Design: One Run Fans Out Per Annotation Source

The OCL algorithm is database-agnostic -- the same pipeline works regardless of which
annotation database (pfam, gene3d, deeploc, signalp, tmbed, metapredict) produced the input.

A single run analyzes EVERY source listed in `annotation_databases` (`"all"` or a
list) in parallel, fanning out over **source x 105 structures**. Each source writes
to its own subtree (`OUTPUT_pipeline/<source>/...`) and publishes to
`output_to_input/BLOCK_annotations_X_ocl/<species_set>_<source>/`:
- `species70_pfam/`, `species70_go/`, `species70_panther/` -- all from one run.

So the per-source results coexist (they are NOT separate RUN versions: per the
GIGANTIC convention the latest RUN of this block supersedes earlier ones). The
`<species_set>_<source>` namespace also preserves the downstream consumer contract
(e.g. the integrator's `annogroup_ocl_run_label: "species70_pfam"`).

### Annogroup Types Mapped Onto Structures

The annogroups subproject produces four canonical types per source; OCL maps the
origin-bearing types (`absent` excluded — see above). Which types a source has
depends on its data (positional vs whole-protein), determined in the annogroups
subproject, not here.

| Source kind | Examples | Origin-bearing types OCL maps |
|---|---|---|
| Positional (domains/segments) | pfam, gene3d, superfamily, smart, cdd, tmbed, signalp | feature, combination, architecture |
| Whole-protein label | deeploc | feature, combination |

## Running the Workflow

Single entry point -- `bash RUN-workflow.sh`. Execution location is controlled
by `execution_mode` in `START_HERE-user_config.yaml`:

- `execution_mode: "local"` -> runs on the current machine
- `execution_mode: "slurm"` -> self-submits to SLURM with cpus/memory/time/account/qos from the same yaml

The conda environment (`aiG-ocl_phylogenetic_structures-annotations_X_ocl`) is created on-demand
from `ai/conda_environment.yml` on first run -- no separate install step needed.

## Fail-Fast Validation

Script 005 validates all results with strict fail-fast behavior: ANY validation failure
causes exit code 1 and stops the pipeline. Edge cases (division by zero for zero-transition
annogroups) are handled explicitly in Scripts 003-004 so they never produce invalid metrics
that validation would flag.

## Directory Structure (post-reorg)

```
ocl_phylogenetic_structures/               # parent subproject (NEW)
├── README.md, AI_GUIDE.md                 # parent docs
├── output_to_input/                       # parent-level (per §2 mirrors producer paths)
│   ├── BLOCK_annotations_X_ocl/           # this BLOCK's downstream symlinks
│   │   ├── species70_pfam/                # <species_set>_<source>, one per source
│   │   │   ├── structure_001/             #   from a SINGLE multi-source run
│   │   │   └── ...
│   │   ├── species70_go/
│   │   └── species70_panther/
│   └── BLOCK_orthogroups_X_ocl/           # sibling BLOCK's downstream symlinks
├── upload_to_server/                      # parent-level publishing
# (no per-subproject research_notebook/ per §1; sandbox at
#  ../../research_notebook/research_ai/subproject-ocl_phylogenetic_structures/)
├── RUN-update_upload_to_server.sh         # parent-level publisher (§38)
│
└── BLOCK_annotations_X_ocl/               # THIS BLOCK
    ├── README.md                          # THIS FILE
    ├── AI_GUIDE.md                        # BLOCK-level AI guide (consolidated per §3)
    └── workflow-COPYME-ocl_analysis/
        ├── START_HERE-user_config.yaml
        ├── RUN-workflow.sh                # Self-submits to SLURM if execution_mode=slurm
        ├── INPUT_user/                    # structure_manifest.tsv
        ├── OUTPUT_pipeline/               # Results per structure
        └── ai/
            ├── conda_environment.yml      # Per-BLOCK env (on-demand create)
            ├── main.nf
            ├── nextflow.config
            └── scripts/                   # Python scripts (001-007)
```

## Dependencies

### BLOCK_annotations_X_ocl reads FROM:
- `../../trees_species/output_to_input/BLOCK_permutations_and_features/` - Phylogenetic blocks,
  paths, parent-child relationships, clade-species mappings
- `../../annogroups/output_to_input/BLOCK_build_annogroups/` - Annogroup map per source
  (`<species_set>/<source>/2_ai-<source>-annogroup_map.tsv`), computed once and
  structure-independent (set via `annogroups_dir` in config)

### BLOCK_annotations_X_ocl provides TO:
- Parent `output_to_input/` for downstream analysis
- Sibling BLOCK `BLOCK_orthogroups_X_ocl/` (combined functional/orthology views)
- Cross-database comparison analyses
- upload_to_server for GIGANTIC server

---

## Session hygiene (per §61 in `ai/ai_FYIs/gigantic_conventions.md`)

GIGANTIC's chat-as-research-notebook convention (§9) works best with
disciplined session hygiene. Two recommendations.

### Always root at the named gigantic_project-COPYME

Every chat session for project work should be initiated rooted at the
user's renamed copy of `gigantic_project-COPYME/` — e.g.,
`gigantic_project-cephalopod_evolution/`.

**Not** at:
- `GIGANTIC/` (the framework root, reserved for framework-development
  sessions per §16)
- `subprojects/<X>/` (a subproject directory)
- `subprojects/<X>/<BLOCK_or_STEP>/workflow-COPYME-*/` (a workflow directory)
- Any other directory deeper than the named project root

Why: the renamed project copy is the canonical session root. All
project conventions, INPUT_user paths, research_notebook captures,
and AI guidance are scoped to that directory. Rooting deeper than
that scopes the AI's view too narrowly and loses cross-subproject
context (and the AI guides at lower levels assume the session was
rooted above them). Rooting at `GIGANTIC/` is reserved for
framework-development sessions per §16.

### One chat session per subproject + a side channel for small questions

For productive project work:

- **One session per subproject** you're actively working in. A session
  focused on `phylonames/` is different from one focused on
  `genomesDB/` is different from one focused on `trees_species/` —
  each maintains its own context, convention reminders, and recent
  state.
- **Continue the same session over many compactions** until it
  becomes overly reactive, muddled, or slow. Compactions are
  lossless (per §9 the full transcript is captured), so a long
  session isn't a problem until it starts feeling like one.
- **When a session goes muddled, start a fresh one** at the same
  named `gigantic_project-*/` root, focused on the same subproject,
  and bring it back up to speed (read the relevant AI_GUIDEs, recent
  commits, etc.).
- **Keep a separate "small questions" session** for random or
  cross-cutting questions (e.g., "what does this convention mean?"
  or "is this NCBI accession a GCF or GCA?"). This keeps the
  subproject sessions focused on their actual work and prevents
  context pollution.

### What this prevents

- Sessions that try to hold every subproject's state in context and
  end up confused about which one they're operating on.
- Sessions that get derailed by one-off questions and lose their
  thread on the subproject work.
- Session captures (per §9) that mix multiple unrelated subprojects
  into a single transcript, making the lab-notebook record harder
  to grep later.
