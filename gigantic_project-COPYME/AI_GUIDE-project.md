# AI Guide: GIGANTIC Project

**For AI Assistants**: This is the master guide for GIGANTIC. Read this first when helping any user with a GIGANTIC project. Subproject and workflow guides reference this document - don't repeat information that's here.

---

## ⚠️ CRITICAL: Zero Tolerance for Silent Artifacts in Research Results

**GIGANTIC produces scientific results that get published and shape research. A false positive in a gene tree, a phantom homolog in an AGS, or a misassigned sequence is not a minor inconvenience — it is a research integrity failure. It can misdirect the field, waste other researchers' time and funding, and destroy careers.**

**This is not an app. There is no "good enough." There is no "probably fine in practice."**

The moment any code path is identified that could generate biological artifacts — false positives, false negatives, or misassignments in research outputs — it must be:

1. **Flagged immediately and explicitly** to the user
2. **Investigated fully** before being rationalized away
3. **Fixed or explicitly accepted** — never silently tolerated

**❌ NEVER:**
- Reason that a known bug "probably has minimal impact in practice" without verifying
- Apply fail-fast only to pipeline crashes, not to biological correctness
- Decide silently that something is "close enough" for research results

**✅ ALWAYS:**
- Treat any known artifact-generating code path as a critical failure requiring investigation
- Check actual pipeline outputs before making claims about correctness
- Require explicit user sign-off before accepting any known source of potential artifacts

**Some tolerance for slop is legitimate** — e.g., e-value thresholds, filter cutoffs are design decisions. But these must be **explicit decisions made by the user**, not something the AI silently decides is acceptable.

---

## ⚠️ CRITICAL: Surface Discrepancies - No Silent Changes

**The user is managing this project - you must surface discrepancies so the user can make decisions. Silent changes undermine project management.**

- ❌ **NEVER** silently do something different than requested
- ❌ **NEVER** assume you know better and proceed without asking
- ✅ **ALWAYS** stop and explain the discrepancy
- ✅ **ALWAYS** ask for clarification before proceeding

**Example**: If user says "put this in script 3" but script 3 handles genomes not proteomes, you must say: "Script 003 handles genomes, not proteomes - did you mean script 002, or should I create a new script?"

---

## Quick Reference

| If user needs... | Go to... |
|------------------|----------|
| Project overview, directory structure | This file |
| Subproject-specific help | `subprojects/[name]/AI_GUIDE-[name].md` |
| Workflow execution help | `subprojects/[name]/workflow-*/ai/AI_GUIDE-*_workflow.md` |

---

## ⚠️ CRITICAL: GIGANTIC Terminology Discipline

GIGANTIC is a phylogenomic platform with several pairs of distinct concepts
that look similar but must NOT be used interchangeably. The full canonical
worked examples of all rules below live in
`subprojects/trees_species/README.md` (Terminology section). The compact
versions below are sufficient for day-to-day work.

### Rule 1: Phylogenetic vs Evolutionary

- **phylogenetic** refers ONLY to a species tree as a data structure —
  its topology, structural components, and relationships expressed by the
  species tree itself. Use for: `phylogenetic_tree`, `phylogenetic_path`
  (root-to-tip walk on a species tree), `phylogenetic_block` (a parent::child
  edge on a species tree), `phylogenetic relationships between clades`,
  parent-child tables derived from a species tree.

- **evolutionary** refers to biology — both (a) actual biological history
  in nature, and (b) biological patterns inferred by combining feature
  data with a species tree. Use for: "evolutionary history," "evolutionary
  relatives," "evolutionary patterns of conservation and loss," "evolutionary
  origin of an orthogroup," "evolutionary OCL inferences."

**The clean mental model**:

> `trees_species` produces PHYLOGENETIC data (species tree structures on disk).
> `orthogroups` / `annotations` produce FEATURE data.
> `orthogroups_X_ocl` / `annotations_X_ocl` combine the two to produce
> EVOLUTIONARY inferences.

**Atomic terms exception**: `phylogenetic block` and `phylogenetic path` are
single named concepts in GIGANTIC vocabulary. Do NOT inject `species tree`
into these compound terms (no "phylogenetic species tree block"). Qualify
the surrounding context if needed.

### Rule 2: Structure vs Topology (Species Tree)

- A **structure** is the persistent identity of one resolved binary species
  tree variant tracked through `trees_species/`, identified by `structure_NNN`
  (e.g., `structure_001` through `structure_105`). The structure is the
  *who* — the persistent identifier.

- A **topology** is the abstract branching pattern of a structure — the
  arrangement of clades, ignoring labels and branch lengths. The (2N-3)!!
  formula counts topologies. The topology is the *what* — the branching
  pattern.

> Every structure has a topology; every topology becomes one structure when
> the pipeline instantiates it (assigns clade identifiers, grafts species
> subtrees, adds branch lengths and metadata).

The two terms are not synonyms. Script 002 enumerates topologies; Script 004
builds complete species trees from those topologies; downstream OCL operates
on structures via `structure_manifest.tsv`.

### Rule 3: Resolved vs Unresolved Input Species Tree

- **Resolved** input (no polytomies/ambiguities) → pipeline produces 1
  structure (`structure_001` = the input species tree)
- **Unresolved** input (N ambiguous nodes) → pipeline produces (2N-3)!!
  structures (each one a different binary resolution of the input)

**Every structure produced by the pipeline is itself resolved by
construction. The resolution status is a property of the input, not of
any specific structure.**

### Rule 4: Tree References Must Be Explicit (Species Tree vs Gene Tree)

GIGANTIC works with two fundamentally different kinds of phylogenetic trees:

- **species tree**: relationships between species (one per species set;
  produced by `trees_species/`; leaves are species)
- **gene tree**: relationships between gene copies for a gene family or
  group (produced by `trees_gene_families/` or `trees_gene_groups/`;
  leaves are gene copies)

**Documentation rule (strict)**: Always qualify tree references as `species
tree` or `gene tree` in READMEs, AI_GUIDEs, design documents, INPUT_user
READMEs, and config file comments. The qualification "phylogenetic tree"
alone is also ambiguous — make it specific.

**Code rule (context-tolerant)**: In code, bare `tree` references are
acceptable when the surrounding subproject context makes the kind of tree
unambiguous. Strict qualification is for documentation, not code.

### Rule 5: Hierarchies vs Trees — Origin vs Root

- **Trees** (species trees, gene trees) have a **root**. Edges represent
  inferred biological relationships (descent, divergence). Rooting is an
  analytical choice.

- **Hierarchies** (the NCBI taxonomic classification) have an **origin**.
  Edges represent set inclusion (`Mammalia ⊂ Chordata`). They are
  definitional, not inferred. A hierarchy is intrinsically singly-originated;
  there is no "unrooted hierarchy."

**Rule**: Do not refer to taxonomy as a "tree" or to its topmost node as a
"root." Use "hierarchy" and "origin" instead. Do not write "rooted hierarchy"
— this is a category error.

### Rule 6: Clade IDs as Topologically-Structured Species Sets

A clade identifier (`clade_id_name`, e.g., `C082_Metazoa`) identifies a
**topologically-structured species set** — a specific combination of:

1. **Species content**: the exact set of descendant species under this clade
2. **Topological arrangement**: the branching pattern of those species as
   seen from this clade's subtree

Two clades across different species tree structures are the SAME clade (same
`clade_id_name`) if and only if BOTH (1) and (2) match. Different species
content OR different branching arrangement = different biological clade with
a different `clade_id`.

**Implications:**

- Named clades outside the unresolved zone (Metazoa, Bilateria, Mammalia,
  etc.) have **globally stable `clade_id_name` across all candidate species
  tree structures** — the same biological grouping receives the same ID in
  every one of the (2N-3)!! structures produced from N unresolved clades.
- Within the unresolved zone, an internal grouping like `(Bilateria,
  Cnidaria)` in one structure and `(Bilateria, Placozoa)` in another are
  DIFFERENT biological groupings and receive different `clade_id_name`
  (even when both are auto-named `Clade_NNN` style).
- If the same ambiguous-zone grouping happens to appear in multiple
  candidate topologies, it receives the SAME `clade_id` in each — because
  its topologically-structured species set is identical.
- **Cross-structure aggregation** (e.g., in the planned `occams_tree`
  subproject that ranks topologies by total-loss parsimony) can safely use
  `clade_id_name` as a global key: if two rows across structures share a
  `clade_id_name`, they refer to the same biological clade.

**Identifier usage convention**: `clade_id_name` is the canonical atomic
identifier — always used as a single unit, never split into `clade_id` and
`clade_name` for internal lookups. Separate `clade_id` and `clade_name`
columns may appear in TSV outputs for human-readable display, but code paths
use `clade_id_name` consistently to avoid ambiguity.

**Implementation**:
`trees_species/BLOCK_permutations_and_features/ai/scripts/003_ai-python-assign_clade_identifiers.py`
computes a canonical (alphabetically-sorted) topological signature for every
internal node and assigns `clade_id` accordingly — new ID when the signature
is novel, reuse when the signature has been registered in any prior structure.
The registry file tracks `appears_in_structures` (which of the candidate
structures each clade appears in).

### Rule 7: Phylogenetic Blocks, Block-States, and the Five-State Vocabulary

GIGANTIC distinguishes tree-structural edges from per-feature states on those
edges using a three-level identifier hierarchy built on `::` and `-LETTER`
suffixes.

- A **phylogenetic block** is a single parent-to-child edge of a species tree
  structure — the parent clade, the child clade, and the edge joining them,
  with no intervening nodes. Written `parent_clade_id_name::child_clade_id_name`
  (e.g. `C069_Holozoa::C082_Metazoa`). Feature-agnostic: the block exists as a
  structural fact about the species tree, independent of any feature.

- A **phylogenetic block-state** is a block paired with a specific feature's
  state on that block. Written `parent_clade_id_name::child_clade_id_name-LETTER`
  (e.g. `C069_Holozoa::C082_Metazoa-O`). Feature-specific: the same block has
  different block-states for different features.

- The **five-state vocabulary** refines classical Dollo by separating two
  kinds of absence: pre-origin absence (feature has not yet arisen) and
  post-loss absence (feature was present upstream and has been lost).

| Letter | State | Parent | Child | Kind |
|---|---|---|---|---|
| **A** | Inherited Absence | absent | absent (pre-origin) | inheritance |
| **O** | Origin | absent | present | event |
| **P** | Inherited Presence | present | present | inheritance |
| **L** | Loss | present | absent | event |
| **X** | Inherited Loss | absent | absent (post-loss) | inheritance |

- **Phylogenetic event blocks** carry state **O** or **L** — the feature's
  state differs between the parent and child endpoints, so an evolutionary
  change is localized to this block.

- **Phylogenetic inheritance blocks** carry state **A**, **P**, or **X** —
  the feature's state is the same at both endpoints; it has been inherited
  across the block rather than changed on it.

**Key implications**:

- An event block's identification claims: at some point within the real
  evolutionary time and biological events the block represents, a change in
  the feature's state occurred between the parent and child endpoints. The
  block is the resolution; within-block placement is not available from the
  species tree alone.
- Every phylogenetic block, for every feature, falls into exactly one of the
  five states. Per-structure OCL accounting is a partition of all blocks in
  the structure into these five categories per feature.
- The origin-block invariant carries cleanly: the block carrying state O for
  a feature is the first block where the feature appears; blocks upstream on
  the root-to-origin path are all state A; blocks immediately downstream are
  state P unless intervening losses put them in state L or X.

**Prose conventions**:

- *the Holozoa-Metazoa phylogenetic block* — both endpoint clade names, because
  both are contained in the block.
- *the Holozoa-Metazoa phylogenetic block in state O for orthogroup OG0000001* —
  block, state letter, feature in scope all explicit.
- Avoid *"the block entering Metazoa"* (directional/agentive), *"the block
  between Holozoa and Metazoa"* ("between" excludes endpoints), or *"conserved
  across this block"* (in biology "conserved across X" refers to parallel
  lineages, not a single parent-child edge).

**Phylogenetic paths and phylogenetic path-states**:

Blocks and paths are the same substrate viewed at two granularities:

- A **phylogenetic block** is the atomic unit — one parent-to-child edge of a
  species tree structure.
- A **phylogenetic path** is a chain of consecutive phylogenetic blocks — the
  walk from the conceptual biological parent of the species-tree root down
  to one species. Every species in the structure has exactly one phylogenetic
  path. The path is literally a sequence of blocks laid end-to-end.

  Every path begins at `C000_OOL` — Origin Of Life — which GIGANTIC treats as
  the conceptual biological parent of any user-provided rooted species tree.
  OOL is not a synthetic parsing device: every real clade ultimately descends
  from OOL, so including it at the start of every path is biologically
  accurate and gives the phylogenetic block INTO the species-tree root the
  same representation as every other block. `trees_species` synthesizes OOL
  automatically when processing the user's species tree — users do not need
  to add it themselves.

Written `start_clade_id_name>>end_clade_id_name` (e.g.
`C000_OOL>>C040_Caenorhabditis_elegans`) using `>>` to distinguish from
block's `::`. Feature-agnostic: the path is a structural fact about the
species tree.

- A **phylogenetic path-state** is a path paired with a specific feature's
  state along each block of that path. Written as the concatenated five-state
  letters in root-to-tip order (e.g. `AAAOPLXX`). Feature-specific: the same
  path has different path-states for different features. A path-state is the
  compact fingerprint of a feature's biological evolutionary history along
  that one species's lineage.

The biological purpose of this vocabulary:

- Every evolutionary event (origin, loss) has to happen on some phylogenetic
  block — that is the smallest chunk of evolution the species tree can
  resolve. Blocks are the atomic unit of OCL analysis.
- Every species's full evolutionary history on the tree is its phylogenetic
  path. The path-state for a feature tells you, in a single string, where
  origins and losses localized on that species's lineage and what the feature
  looked like at every intermediate ancestor.
- `trees_species` produces the phylogenetic structural substrate (blocks,
  paths). `orthogroups_X_ocl` / `annotations_X_ocl` combine that substrate
  with feature data to produce the evolutionary inferences (block-states,
  path-states).

**Full specification**:
`subprojects/orthogroups_X_ocl/research_notebook/ai_research/planning-phylogenetic_blocks_and_locks/whitepaper.md`
contains the complete mathematical and phylogenetic definitions, identifier
reference, implementation notes for Scripts 002-005, and the state life-cycle
diagram.

---

## What GIGANTIC Is

**GIGANTIC** = Genome Integration and Gene Analysis across Numerous Topology-Interrogated Clades

A modular phylogenomics platform for comparative genomics. Key facts:
- **AI-native**: AI assistants are the expected way users run GIGANTIC
- **Developed through**: AI pair programming (Claude Code, Opus 4.5) with Eric Edsinger
- Users copy `gigantic_project-COPYME/` and rename it for their project

---

## AI-Native Open Source Model

GIGANTIC assumes users will work with an AI assistant to implement the platform. This is not optional guidance - it is a core design assumption that shapes how GIGANTIC is built, documented, and distributed.

**Traditional model**: Ship a containerized package that works out of the box but quickly becomes outdated. The developer maintains the container, patches dependencies, and responds to user issues. The developer is the bottleneck.

**GIGANTIC model**: Ship fully developed modular frameworks, workflows, and pipelines - operational and tested at release time - with dual-layer documentation: READMEs for humans and AI_GUIDEs for their AI assistants. Users deploy using current tool versions, adapted to their local environment by their AI assistant.

**What this means for you as an AI assistant**:
- The AI_GUIDE files are written specifically for you to read and act on
- You are expected to install current versions of bioinformatics tools (BLAST, MAFFT, IQ-TREE, etc.) rather than relying on pre-packaged versions
- You should adapt conda environments, file paths, and resource configurations to the user's system
- When tools have been updated since the GIGANTIC release, use the latest versions and adjust scripts if needed
- The user may not be a bioinformatics expert - you bridge that gap

**Benefits of this approach**:
- Pipelines improve with time (current tools, current AI capabilities) rather than decaying
- No waiting on the GIGANTIC developer to fix environment-specific issues
- More powerful pipelines without generalization compromises
- Each deployment is tailored to the user's specific system and needs

---

## Complete Directory Structure

All paths are relative to `gigantic_project-[project_name]/` (the copied project root).

```
gigantic_project-[project_name]/
│
├── AI_GUIDE-project.md              # THIS FILE - project-level AI guidance
├── RUN-setup_environments.sh        # OPTIONAL: Pre-creates all conda environments (on-demand by default)
├── RUN-record_project.sh            # Extract Claude sessions for entire project
│
├── ai/                              # AI TOOLS
│   └── tools/                       # Extraction and utility scripts
│       └── 001_ai-python-extract_claude_sessions.py
│
├── conda_environments/              # CONDA ENVIRONMENT DEFINITIONS
│   ├── README.md                    # Environment documentation
│   └── ai_gigantic_[subproject].yml # One file per subproject
│
├── INPUT_user/                      # USER-PROVIDED GENOMIC RESOURCES
│   │                                # RUN scripts copy relevant files to workflow INPUT_user/ for archival
│   ├── README.md                    # "Start Here" - formatting instructions
│   ├── species_set/
│   │   └── species_list.txt         # Canonical species list for the project
│   └── genomic_resources/
│       ├── genomes/                 # Genome assembly .fasta files
│       ├── proteomes/               # Proteome amino acid .aa files
│       ├── annotations/             # GFF3/GTF annotation files
│       └── maps/                    # Identifier mapping .tsv files
│
├── research_notebook/               # RESEARCH DOCUMENTATION
│   ├── research_user/               # User's open sandbox (no structure, no rules)
│   │                                # Use for anything - notes, literature, drafts, analyses
│   └── research_ai/                 # AI session provenance (project-wide)
│       └── sessions/                # All AI session extractions (flat, project-wide)
│                                    # Sessions can span subprojects, so kept together
│
└── subprojects/                     # ANALYSIS MODULES
    │
    └── [subproject_name]/           # Each subproject follows this pattern:
        │                            # May contain STEP_N-name/ (sequential) or
        │                            # BLOCK_name/ (standalone) subdirectories
        │
        ├── README.md                    # Human documentation
        ├── AI_GUIDE-[name].md           # AI guidance (references this project guide)
        ├── RUN-clean_and_record_subproject.sh  # Cleanup + session recording
        ├── RUN-update_upload_to_server.sh      # Updates server sharing symlinks
        │
        ├── user_research/               # Subproject-specific personal workspace
        │                                # Alternative to project-level research_notebook/research_user/
        │
        ├── output_to_input/             # OUTPUTS FOR OTHER SUBPROJECTS
        │   │                            # Single canonical location per subproject
        │   │                            # Contains BLOCK_X/ or STEP_X/ subdirectories
        │   │                            # RUN-workflow.sh creates symlinks here
        │   │                            # Other subprojects read from here
        │   ├── BLOCK_X/                 # (orthogroups example - one dir per BLOCK)
        │   ├── STEP_2-standardize/      # (genomesDB example - one dir per STEP)
        │   └── maps/                    # (phylonames example - flat subproject)
        │
        ├── upload_to_server/            # OUTPUTS FOR GIGANTIC SERVER
        │   ├── upload_manifest.tsv      # Controls what gets shared
        │   └── [symlinks]               # Created by RUN-update_upload_to_server.sh
        │
        ├── workflow-COPYME-[name]/          # WORKFLOW TEMPLATE (not numbered)
        │   │                                # Only ONE COPYME per workflow type
        │   │
        │   ├── README.md                    # Quick start guide
        │   ├── RUN-workflow.sh              # Local execution: bash RUN-workflow.sh
        │   ├── RUN-workflow.sbatch          # SLURM execution: sbatch RUN-workflow.sbatch
        │   ├── START_HERE-user_config.yaml  # User configuration (edit before running)
        │   │
        │   ├── INPUT_user/                  # WORKFLOW INPUTS
        │   │   │                            # Copied from project INPUT_user/ at runtime
        │   │   └── [input files]            # Archived with this workflow run
        │   │
        │   ├── OUTPUT_pipeline/             # WORKFLOW OUTPUTS
        │   │   ├── N-output/                # Script N outputs (numbered for transparency)
        │   │   └── ...
        │   │
        │   └── ai/                          # INTERNAL (users don't touch)
        │       ├── AI_GUIDE-*_workflow.md   # Workflow-level AI guidance
        │       ├── main.nf                  # NextFlow pipeline
        │       ├── nextflow.config          # NextFlow settings
        │       ├── scripts/                 # Python/Bash scripts
        │       ├── logs/                    # Workflow run logs (written by write_run_log)
        │       └── validation/              # Validation outputs
        │
        └── workflow-RUN_XX-[name]/          # WORKFLOW RUN INSTANCES (numbered)
            │                                # Copy from COPYME, increment XX for each run
            └── [same structure as COPYME]
```

---

## Key Patterns

### STEP vs BLOCK: When to use which inside a subproject

Subprojects organize their internal work in one of two ways. The choice depends on
the dependency shape of the work, not on personal preference.

**STEP pattern** — use when the work is a strict linear pipeline. `STEP_N+1` has
no meaning without `STEP_N` having run first. The user always runs them in order,
end to end.

- Examples: `genomesDB` (STEP_0 prepare proteomes [optional, evigene T1 extraction]
  → STEP_1 sources → STEP_2 standardize → STEP_3 databases
  → STEP_4 final species set), `trees_gene_families` (STEP_1 homolog discovery
  → STEP_2 phylogenetic analysis)
- Naming: `STEP_N-short_descriptor/`

**BLOCK pattern** — use when the work is a set of modular units with a dependency
graph (not a chain). User may choose which blocks to run. Dependencies are
expressed through each block's `output_to_input/` consumption, and documented in
the subproject's README and AI_GUIDE.

- Examples: `orthogroups` (BLOCK_orthohmm, BLOCK_orthofinder, BLOCK_broccoli are
  alternatives; BLOCK_comparison depends on whichever were run),
  `annotations_hmms` (one BLOCK per annotation tool), `trees_species`
  (BLOCK_gigantic_species_tree, BLOCK_permutations_and_features)
- Naming: `BLOCK_short_descriptor/`

**Distinguishing test:** if `X_2` and `X_3` both depend on `X_1` but NOT on each
other, that's a dependency TREE — use BLOCK. If `X_2` strictly follows from
`X_1` with no alternative path, that's a CHAIN — use STEP.

**Cross-subproject integration work** (e.g., a step that combines outputs from
multiple unrelated subprojects) belongs in its own subproject, NOT nested as a
BLOCK/STEP inside a data-producer subproject. This keeps each subproject's
scope coherent — a subproject produces ONE kind of thing; integrations across
kinds live at the peer subproject level.

---

### Project INPUT_user → Workflow INPUT_user Flow

```
INPUT_user/                              # User places species list + genomic files HERE
├── species_set/
│   └── species_list.txt                 # Project-wide DEFAULT species list
└── genomic_resources/
    ├── genomes/                         # Genome assembly .fasta files
    ├── proteomes/                       # Proteome .aa files
    ├── annotations/                     # GFF3/GTF annotation files
    └── maps/                            # Identifier mapping .tsv files

Species list resolution (by RUN-workflow.sh):
  1. workflow-*/INPUT_user/species_list.txt   ← checked FIRST (user override)
  2. INPUT_user/species_set/species_list.txt  ← used as DEFAULT (copied to workflow)
```

**Why**: One place for all user-provided genomic resources, organized by type. The species list uses an override pattern: the project-level list is the default, but any workflow can override it with its own list. Each workflow run ends up with a copy in its INPUT_user/ for archival. Genomic files are referenced by manifests in workflow-level INPUT_user directories.

### Core Design Principle: Scripts Own the Data, NextFlow Manages Execution

**GIGANTIC is a scientific research platform, not a software application.** This fundamental distinction drives a non-negotiable design principle:

**Every script reads its inputs from `OUTPUT_pipeline/N-output/` and writes its outputs to `OUTPUT_pipeline/N-output/`.** NextFlow orchestrates the execution ORDER of scripts but does NOT silently transfer data between them through internal channels. All intermediate results must be recorded in `OUTPUT_pipeline/N-output/` where they are:

- **Inspectable**: A researcher can examine any step's output directly
- **Verifiable**: Results can be validated independently at each stage
- **Reproducible**: Another researcher (or your future self) can see exactly what happened
- **Debuggable**: When something goes wrong, you can trace the data step by step

**NextFlow's role in GIGANTIC**: NextFlow is an execution manager, not a data broker. It determines WHEN scripts run (dependency ordering, parallelization, retry logic). It does NOT determine WHERE data lives. Scripts handle their own I/O through the transparent `OUTPUT_pipeline/N-output/` directory structure.

**Why this matters**: In scientific computing, "trust me, the intermediate data is somewhere in a hashed work directory" is not acceptable. Every intermediate result is part of the scientific record. Completing a pipeline with invisible intermediate data is worse than failing - it produces results that cannot be independently verified. This principle applies even when transparent data handling costs additional disk space.

**Contrast with application development**: Software applications optimize for efficiency and can use opaque internal data channels because the end product (a working app) is what matters. In research, the process IS the product - understanding how results were derived is as important as the results themselves.

### Pipeline Output Lifecycle: work/ → OUTPUT_pipeline/ → output_to_input/

GIGANTIC workflows follow a three-stage data lifecycle:

```
1. Nextflow runs scripts in work/         # Cryptic hashed directories (for caching)
       ↓ (publishDir)
2. OUTPUT_pipeline/N-output/              # Human-readable, numbered by script
       ↓ (RUN-workflow.sh creates symlinks)
3. output_to_input/                       # Downstream subprojects read from here
```

**Stage 1**: Nextflow executes scripts in `work/` using hashed subdirectory names. Not human-navigable.

**Stage 2**: Each script's outputs are copied via `publishDir` to `OUTPUT_pipeline/N-output/` (where N matches the script number: 001 → `1-output/`). This is where users browse results. **This is the authoritative location for all intermediate and final results.**

**Stage 3**: After the pipeline completes, `RUN-workflow.sh` creates symlinks in the subproject's single `output_to_input/` directory:
- **Subproject root** `output_to_input/BLOCK_X/` or `output_to_input/STEP_X-name/` → downstream subprojects read from here
- Each BLOCK or STEP gets its own subdirectory under `output_to_input/`
- The latest workflow run "wins" the slot (overwrites existing symlinks)

**Disk efficiency**: Data files exist only in `OUTPUT_pipeline/`. Symlinks add zero disk usage. The `RUN-clean_and_record_subproject.sh` script removes `work/`, `.nextflow/`, and `.nextflow.log*` after successful runs to reclaim temporary disk space while preserving all outputs and symlinks.

### output_to_input Pattern

Each subproject has exactly **one** `output_to_input/` directory at its root. Inside are subdirectories for each BLOCK or STEP:

```
# BLOCK-based subproject (e.g., orthogroups):
subprojects/orthogroups/
├── BLOCK_orthofinder/workflow-RUN_01-*/OUTPUT_pipeline/3-output/results.tsv  # ACTUAL FILE
│       ↓ (symlinked by RUN-workflow.sh)
└── output_to_input/BLOCK_orthofinder/results.tsv                             # SYMLINK

# STEP-based subproject (e.g., genomesDB):
subprojects/genomesDB/
├── STEP_2-standardize_and_evaluate/workflow-RUN_01-*/OUTPUT_pipeline/...     # ACTUAL FILE
│       ↓ (symlinked by RUN-workflow.sh)
└── output_to_input/STEP_2-standardize_and_evaluate/speciesN_proteomes/      # SYMLINK

# Flat subproject (e.g., phylonames):
subprojects/phylonames/
├── workflow-RUN_01-*/OUTPUT_pipeline/3-output/map.tsv                        # ACTUAL FILE
│       ↓ (symlinked by RUN-workflow.sh)
└── output_to_input/maps/map.tsv                                              # SYMLINK
```

**Key principles**:
- One `output_to_input/` per subproject (never inside BLOCK or STEP directories)
- BLOCK/STEP subdirectories organize outputs by source
- Latest workflow run overwrites existing symlinks (latest run "wins")
- No archival copies at the workflow level -- provenance is tracked by which RUN directory the symlinks point to
- `.gitignore` files in each BLOCK/STEP subdirectory track empty directories in version control

**Why**: Single source of truth, no data duplication, clear provenance, minimal disk footprint.

### upload_to_server Pattern

```
upload_to_server/upload_manifest.tsv  # User edits to select what to share
        ↓ (RUN-update_upload_to_server.sh)
upload_to_server/[symlinks]           # GIGANTIC server scans these
```

**Why**: User controls sharing; manifest documents decisions.

### RUN File Convention

Every workflow has exactly two runner files with standardized names:

| File | Command | Use When |
|------|---------|----------|
| `RUN-workflow.sh` | `bash RUN-workflow.sh` | Local machine, workstation |
| `RUN-workflow.sbatch` | `sbatch RUN-workflow.sbatch` | SLURM cluster (edit account/qos first) |

The workflow directory name provides context (e.g., `workflow-COPYME-generate_phylonames/RUN-workflow.sh`). The RUN files themselves are always named `RUN-workflow.*` for consistency across all subprojects.

**Conda lifecycle**: All environment activation and deactivation is handled within `RUN-workflow.sh`. The `.sbatch` file is a thin wrapper (~25 lines) containing only SLURM resource directives and `bash RUN-workflow.sh` - it never manages conda.

**SLURM resource allocation**: HiPerGator allocates 7.5 GB RAM per CPU. All `.sbatch` files follow the rule `--mem = --cpus-per-task × 7.5 GB`. Under-allocating resources (e.g., 2 CPUs / 8 GB) can cause NextFlow to hang indefinitely during JVM startup on compute nodes, even though the same workflow runs fine locally. If a SLURM job appears stuck at "Running NextFlow pipeline..." with no processes starting, the most likely cause is insufficient resource allocation. Increase CPUs and memory before investigating other causes. On other HPC systems, check your cluster's RAM-per-CPU ratio and adjust accordingly.

### Long-Running Jobs

Some GIGANTIC workflows run for days or even weeks (e.g., OrthoFinder on large species sets, IQ-TREE phylogenetics). How to handle this depends on how you're running the workflow:

| Execution Method | Duration Safety | What Happens if You Disconnect |
|------------------|----------------|-------------------------------|
| `sbatch RUN-workflow.sbatch` | Safe - SLURM manages the job | Job keeps running. Reconnect anytime. |
| `bash RUN-workflow.sh` via SSH | **Dangerous** - process tied to SSH session | Job is killed when SSH drops |
| `bash RUN-workflow.sh` on local machine | Process tied to terminal | Job is killed if terminal closes |

**For SLURM clusters (recommended for long jobs):**

Use `sbatch` - this is the safest option. Once submitted, the job is managed entirely by the SLURM scheduler. You can close your laptop, disconnect from SSH, or log out. The job continues running. Check on it later with `squeue -u $USER` or `sacct`.

**For non-SLURM remote servers (SSH):**

Use `screen` or `tmux` to create a persistent terminal session that survives SSH disconnections:

```bash
# Start a screen session
screen -S my_workflow

# Run the workflow inside screen
cd workflow-RUN_01-generate_phylonames/
bash RUN-workflow.sh

# Detach from screen (workflow keeps running): Ctrl+A then D
# Reconnect later:
screen -r my_workflow
```

**For local machines:**

Long-running workflows are rare on local machines, but if needed, use `screen` or `tmux` as described above to protect against accidental terminal closure.

**Nextflow's `-resume` as a safety net:**

If a workflow is interrupted for any reason, Nextflow can pick up where it left off:

```bash
cd workflow-RUN_01-generate_phylonames/
# Re-run with -resume flag - completed steps are cached and skipped
nextflow run ai/main.nf -resume
```

This works because Nextflow caches completed process outputs in the `work/` directory. Only incomplete or failed steps are re-executed. Note: this must be run from the workflow directory, not through `RUN-workflow.sh` (which runs fresh by default).

### Workflow Naming Convention (COPYME/RUN)

GIGANTIC uses a **COPYME/RUN naming system** for workflows:

| Type | Naming Pattern | Description |
|------|----------------|-------------|
| **COPYME** (template) | `workflow-COPYME-[name]` | The template workflow. NOT numbered. Only ONE COPYME per workflow type. |
| **RUN** (instance) | `workflow-RUN_XX-[name]` | Numbered copies for actual runs. Each run gets its own directory. |

**Examples:**
```
workflow-COPYME-generate_phylonames    # Template (this is what you copy)
workflow-RUN_01-generate_phylonames    # First run instance
workflow-RUN_02-generate_phylonames    # Second run instance
```

**To create a new run:**
```bash
# From the subproject directory
cp -r workflow-COPYME-[name] workflow-RUN_01-[name]
cd workflow-RUN_01-[name]
# Edit config, add inputs, then run
```

**Key Principles:**
- COPYME stays clean as the template - never run workflows directly in COPYME
- All actual work happens in RUN_XX directories
- Increment the number (RUN_01, RUN_02, ...) for each new run
- Each RUN directory preserves its own inputs and outputs for reproducibility

### Graceful Species Dropping (Data Availability Pattern)

Some subprojects require per-species input data that may not be available for all species
in the GIGANTIC set (e.g., gene annotations, transcriptomes, experimental data). For these
subprojects, GIGANTIC uses a **three-tier species processing status** instead of fail-hard:

| Status | Meaning |
|--------|---------|
| **PROCESSED** | Species has valid input data and was fully processed |
| **SKIPPED_NO_DATA** | No input file provided by user (expected for many species) |
| **SKIPPED_INCOMPLETE** | File exists but data failed validation |

**Why not fail-hard?** Missing per-species data is a **data availability limitation**, not a
pipeline error. Not all species have published gene annotations, transcriptomes, or other
specialized data types. The pipeline processes what it can and clearly reports what was
skipped and why.

**When to use this pattern**:
- Subproject inputs depend on external data availability (not all species have it)
- User provides per-species files and some species genuinely lack source data
- Skipping a species does not invalidate the analysis for other species

**When NOT to use this pattern** (use fail-hard instead):
- Core pipeline data (proteomes, species lists) - these MUST be present
- Intermediate pipeline outputs - if Script 002 fails, Script 003 should not run
- Data that should always exist if upstream subprojects completed successfully

**Implementation pattern**:
1. Script 001 validates all species and classifies each as PROCESSED/SKIPPED_NO_DATA/SKIPPED_INCOMPLETE
2. Produces a `species_processing_status.tsv` documenting every species and its status
3. Downstream scripts only process PROCESSED species
4. Final summary includes the processing status for transparency

**Current subprojects using this pattern**: gene_sizes

### Subproject Internal Organization: STEPs and BLOCKs

Subprojects organize their internal workflow directories using two patterns:

| Pattern | Format | Relationship | Example |
|---------|--------|-------------|---------|
| **STEP** | `STEP_N-name/` | Sequential (N depends on N-1) | `STEP_1-sources/ → STEP_2-standardize/ → STEP_3-databases/` |
| **BLOCK** | `BLOCK_name/` | Standalone (run independently) | `BLOCK_orthofinder/`, `BLOCK_orthohmm/`, `BLOCK_broccoli/` |

**STEPs** are sequential: each step depends on the output of the previous step. Used when there is a linear pipeline (e.g., genomesDB: ingest → standardize → build databases → finalize species set). Each STEP contains its own `workflow-COPYME-*/` workflow.

**BLOCKs** are standalone: each block can run independently and in parallel. Used when multiple equivalent analyses operate on the same input (e.g., orthogroups: three tools all run on the same proteomes). Each BLOCK contains its own `workflow-COPYME-*/` workflow.

Both STEPs and BLOCKs follow the same internal structure: `workflow-COPYME-*/`, `AI_GUIDE-*.md`, `README.md`. Their outputs are shared via the subproject-root `output_to_input/` directory (not within each BLOCK/STEP). See the "output_to_input Pattern" section above.

**Subprojects using STEPs**: genomesDB, trees_gene_families, trees_gene_groups
**Subprojects using BLOCKs**: orthogroups, trees_species, annotations_hmms, gene_sizes

### Session Provenance Recording (AI-Native Feature)

GIGANTIC automatically extracts Claude Code session summaries for research documentation:

```bash
# Project level: Record all sessions (project + subprojects + workflows)
bash RUN-record_project.sh

# Subproject level: Cleanup with optional session recording
bash RUN-clean_and_record_subproject.sh --record-sessions
bash RUN-clean_and_record_subproject.sh --all  # cleanup + recording
```

**Output location**:
```
research_notebook/research_ai/
└── sessions/                        # Single flat directory (project-wide)
    ├── session_*.md                 # Extracted compaction summaries
    └── SESSION_EXTRACTION_LOG.md    # Activity log
```

**Workflow-level logs** (run logs, validation) are separate and live inside each workflow's `ai/` directory:
```
workflow-COPYME-*/ai/logs/           # Timestamped run logs
workflow-COPYME-*/ai/validation/     # Validation outputs
```

**Why This Matters**:
- Scientific research requires complete provenance
- AI sessions are treated as first-class research artifacts
- Enables reproducibility and transparency in AI-assisted research
- Safe to run multiple times (overwrites with complete current state)

---

## ⚠️ CRITICAL: Data Flow Contract

Three rules govern where scripts may read data from. Violating them couples
subprojects to each other's internal layouts and breaks GIGANTIC's
composability + reproducibility guarantees.

**Rule 1 — Inter-subproject / inter-workflow:** Always through
`output_to_input/` of the producing subproject. Never reach into another
workflow's `OUTPUT_pipeline/` directly. The `output_to_input/` directory is
the published, version-stable interface — what's behind those symlinks is
the producing subproject's private business and may change.

**Rule 2 — Intra-workflow:** Scripts in the same workflow may read each
other's `OUTPUT_pipeline/N-output/` outputs. These are durable, named,
traceable artifacts.

**Rule 3 — Never read NextFlow's `work/`:** It is ephemeral cache, cleaned
between runs, and lacks the explicit traceability GIGANTIC requires for
research transparency. Pass data between scripts via `OUTPUT_pipeline/`,
not via NextFlow channels reading from `work/`.

### Publishing Responsibility

When a workflow finishes, its `RUN-workflow.sh` is responsible for
**publishing** selected `OUTPUT_pipeline/` artifacts into the subproject's
`output_to_input/` (typically as relative-path symlinks). Downstream
consumers see only `output_to_input/`; the layout of `OUTPUT_pipeline/`
is the producing workflow's internal business.

### Quick Diagram

```
producing_subproject/
├── BLOCK_X/workflow-RUN_NN/
│   └── OUTPUT_pipeline/           # internal — DO NOT read across subprojects
│       └── N-output/file.tsv
└── output_to_input/               # published interface — read across subprojects
    └── BLOCK_X/                   # symlinks → ../../BLOCK_X/workflow-RUN_NN/OUTPUT_pipeline/N-output/file.tsv

consuming_subproject/
└── workflow-RUN_NN/
    └── ai/scripts/001_*.py        # reads via config: producing_subproject/output_to_input/BLOCK_X/...
                                   # NOT: producing_subproject/BLOCK_X/workflow-RUN_NN/OUTPUT_pipeline/...
```

---

## Subproject Dependency Chain

### Core Pipeline

```
[1] phylonames                 # MUST RUN FIRST - generates species identifiers
       │
       ▼
[2] genomesDB ─────────────────┐
       │    (uses phylonames   │
       │     for file naming)  │
       ▼                       │
[3] trees_species ─────────────┤
       │                       │
       ├───────────┬───────────┤
       │           │           │
       ▼           ▼           │
[4] orthogroups  [5] annotations_hmms
       │           │           │
       ▼           │           │
[6] orthogroups_X_ocl ◄────────┘
       │
       ▼
[7] annotations_X_ocl
```

### Additional Subprojects

These subprojects connect to the core pipeline at various points:

```
genomesDB ──► trees_gene_families    # Gene family homolog discovery and phylogenetics
genomesDB ──► trees_gene_groups      # Orthogroup-based phylogenetics
genomesDB ──► gene_sizes             # Gene structure metrics and size analysis
gene_sizes + orthogroups ──► gene_sizes_X_integrations  # dN/dS, rank deviation, enrichment
genomesDB ──► synteny                # Gene order conservation analysis
genomesDB ──► dark_proteome          # Uncharacterized protein analysis
genomesDB ──► one_direction_homologs # One-way BLAST homolog identification
genomesDB ──► xenologs_vs_artifacts  # Xenolog detection and artifact filtering
genomesDB ──► transcriptomes         # Transcriptome integration
genomesDB ──► rnaseq_integration     # RNA-seq expression data integration
genomesDB ──► gene_names             # Comprehensive gene naming
genomesDB ──► hgnc_automation        # Automated reference gene set generation
genomesDB ──► hot_spots              # Evolutionary hotspot analysis
```

### Complete Subproject Reference

| Subproject | Prerequisites | Purpose | Status |
|------------|---------------|---------|--------|
| phylonames | None | Species name mappings from NCBI taxonomy | Operational |
| genomesDB | phylonames | Proteome databases and BLAST setup | Operational |
| orthogroups | genomesDB | Ortholog group identification (uses BLOCKs: orthofinder, orthohmm, broccoli, comparison) | Functional |
| trees_gene_families | genomesDB | Gene family homolog discovery and phylogenetics | Functional |
| trees_gene_groups | genomesDB | Orthogroup-based phylogenetics | Structural |
| trees_species | phylonames | Species tree topology permutations and phylogenetic features (uses BLOCKs: permutations_and_features, de_novo_species_tree) | Functional |
| annotations_hmms | genomesDB | Functional protein annotation | Planned |
| orthogroups_X_ocl | orthogroups + trees_species | Origin-Conservation-Loss analysis | Planned |
| annotations_X_ocl | annotations_hmms + orthogroups_X_ocl | Annotation-OCL integration | Planned |
| gene_sizes | genomesDB | Gene structure size analysis (user-provided CDS intervals) | Functional |
| gene_sizes_X_integrations | gene_sizes + orthogroups | dN/dS, rank deviation, functional enrichment by gene size | Planned |
| synteny | genomesDB | Gene order conservation analysis | Planned |
| dark_proteome | genomesDB | Uncharacterized protein analysis | Planned |
| hot_spots | genomesDB | Evolutionary hotspot analysis | Planned |
| one_direction_homologs | genomesDB | One-way DIAMOND homolog identification against NCBI nr | Structural |
| xenologs_vs_artifacts | genomesDB | Xenolog detection and artifact filtering | Planned |
| transcriptomes | genomesDB | Transcriptome integration | Planned |
| rnaseq_integration | genomesDB | RNA-seq expression data integration | Planned |
| gene_names | genomesDB | Comprehensive gene naming | Planned |
| hgnc_automation | genomesDB | Automated reference gene set generation | Planned |

---

## Phyloname Formats (Critical Concept)

GIGANTIC uses standardized species identifiers throughout:

| Format | Structure | Example | Use |
|--------|-----------|---------|-----|
| `phyloname` | `Kingdom_Phylum_Class_Order_Family_Genus_species` | `Metazoa_Chordata_Mammalia_Primates_Hominidae_Homo_sapiens` | Data tables, analysis |
| `phyloname_taxonid` | Same + `___taxonID` | `..._Homo_sapiens___9606` | File naming (unique) |

**To extract genus_species from phyloname**:
```python
parts = phyloname.split('_')
genus_species = parts[5] + '_' + '_'.join(parts[6:])
```

---

## How to Help Users

### Step 1: Identify Location

Ask: "What subproject are you working on?" or check their current directory:
```bash
pwd
```

### Step 2: Read Appropriate Guide

- **Project-level issues**: This file
- **Subproject issues**: `subprojects/[name]/AI_GUIDE-[name].md`
- **Workflow execution**: `ai/AI_GUIDE-*_workflow.md` inside the workflow

### Step 3: Check Configuration

Look at these files:
- `INPUT_user/species_set/species_list.txt` - do they have species listed?
- `START_HERE-user_config.yaml` - is project name set?
- `RUN-*.sbatch` - is account/qos configured? (SLURM only)

### Step 4: Check Logs

If something failed:
```bash
# Check workflow logs
ls OUTPUT_pipeline/

# Check SLURM logs
ls slurm_logs/

# Check NextFlow logs
cat .nextflow.log
```

### Step 5: Guide Step by Step

Users may not be bioinformatics experts. Give specific commands, not general advice.

---

## Common User Questions

**"Where do I start?"**
→ `subprojects/phylonames/`. Run this first.

**"Where do I put my species list?"**
→ `INPUT_user/species_set/species_list.txt` (project-wide default). To override for a specific workflow, place a `species_list.txt` in that workflow's `INPUT_user/` directory.

**"How do I run a workflow?"**
→ `bash RUN-*.sh` (local) or `sbatch RUN-*.sbatch` (SLURM)

**"Where are my results?"**
→ `OUTPUT_pipeline/` in the workflow directory

**"How do other subprojects get my results?"**
→ Via `output_to_input/` symlinks

**"Something failed, what now?"**
→ Check error message, read the workflow's AI_GUIDE, check log files

**"My workflow will run for days - how do I keep it running?"**
→ Use `sbatch` on SLURM (safest). For SSH sessions, use `screen` or `tmux`. See "Long-Running Jobs" above.

---

## CPU and Memory Configuration

Workflows use two fields in `START_HERE-user_config.yaml` to set SLURM resources:
`cpus` and `memory_gb`. The values interact with the cluster's standard RAM-per-CPU
ratio and with the workflow's natural parallelism.

### RAM-per-CPU ratio (cluster-specific)

Each HPC cluster allocates a fixed amount of RAM per requested CPU when you don't
specify `--mem` explicitly. On **HiPerGator** (the reference cluster for GIGANTIC
development), this is **7.5 GB per CPU**. Other clusters may use different ratios
(e.g., 4 GB/CPU). Users on non-HiPerGator systems should confirm their local ratio
and adjust `memory_gb` accordingly.

### CPU strategy for per-task-parallel pipelines

When a pipeline naturally parallelizes across independent tasks (e.g., OCL analysis
across `N` tree structures), the efficient allocation is:

    cpus = N_parallel_tasks + 1   # one CPU per task + one for the NextFlow driver

For example, for OCL on 105 species tree structures:

    cpus: 106
    memory_gb: 795   # 106 × 7.5 GB (HiPerGator ratio) — each parallel task can use up to ~7.5 GB

NextFlow's `local` executor inside the SLURM allocation dispatches up to `cpus`
concurrent tasks; providing memory proportional to CPUs lets each task have
reasonable working memory without one heavy task blocking others.

### Baseline for smaller or mostly-serial pipelines

For pipelines without per-task parallelism (a handful of sequential scripts), start
with:

    cpus: 1
    memory_gb: 8      # roughly HiPerGator's 7.5 GB/CPU baseline, rounded up

Bump `memory_gb` if a specific step loads a large dataset (e.g., loading 170k
orthogroups with full GIGANTIC identifiers can peak at a few GB). For merely
"lightweight" jobs (small TSVs, simple parsing), `memory_gb: 1` is often
sufficient on a single CPU.

### Rules of thumb

| Situation | `cpus` | `memory_gb` |
|-----------|--------|-------------|
| Lightweight single-process (simple TSV parse / copy / rename) | 1 | 1 |
| Typical single-structure pipeline (one config, one output) | 1–3 | 8–24 (~7.5 GB/CPU) |
| Per-task parallel pipeline, `N` tasks | `N + 1` | `(N+1) × 7.5` (HiPerGator) |
| Memory-heavy step dominates (large BLAST DB, FASTA embedding) | per-step tuning | explicitly set in script or nextflow.config |

### Why match memory to CPUs

If `memory_gb` is much lower than `cpus × 7.5 GB`, individual heavy tasks may hit
memory limits and be killed even though CPUs sit idle. If it's much higher than
needed, the SLURM job consumes a larger share of cluster resources than necessary
(slower scheduling, less fair to other users). Matching the ratio keeps throughput
high and scheduling fair.

---

## Conda Environments

GIGANTIC uses **on-demand** conda environment management. Each subproject's `RUN-workflow.sh` automatically creates its conda environment on first run if it doesn't exist yet.

```bash
# ON-DEMAND (automatic): Just run a workflow - its env is created if missing
cd subprojects/phylonames/.../workflow-RUN_1-generate_phylonames/
bash RUN-workflow.sh  # Creates ai_gigantic_phylonames env if needed

# BULK (optional): Pre-create ALL environments at once
bash RUN-setup_environments.sh
```

**Environment files location**: `conda_environments/ai_gigantic_[subproject].yml`

**Naming convention**: All environments begin with `ai_gigantic_` (e.g., `ai_gigantic_phylonames`)

**NextFlow availability**: Each `RUN-workflow.sh` tries NextFlow from the conda env first. If not available there, it falls back to `module load nextflow` (for HPC systems like HiPerGator). On some HPC systems, NextFlow from conda may not install correctly due to Java conflicts - the module fallback handles this transparently.

**Design rationale**:
- On-demand creation means users only install what they need
- No upfront setup step required - just run a workflow
- `RUN-setup_environments.sh` remains available for bulk creation
- Consistent `ai_gigantic_` naming makes GIGANTIC envs easy to identify in `conda env list`

---

## For AI Assistants: Research Data Protection

**GIGANTIC includes a hook that prevents you from deleting research data.** This is a hard technical guardrail, not a suggestion.

The hook (`.claude/hooks/protect_research_data.sh`) blocks destructive commands (`rm`, `rmdir`, `mv`, `find -delete`) targeting these directories:

- `workflow-RUN_*` - Pipeline run instances with research output
- `OUTPUT_pipeline` - Pipeline output directories
- `output_to_input` - Data shared between subprojects
- `upload_to_server` - Curated data for server sharing
- `research_notebook` - Research documentation and AI sessions
- `gigantic_ai` - AI workspace resources

**If a user asks you to delete something in a protected directory**: Tell the user that the hook prevents this and they should delete it manually outside of Claude Code if they truly want it gone.

**If you think something in a protected directory should be deleted**: Ask the user. Do not attempt to work around the hook. The hook exists because an AI assistant destroyed pipeline output data that took hours to generate and could not be recovered from version control. This is not a theoretical risk - it happened.

**General rule**: Never take destructive actions on research data without explicit user instruction. When in doubt, ask.

---

## For AI Assistants: Honesty About Mistakes

**Do not whitewash mistakes.**

When you make an error:
- Say "I was **incorrect**" or "I was **wrong**" - not "that was confusing"
- Acknowledge the actual mistake clearly
- Correct it without minimizing language

This builds trust with users who rely on accurate information.
