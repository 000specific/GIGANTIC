# AI Guide: trees_species Subproject

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March 04 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

**For AI Assistants**: Read `../../AI_GUIDE.md` first for GIGANTIC overview,
directory structure, and general patterns. This guide covers trees_species-specific
concepts and troubleshooting.

---

## Quick Reference

| User needs... | Go to... |
|---|---|
| GIGANTIC overview, directory structure | `../../AI_GUIDE.md` |
| trees_species concepts, troubleshooting | This file |
| BLOCK_gigantic_species_tree (standardize + label) | `BLOCK_gigantic_species_tree/AI_GUIDE.md` |
| BLOCK_permutations_and_features (enumerate + extract features) | `BLOCK_permutations_and_features/AI_GUIDE.md` |
| BLOCK_user_requests (query layer over enumerated structures) | `BLOCK_user_requests/AI_GUIDE.md` |
| BLOCK_de_novo_species_tree (future placeholder) | `BLOCK_de_novo_species_tree/AI_GUIDE.md` |
| Running the gigantic_species_tree workflow | `BLOCK_gigantic_species_tree/workflow-COPYME-gigantic_species_tree/ai/AI_GUIDE.md` |
| Running the permutations workflow | `BLOCK_permutations_and_features/workflow-COPYME-permutations_and_features/ai/AI_GUIDE.md` |
| Running the select_structures workflow | `BLOCK_user_requests/AI_GUIDE.md` |

---

## What This Subproject Does

Processes species phylogenetic trees to extract structured data for downstream
origin-conservation-loss (OCL) analyses. Four BLOCKs:

1. **BLOCK_gigantic_species_tree** (active) - Takes a raw user-provided species tree
   (Newick with `Genus_species` leaves + optional user clade names), validates and
   standardizes it, fills in `ancestral_clade_NNN` names for unlabeled internal nodes,
   assigns `CXXX_` clade identifiers to every node, and emits canonical Newick
   variants + clade map + visualization. Typically the first step for a new species set.
2. **BLOCK_permutations_and_features** (active) - Takes a labeled species tree
   (typically from `BLOCK_gigantic_species_tree`), generates topology permutations for
   unresolved nodes, extracts phylogenetic features. 10 sequential scripts (script
   010 is a per-run audit log).
3. **BLOCK_user_requests** (active) - Lightweight query layer over the
   enumerated structures. User describes topological hypotheses in
   `query_manifest.yaml` and the workflow returns matching structures from
   the candidate set (e.g., 105 for 5 unresolved clades).
4. **BLOCK_de_novo_species_tree** (future — planned, no scaffold yet) — Build species trees from sequence data via BUSCO→MAFFT→ClipKit→IQ-TREE. Only `AI_GUIDE.md` exists currently; scaffold to be created when work begins.

**Typical pipeline order**: `BLOCK_gigantic_species_tree` → `BLOCK_permutations_and_features` → (optional) `BLOCK_user_requests` → downstream OCL subprojects.

---

## Key Concepts

### Phylogenetic vs Evolutionary Terminology

| Term | Refers to | Example |
|------|-----------|---------|
| **Phylogenetic path** | Path on a specific species tree topology (model) | `Homo_sapiens → Primates → ... → Basal` on structure_001 |
| **Evolutionary path** | Actual biological history through time (reality) | All ancestors of Homo sapiens that actually existed |
| **Phylogenetic block** | Parent::Child transition on a species tree (model) | `Cydippida::Pleurobrachia_bachei` |
| **Evolutionary block** | Actual biological divergence event (reality) | The real split that created the Pleurobrachia lineage |

Phylogenetic features are **models** computed from species tree topologies.
Evolutionary features are the **biological reality** being modeled.
Permutation explores alternative models of the same underlying reality.

**Note**: `phylogenetic path` and `phylogenetic block` are atomic terms in
GIGANTIC vocabulary — do not write "phylogenetic species tree path" or
"phylogenetic species tree block." See `README.md` Terminology section for
the full canonical definitions including Structure vs Topology, the
Resolved vs Unresolved input states, and the species-tree-vs-gene-tree
explicitness rule.

### Topology Permutations

When the phylogenetic relationships between certain clades are uncertain (unresolved),
GIGANTIC generates all possible arrangements to test how downstream results (OCL patterns)
vary across alternative topologies.

- User specifies which nodes to permute via config
- Formula: (2N-3)!! unique unrooted topologies for N clades
- Example: 5 clades → 105 topologies
- Zero permutations is valid (single species tree mode — see "Resolved vs Unresolved Input Species Tree" in `README.md`)

### Clade Identifiers — Topologically-Structured Species Sets

Each clade has a permanent identifier `clade_id_name` (e.g., `C082_Metazoa`)
that identifies a **topologically-structured species set**: a specific
combination of (1) descendant species and (2) their branching arrangement.
Two clades across different species tree structures are the SAME clade if
and only if both match. Numerical ranges (illustrative):
- C001 onward: Terminal species in the original tree
- Internal nodes of structure_001 (user's input species tree) retain their
  original IDs
- Novel internal groupings minted during permutation of unresolved clades
  receive new IDs starting after the max existing

The assignment is **biologically content-driven** via canonical topological
signatures (see `BLOCK_permutations_and_features/AI_GUIDE.md`
"Clade Identifiers — Topologically-Structured Species Sets" for mechanism).
If the same ambiguous-zone grouping appears in multiple candidate topologies,
it receives the SAME ID. Named clades outside the unresolved zone (Metazoa,
Bilateria, etc.) have globally stable IDs across all 105 structures.

Downstream consumers (`ocl_phylogenetic_structures/BLOCK_orthogroups_X_ocl/`,
the planned `occams_tree`) use `clade_id_name` as an atomic cross-structure
key — never split into `clade_id` and `clade_name` for lookups.

See `README.md` Terminology section (rule "Clade IDs as Topologically-
Structured Species Sets") and Rule 6 of `../../AI_GUIDE.md` for the
canonical definition.

### Structure Numbering

- **structure_001**: The original input species tree topology (reference)
- **structure_002-105**: Permuted alternative topologies

(See `README.md` Terminology section for the canonical Structure vs Topology
definitions and the Resolved vs Unresolved input species tree distinction.)

---

## Directory Structure

```
trees_species/
├── README.md
├── AI_GUIDE.md              # THIS FILE
├── RUN-update_upload_to_server.sh
│
├── output_to_input/                       # Single canonical downstream location
│   ├── BLOCK_de_novo_species_tree/        # Future
│   ├── BLOCK_gigantic_species_tree/       # Symlinks to labeled species tree + clade map
│   └── BLOCK_permutations_and_features/   # Symlinks to OUTPUT_pipeline data
│       ├── Species_Phylogenetic_Paths/
│       ├── Species_Phylogenetic_Blocks/
│       ├── Species_Parent_Sibling_Sets/
│       ├── Species_Parent_Child_Relationships/
│       ├── Species_Tree_Structures/
│       └── Species_Clade_Species_Mappings/
│
├── upload_to_server/
│   (no per-subproject research_notebook/ — single project-root sandbox at
│   gigantic_project-COPYME/research_notebook/ per §1, §25; chat captures
│   land at research_notebook/research_ai/sessions/ per §9)
│
├── BLOCK_de_novo_species_tree/            # Future — planned, no scaffold yet
│   └── AI_GUIDE.md                        # placeholder doc only
│
├── BLOCK_gigantic_species_tree/           # ACTIVE: standardize + label user-provided species tree
│   ├── AI_GUIDE.md
│   ├── RUN-update_upload_to_server.sh
│   └── workflow-COPYME-gigantic_species_tree/
│       ├── README.md
│       ├── RUN-workflow.sh                  # Unified driver (§29)
│       ├── START_HERE-user_config.yaml
│       ├── INPUT_user/
│       │   ├── README.md
│       │   └── species_tree.newick        # User provides
│       ├── OUTPUT_pipeline/
│       │   ├── 1-output/   # Canonical input tree + name mapping + validation
│       │   ├── 2-output/   # Fully labeled tree (CXXX_Name everywhere)
│       │   ├── 3-output/   # Three Newick variants (simple, full, ids-only)
│       │   ├── 4-output/   # Clade name <-> clade ID lookup TSV
│       │   ├── 5-output/   # Visualization (SVG or soft-fail placeholder)
│       │   └── 6-output/   # Cross-validation report
│       └── ai/
│           ├── AI_GUIDE.md
│           ├── main.nf
│           ├── nextflow.config
│           └── scripts/    # 7 Python scripts (001-007)
│
└── BLOCK_permutations_and_features/
    └── workflow-COPYME-permutations_and_features/
        ├── RUN-workflow.sh                  # Unified driver (§29)
        ├── START_HERE-user_config.yaml
        ├── INPUT_user/
        │   ├── species_tree.newick        # User provides
        │   └── clade_names.tsv            # User provides (optional)
        ├── OUTPUT_pipeline/
        │   ├── 1-output/   # Species tree components
        │   ├── 2-output/   # Topology skeletons
        │   ├── 3-output/   # Annotated topologies with clade IDs
        │   ├── 4-output/   # Complete trees + phylogenetic paths
        │   ├── 5-output/   # Parent-child relationships
        │   ├── 6-output/   # Phylogenetic blocks
        │   ├── 7-output/   # Integrated clade data
        │   ├── 8-output/   # Visualizations (PDF/SVG)
        │   └── 9-output/   # Clade-species mappings
        └── ai/
            ├── main.nf
            ├── nextflow.config
            └── scripts/     # 9 Python scripts (001-009)
```

---

## Pipeline Scripts (BLOCK_permutations_and_features — 10 scripts)

| Script | Purpose | Reads from | Writes to |
|---|---|---|---|
| 001 | Extract species tree components (outgroups, major clades, registry) | INPUT_user/ | 1-output/ |
| 002 | Generate topology permutations | 1-output/ | 2-output/ |
| 003 | Assign clade identifiers to permuted topologies | 1-output/, 2-output/ | 3-output/ |
| 004 | Build complete species trees (graft species onto topologies) | 1-output/, 3-output/ | 4-output/ |
| 005 | Extract parent-child/sibling relationships | 4-output/ | 5-output/ |
| 006 | Generate phylogenetic blocks | 4-output/, 5-output/ | 6-output/ |
| 007 | Integrate all clade data into master table | 2-output/, 4-output/, 6-output/ | 7-output/ |
| 008 | Visualize species trees (PDF/SVG) | 4-output/ | 8-output/ |
| 009 | Generate clade-to-species mappings | 4-output/, 6-output/, 7-output/ | 9-output/ |
| 010 | Per-run audit log | n/a | `ai/logs/run_*.log` |

**Note**: In the current main.nf the workflow runs strictly sequentially (001 → 010); script 008 could be run in parallel after 004 in principle, but the current execution graph keeps everything sequential.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "No clades specified for permutation" | Config has empty `unresolved_clades` list | Add clade names to config, or set `permutation_count: 0` for single-tree mode |
| "Clade not found in tree" | Clade name in config doesn't match tree | Check clade names match exactly (case-sensitive) |
| "ete3 not available" | Missing visualization dependency | Rerun `bash RUN-workflow.sh` in the BLOCK's workflow directory — it auto-creates the per-BLOCK env from `ai/conda_environment.yml` (env names: `aiG-trees_species-gigantic_species_tree`, `aiG-trees_species-permutations_and_features`) |
| "0 structures generated" | Permutation calculation error | Check that unresolved_clades has at least 2 entries |

---

## Key Files

| File | User Edits? | Purpose |
|------|-------------|---------|
| `START_HERE-user_config.yaml` | Yes | Species set name, unresolved clades, paths |
| `INPUT_user/species_tree.newick` | Yes | The input species tree |
| `INPUT_user/clade_names.tsv` | Optional | Custom clade ID → name mapping |
| `RUN-workflow.sh` | No | Workflow launcher; on-demand creates the per-BLOCK conda env from `ai/conda_environment.yml` |
| `ai/conda_environment.yml` | No | Per-BLOCK conda env spec (canonical dependencies for this BLOCK) |
| `ai/main.nf` | No | NextFlow pipeline definition |
| `ai/scripts/*.py` | No | Pipeline scripts |

---

## Questions to Ask User

| Situation | Ask |
|-----------|-----|
| Starting a new analysis | "Which species tree should I use? Do you have a Newick file?" |
| Setting up permutations | "Which nodes/clades should be treated as unresolved?" |
| Results look unexpected | "Is structure_001 the correct reference topology?" |
| Cross-subproject integration | "Have phylonames been generated for this species set?" |

---

## Session hygiene (per §61)

For productive project work:
- **Root every chat session at this named `gigantic_project-*/` directory**.
  Not at `GIGANTIC/` (framework root, reserved for framework dev per §16),
  not at `subprojects/<X>/`, not at a `workflow-COPYME-*/` dir, not at
  any directory deeper than the named project root.
- **One chat session per subproject** you're actively working in — keeps
  context focused and prevents cross-subproject confusion.
- **Continue the same session over many compactions** (lossless per §9)
  until it becomes muddled or slow; then start fresh in a new session,
  same root, same subproject focus.
- **Keep a separate "small questions" session** for one-off questions
  so subproject sessions stay focused.

See `ai/ai_FYIs/gigantic_conventions.md` §61 for the full rationale.
