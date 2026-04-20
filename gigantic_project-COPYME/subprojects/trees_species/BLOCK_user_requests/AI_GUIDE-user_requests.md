# AI Guide: BLOCK_user_requests

**AI**: Claude Code | Opus 4.6 | 2026 April 18
**Human**: Eric Edsinger

**For AI Assistants**: Read `../AI_GUIDE-trees_species.md` first for
trees_species subproject context. This guide covers the user-requests BLOCK.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../AI_GUIDE-project.md` |
| trees_species concepts (structures, clade IDs, blocks) | `../AI_GUIDE-trees_species.md` |
| This BLOCK (select_structures workflow) | This file |

---

## What This BLOCK Does

`BLOCK_user_requests` is a lightweight, user-driven query layer over the 105
species tree structures produced by `BLOCK_permutations_and_features`.
Collaborators often ask questions like:

> "I want the tree where Ctenophora is sister to all other animals and
> Placozoa is sister to the Cnidaria+Bilateria clade."

The `workflow-COPYME-select_structures` in this BLOCK is a thin filter that
takes such topological hypotheses (in YAML form) and returns the matching
structures from the 105 candidates.

### Design principle

Queries are expressed as **phylogenetic block relationships** (per Rule 7)
rather than as full newick patterns. This leverages the GIGANTIC block framework
and keeps the query language tractable for non-expert users.

The two primitives cover most real-world topological hypotheses:

1. **`require_direct_child`**: A specific parent-child relationship must exist
   as a phylogenetic block (e.g., `Metazoa::Ctenophora` direct edge)
2. **`require_sister`**: Two named clades must share the same immediate parent
   (e.g., Cnidaria and Bilateria are sisters)

All conditions in a query are AND-combined.

### Canonical representative (handling implicit "inherit the rest")

Most real-world user requests specify topology at the level of a few contested
clades and implicitly expect everything else to inherit from the user's input
tree. For example, Leonid might ask for "4 trees across Cteno/Porifera basal
and two ParaHoxozoa arrangements" without caring about Ichthyosporea or
Filozoa internals.

Naively, each query matches MANY structures (equivalence classes over the
"don't care" regions). The `canonical_representative` setting picks ONE
representative per query:

```yaml
settings:
  canonical_representative:
    enabled: true
    reference_structure: structure_001   # user's input tree
```

For each query with multiple matches, the tool picks the match that shares
the MOST phylogenetic blocks with the reference structure. Since
`structure_001` is always the user's input tree, this naturally preserves
the user's arrangement in unconstrained regions. Ties broken by lowest
structure_id (for determinism).

Output files when canonical is enabled:
- `1_ai-canonical_structures.tsv` (one row per query)
- `1_ai-canonical_structures/` (newick copies)
- `1_ai-canonical_previews/` (ASCII previews)

The full equivalence-class outputs (`1_ai-matching_structures.tsv`,
`1_ai-selected_structures/`, `1_ai-ascii_previews/`) are still produced so
users can see all equivalent structures if they want.

---

## When to Use This BLOCK

**Good fits:**
- A collaborator describes a species tree topology in natural language and
  you need to map it onto one of the 105 enumerated structures
- You want to filter structures by specific basal-lineage hypotheses (e.g.,
  Ctenophora-sister vs Porifera-sister)
- You want to test specific sister-clade arrangements at contested nodes
- You need to feed a small, hand-picked set of structures into a downstream
  subproject (e.g., annotations_X_ocl run restricted to 4 trees)

**Not a fit:**
- Complex constraints involving branch lengths, bootstrap support, or
  continuous features -- this BLOCK is purely topological
- Cross-structure aggregations (that's STEP_2 `occams_tree` territory)
- Generating new topologies not in the 105 candidates

---

## Directory Structure

```
BLOCK_user_requests/
├── AI_GUIDE-user_requests.md              # THIS FILE
└── workflow-COPYME-select_structures/     # Template (never run directly)
    ├── START_HERE-user_config.yaml        # run_label, paths
    ├── RUN-workflow.sh                    # single entry point
    ├── INPUT_user/
    │   ├── README.md
    │   └── query_manifest.yaml            # USER EDITS THIS
    ├── OUTPUT_pipeline/
    │   └── 1-output/
    │       ├── 1_ai-matching_structures.tsv
    │       ├── 1_ai-query_summary.md
    │       ├── 1_ai-selected_structures/  # newick copies
    │       └── 1_ai-ascii_previews/       # ASCII tree renders
    └── ai/
        └── scripts/
            └── 001_ai-python-select_structures.py
```

---

## Key Concepts

### Bare-name matching

Queries use **bare clade names** (e.g., "Metazoa", "Ctenophora"), not the
atomic `CXXX_Name` identifiers. This matters because the same biological
clade receives different `clade_id_name` values across structures that differ
in their descendant arrangement (per Rule 6 -- clade IDs encode
topologically-structured species sets, not just species content).

If a user writes `require_direct_child: {parent: Metazoa, child: Ctenophora}`,
the tool matches on the text after the `CXXX_` prefix. This finds structures
where ANY `CXXX_Metazoa` has ANY `CYYY_Ctenophora` as a direct child,
regardless of the specific numeric IDs.

### Why phylogenetic blocks (not path-states or newick patterns)?

- **Path-states** are feature-dependent (they require a specific feature to
  be mapped onto the tree). Topology queries are feature-agnostic.
- **Newick patterns** require substring matching of ambiguously-ordered
  children, which gets messy quickly. Blocks are atomic and unordered.
- **Blocks** match the question being asked: "which parent-child edges must
  exist in this structure?" Direct mapping to Rule 7.

### Multi-match structures

Often a topological hypothesis with K specified clades matches MULTIPLE
structures among the 105, because the hypothesis is underdetermined (the
other N-K clades can arrange themselves freely). This is expected behavior
and useful information:
- Each "tree" the user describes maps to an equivalence class of structures
- Downstream analysis can use the whole equivalence class or pick a canonical
  representative

---

## Query Language Reference

### require_direct_child

```yaml
require_direct_child:
  - { parent: Metazoa, child: Ctenophora }
  - { parent: Bilateria, child: Chordata }
```

Each entry asserts: "there exists a phylogenetic block in the structure where
the parent bare name matches and the child bare name matches."

**Why this works for "X is sister to all others":** In a binary tree, a node
has exactly 2 children. If X is a direct child of Metazoa, the sister is
whatever the other Metazoa child is -- which by process of elimination
contains all non-X animals. So `{parent: Metazoa, child: Ctenophora}` is
equivalent to saying "Ctenophora is sister to all other animals."

### require_sister

```yaml
require_sister:
  - [ Cnidaria, Bilateria ]
  - [ Placozoa, Cnidaria ]
```

Each entry is a 2-element list asserting: "these two clades share the same
immediate parent on the species tree."

**Why this works for ParaHoxozoa resolution:** The three clades Placozoa,
Cnidaria, Bilateria have three possible binary arrangements:
- `(Plac, (Cnid, Bil))` -- pinned by `[Cnid, Bil]` sister
- `((Plac, Cnid), Bil)` -- pinned by `[Plac, Cnid]` sister
- `((Plac, Bil), Cnid)` -- pinned by `[Plac, Bil]` sister

A single sister pair is enough to distinguish the three.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| "No combined phylogenetic blocks file found" | trees_species not run | Run `BLOCK_permutations_and_features` first |
| "Query manifest not found" | INPUT_user/query_manifest.yaml missing | Copy from COPYME template and edit |
| "0 structures match" for a specific query | Query too strict, bad clade name, or hypothesis not in enumerated 105 | Check ASCII preview of structure_001 to verify clade names; look for typos (e.g., "Placozoan" vs "Placozoa") |
| Same structure matches multiple queries | Queries are too loose (not mutually exclusive) | Add constraints to narrow each query |

---

## Questions to Ask Users

| Situation | Ask |
|-----------|-----|
| User describes a tree in natural language | "Can you list each direct parent-child relationship at the clades you care about?" |
| User names clades that might not appear | "How is this clade named in your reference tree? (e.g., Ctenophora vs Ctenophore)" |
| Query returns too many matches | "Do you want ONE canonical representative per query (e.g., lowest-numbered structure_id)? Or all equivalent structures?" |
| Query returns zero matches | "Let me show you structure_001 (your input tree) -- does the named clade appear?" |

---

## Potential Future Extensions

Scoped to trees_species for now (per Eric's guidance 2026-04-18), but worth
noting as future possibilities:

- **Additional operators**: `require_ancestor(A, descendant_of_B)`,
  `forbid_direct_child(parent, child)`, `require_clade_count(name, n)`.
- **Full-tree pattern matching** using external libraries (ete3, dendropy).
  Useful if query complexity outgrows block primitives.
- **Generalization**: if this pattern proves useful beyond topology queries,
  it could expand into a general "user-filtered subset" BLOCK for other
  subprojects (e.g., annotations by specific Pfam accessions, orthogroups by
  gene family).
- **Interactive query builder**: a lightweight form (maybe integrated with
  the coming "data diver") that helps non-expert users express topological
  hypotheses without writing YAML by hand.
