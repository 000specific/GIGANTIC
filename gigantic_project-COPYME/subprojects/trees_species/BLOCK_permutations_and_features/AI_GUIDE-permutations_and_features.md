# AI Guide: BLOCK_permutations_and_features

**AI**: Claude Code | Opus 4.6 | 2026 March 04
**Human**: Eric Edsinger

**For AI Assistants**: Read `../AI_GUIDE-trees_species.md` first for subproject concepts.
This guide covers the permutations_and_features block specifically.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../AI_GUIDE-project.md` |
| trees_species concepts | `../AI_GUIDE-trees_species.md` |
| BLOCK overview | This file |
| Running the workflow | `workflow-COPYME-permutations_and_features/ai/AI_GUIDE-permutations_and_features_workflow.md` |

---

## What This Block Does

Takes a user-provided annotated species tree (Newick format with CXXX_Name labels) and
generates all possible topology permutations for user-specified unresolved clades.
For each topology, extracts comprehensive phylogenetic features: paths, blocks,
parent-child relationships, clade-species mappings, and species tree visualizations.

(See `../README.md` Terminology section for canonical definitions of structure,
topology, resolved vs unresolved input species tree, and species-tree-vs-gene-tree
explicitness.)

Key capabilities:
- **Topology permutations**: (2N-3)!! unrooted topologies for N unresolved clades
  (e.g., 5 clades = 105 topologies, 0 clades = single species tree mode)
- **Clade identifier system**: Persistent CXXX identifiers across all structures
- **Phylogenetic blocks**: Parent::Child branch identifiers with synthetic C000_Pre_Basal root
- **Comprehensive integration**: 24-column master table with all clade data
- **Species-set agnostic**: Works with any species set (configured via species_set_name)

---

## Directory Structure

```
BLOCK_permutations_and_features/
├── AI_GUIDE-permutations_and_features.md    # THIS FILE
└── workflow-COPYME-permutations_and_features/
    ├── README.md
    ├── RUN-workflow.sh
    ├── RUN-workflow.sbatch
    ├── START_HERE-user_config.yaml
    ├── INPUT_user/                          # species_tree.newick (+ optional clade_names.tsv)
    ├── OUTPUT_pipeline/
    └── ai/
        ├── main.nf
        ├── nextflow.config
        ├── AI_GUIDE-permutations_and_features_workflow.md
        └── scripts/                         # 9 sequential Python scripts
```

---

## Pipeline Summary

| Script | Purpose | Key Input | Key Output |
|--------|---------|-----------|------------|
| 001 | Extract species tree components | species_tree.newick | Clade registry, paths, metadata |
| 002 | Generate topology permutations | Metadata (unresolved clades) | Permutation Newick strings |
| 003 | Assign clade identifiers | Topology permutations | Annotated skeletons with CXXX IDs |
| 004 | Build complete species trees | Skeletons + original species tree | Complete species trees, clade registry |
| 005 | Extract parent-child relationships | Complete trees | Parent-sibling (9-col) + parent-child (4-col) |
| 006 | Generate phylogenetic blocks | Parent-sibling tables | Phylogenetic blocks (Parent::Child) |
| 007 | Integrate all clade data | Registry, trees, blocks | 24-column master clade table |
| 008 | Visualize species trees | Complete Newick trees | SVG + PDF per structure |
| 009 | Generate clade-species mappings | Integrated data, blocks | Clade-to-descendant-species table |

---

## Key Concepts

### Clade Identifiers — Topologically-Structured Species Sets

Clade IDs produced by this BLOCK identify **topologically-structured species
sets** — a combination of (1) a specific set of descendant species and
(2) the topological arrangement of those species in the subtree. Two clades
across different structures are the SAME clade (same `clade_id_name`, e.g.,
`C082_Metazoa`) if and only if BOTH match.

**Assignment policy (script 003):**
- Format: `CXXX` (e.g., C001, C068, C079), combined with a human-readable
  name into `clade_id_name` like `C082_Metazoa` as the canonical atomic
  identifier
- Species retain their original IDs across all structures
- Internal nodes of `structure_001` (user's input species tree) retain
  original IDs
- For `structure_002` onward: each internal node's **canonical
  topological signature** (alphabetically-sorted Newick of its species
  subset, using unresolved clade names as leaves) is computed; if the
  signature matches a clade already registered in an earlier structure,
  that clade's existing ID is **reused**. If the signature is new, a new
  `C{next}` ID is minted.
- Result: the same biological clade (same species + same arrangement) has
  the same `clade_id_name` across every structure it appears in. The
  registry's `appears_in_structures` column tracks which candidate
  structures each clade belongs to.

**Cross-structure use**: downstream subprojects (e.g., `orthogroups_X_ocl`
and the planned `occams_tree`) can treat `clade_id_name` as a globally
stable key for a biological clade. No structure-prefixed composite
identifier is needed.

**Auto-naming**: ambiguous-zone internal clades with no literature name
get placeholder names like `Clade_069`. The `clade_id` is the semantic
identifier; the name is a display label. Users may rename later if
desired; the pipeline does not depend on name uniqueness beyond the
`clade_id_name` composite.

**Sibling-order invariance (applies at arbitrary depth)**:
In phylogenetic trees, `(species_A, species_B)` and `(species_B, species_A)`
represent the same topological grouping — sibling order in a Newick string
is a representational detail, not biology. The canonical signature
computation (`get_canonical_structure()` in script 003) enforces this
invariance by alphabetically sorting children's signatures before joining
them, **at every recursion level**. So the invariance holds for arbitrarily
deep nesting:

- `((A,B),C)`, `((B,A),C)`, `(C,(A,B))` all → `((A,B),C)` (same canonical)
- `(((A,B),C),D)`, `(D, (C, (A,B)))`, `(D, ((B,A), C))` all → `(((A,B),C),D)`

All receive the same `clade_id_name`. In contrast, `((A,C),B)` maps to
`((A,C),B)` — correctly different, because A+C is a different biological
grouping than A+B.

**Scope — rooted trees only**:
This canonicalization applies to ROOTED trees, which is exactly what this
BLOCK produces (every structure has an explicit root/basal node). For
rooted trees, `(A, (B,C))` and `((A,B), C)` encode different biological
groupings and correctly receive different canonical signatures. Unrooted-
tree equivalence (where those two would be considered equivalent) is a
different computation entirely (based on bipartition sets) and out of scope
for GIGANTIC's species tree analyses — species trees here are always
rooted.

The annotated Newick files emitted by this BLOCK preserve input child
order (for readability / debugging), but clade ID assignments are
already made on canonical equality, so downstream pipelines should use
`clade_id_name` as the atomic identifier rather than parse Newick child
order.

For the full canonical definition, see Rule 6 in the project's
`AI_GUIDE-project.md` or the Terminology section of
`../README.md`.

### Phylogenetic Blocks
- Format: `Parent_ID_Name::Child_ID_Name` (e.g., `C068_Basal::C069_Bilateria`)
- Synthetic `C000_Pre_Basal` parent for root nodes
- Each internal node produces exactly 2 blocks (binary tree)

### Single Species Tree Mode
When 0 unresolved clades are specified, the pipeline skips permutation and outputs the
original species tree as structure_001 with all features extracted. (This is the
"resolved input" case — see the canonical Resolved vs Unresolved subsection in
`../README.md`.)

---

## Output to Downstream

This block publishes to `output_to_input/BLOCK_permutations_and_features/` at the subproject root:
- `Species_Tree_Structures/` - Complete Newick species trees per structure
- `Species_Phylogenetic_Paths/` - Root-to-leaf paths per species per structure
- `Species_Parent_Sibling_Sets/` - Parent-sibling tables (9-column)
- `Species_Parent_Child_Relationships/` - Parent-child tables (4-column)
- `Species_Phylogenetic_Blocks/` - Phylogenetic block identifiers
- `Species_Clade_Species_Mappings/` - Clade-to-descendant-species mappings

Downstream subprojects (orthogroups_X_ocl, annotations_X_ocl, origins_conservation_loss)
access these via the subproject-root `output_to_input/` directory.
