# ocl_phylogenetic_structures

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 29 (Phase 1 stub)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 29 (OCL fix Commit 10 — §42 + §48 + §51 flesh-out)
Human:   Eric Edsinger
Purpose: Subproject-level README for ocl_phylogenetic_structures — the
         parent that hosts every `_X_ocl` BLOCK whose substrate is a
         species tree STRUCTURE (per Rule 2 + Rule 5). The sibling parent
         z_ocl_taxonomic_hierarchies/ hosts the equivalent BLOCKs whose
         substrate is a taxonomic HIERARCHY (NCBI taxonomy or user-supplied).
Scope:   This README is the user-facing landing page. AI navigation lives
         in AI_GUIDE.md alongside it.
============================================================================ -->

## Where this fits

- Parent project landing: [`../../README.md`](../../README.md)
- Parent project AI guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md) (Rules 1-7)
- This subproject's AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)
- Rule 7 whitepaper (canonical block / block-state vocab):
  [`../../ai/ai_FYIs/ocl_phylogenetic_structures-rule_7_whitepaper.md`](../../ai/ai_FYIs/ocl_phylogenetic_structures-rule_7_whitepaper.md)
- Sandbox sibling (gene-tree-vs-species-tree concordance): [`../z_species_trees_vs_gene_trees/`](../z_species_trees_vs_gene_trees/)
- Sibling parent (taxonomic hierarchy axis): [`../z_ocl_taxonomic_hierarchies/`](../z_ocl_taxonomic_hierarchies/)
- IN: `../trees_species/output_to_input/BLOCK_permutations_and_features/` (species tree STRUCTURES — substrate) + feature-producing subprojects per BLOCK (orthogroups, annotations_hmms, trees_gene_families AGS, trees_gene_groups AGS, hotspots, dark_proteomes, synteny)
- OUT: `output_to_input/<BLOCK>/` consumed by downstream OCL-interpretation work; `upload_to_server/` for the project data server

## Purpose

Origin / Conservation / Loss (OCL) inferences for a feature × species
tree structure pair. Each `BLOCK_<feature>_X_ocl/` consumes one upstream
feature signal (orthogroups, annotation groups, AGS-based gene family /
gene group membership, etc.) and reports, per species tree structure,
where that feature **originated** (its most-recent-common-ancestor
clade), where it **persists** (which descendant clades retain it), and
where it has been **lost** (per the five-state phylogenetic-block-state
vocabulary defined in Rule 7 — A / O / P / L / X).

OCL methodology is feature-agnostic at the workflow level. The same
`workflow-COPYME-ocl_analysis/` template runs inside each BLOCK; the
BLOCK differs only in its upstream feature source and per-BLOCK output
naming.

The sibling subproject `../z_ocl_taxonomic_hierarchies/` performs the
same analysis but against **taxonomic hierarchies** rather than species
tree structures. See **Rule 5** (tree-vs-hierarchy distinction) in
`../../AI_GUIDE.md` for why these are separate parents and not a single
subproject with a substrate switch.

## BLOCK roster

| BLOCK | Status | Feature source | Notes |
|-------|--------|----------------|-------|
| [`BLOCK_orthogroups_X_ocl/`](BLOCK_orthogroups_X_ocl/) | **functional** | `../orthogroups/` (any tool BLOCK: orthohmm, orthofinder, broccoli) | Migrated from the standalone `orthogroups_X_ocl/` subproject during the 2026-05-29 OCL reorg. Per-orthogroup OCL across 105 candidate species70 species tree structures. |
| [`BLOCK_annotations_X_ocl/`](BLOCK_annotations_X_ocl/) | **functional** | `../annotations_hmms/BLOCK_build_annotation_database/` | Migrated from the standalone `annotations_X_ocl/` subproject. Per-annogroup OCL (single / combo / zero subtypes for domain databases; single only for simple databases). |
| [`BLOCK_trees_gene_families_X_ocl/`](BLOCK_trees_gene_families_X_ocl/) | placeholder | `../trees_gene_families/.../STEP_1-homolog_discovery/` AGS | Reads AGS (pre-treebuilding All Gene Set) per hand-curated gene family. Side-steps the gene-tree-vs-species-tree reconciliation problem by operating on the homolog-set level rather than the tree level. |
| [`BLOCK_trees_gene_groups_X_ocl/`](BLOCK_trees_gene_groups_X_ocl/) | placeholder | `../trees_gene_groups/.../STEP_1-homolog_discovery/` AGS | Same AGS-level routing as gene families, but per gene group (HGNC, SNAP family, etc.). |
| [`BLOCK_synteny_X_ocl/`](BLOCK_synteny_X_ocl/) | placeholder | `../z_synteny/` (placeholder upstream) | Future axis: synteny-block conservation/loss across tree structures. |
| [`BLOCK_hotspots_X_ocl/`](BLOCK_hotspots_X_ocl/) | placeholder | `../hotspots/` | Feature definition open per user direction. |
| [`BLOCK_dark_proteomes_X_ocl/`](BLOCK_dark_proteomes_X_ocl/) | placeholder | `../dark_proteomes/` | Feature definition open per user direction. |

Each BLOCK is independently runnable per §41 (BLOCK = parallel /
alternative analyses; no fixed run order between BLOCKs).

## Directory structure

```
ocl_phylogenetic_structures/
├── README.md                                    # THIS FILE
├── AI_GUIDE.md                                  # AI-facing navigation + posture
├── RUN-update_upload_to_server.sh               # subproject-level publisher (§38)
│
├── output_to_input/                             # downstream symlinks, mirrors producer paths (§2)
│   ├── BLOCK_orthogroups_X_ocl/<run_label>/structure_NNN/<file>  (symlinks into BLOCK's OUTPUT_pipeline)
│   ├── BLOCK_annotations_X_ocl/<run_label>/structure_NNN/<file>
│   └── (further BLOCKs as they become functional)
│
├── upload_to_server/                            # subproject-level publishing tree (§38)
│   └── <auto-assembled by RUN-update_upload_to_server.sh from per-workflow upload_manifest.tsv>
│
├── BLOCK_orthogroups_X_ocl/                     # functional
├── BLOCK_annotations_X_ocl/                     # functional
├── BLOCK_trees_gene_families_X_ocl/             # placeholder
├── BLOCK_trees_gene_groups_X_ocl/               # placeholder
├── BLOCK_synteny_X_ocl/                         # placeholder
├── BLOCK_hotspots_X_ocl/                        # placeholder
└── BLOCK_dark_proteomes_X_ocl/                  # placeholder

(NO per-subproject research_notebook/ per §1. Sandbox content for this
 subproject lives at:
   ../../research_notebook/research_ai/subproject-ocl_phylogenetic_structures/
 — see §1 + §50 in `../../ai/ai_FYIs/gigantic_conventions.md`.)
```

## Outputs Shared Downstream (`output_to_input/`)

Per §2, `output_to_input/` mirrors producer paths. Each BLOCK exposes
its run-label-keyed outputs under
`output_to_input/<BLOCK>/<run_label>/structure_NNN/`. Downstream OCL-
interpretation work reads from the appropriate BLOCK subdir.

**Downstream consumers (per §40)**:

- `../z_parsimony_tree_structures/` (Layer 3, set aside) — future
  occams-tree-style structure ranking consumer that scores candidate
  species tree structures by their total OCL-implied losses
- Future cross-BLOCK aggregation work (cross-feature consensus, etc.)

## Sharing Data via the GIGANTIC Server

Per §38, this subproject hosts ONE `upload_to_server/` and ONE
`RUN-update_upload_to_server.sh` driver at the subproject root. Each
BLOCK's `workflow-RUN_*/upload_manifest.tsv` is discovered by the shared
helper and assembled into the upload tree:

```bash
bash RUN-update_upload_to_server.sh           # publish
bash RUN-update_upload_to_server.sh --dry-run # preview
```

The data server reads the assembled symlink tree directly — no copy or
sync step. See `../../server/AI_GUIDE.md` for the full publishing
workflow.

## Why two parents — phylogenetic structures vs taxonomic hierarchies

Per Rule 5 (project `AI_GUIDE.md`):

- **Trees** (species trees) have a **root**. Edges represent INFERRED
  biological relationships. Structures are inferred and replaceable.
- **Hierarchies** (NCBI taxonomy) have an **origin**. Edges represent
  set inclusion (definitional, not inferred). Origin is intrinsic.

These are different KINDS of objects. OCL methodology is the same — count
origins / persistences / losses across edges — but the target object type
differs at the PARENT level, not the BLOCK level. Each parent has the
same BLOCK roster; the substrate differs.

This subproject targets species tree structures. The sibling
`../z_ocl_taxonomic_hierarchies/` (z_ early-development per §49) targets
taxonomic hierarchies.

## See also

- `AI_GUIDE.md` — AI navigation
- `../../ai/ai_FYIs/ocl_phylogenetic_structures-rule_7_whitepaper.md` —
  canonical Rule 7 vocab (phylogenetic blocks, block-states, the
  A/O/P/L/X five-state system)
- `../../ai/ai_FYIs/gigantic_conventions.md` — full convention catalog
- `../../research_notebook/research_ai/HANDOFF-ocl_reorganization-2026may28.md`
  — full design / decision context for the OCL reorganization
