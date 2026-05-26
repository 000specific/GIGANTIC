# AI Guide: BLOCK_gigantic_species_tree (trees_species)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March 04 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

**For AI Assistants**: This guide covers `BLOCK_gigantic_species_tree` within the `trees_species` subproject. For `trees_species` overview and pipeline architecture, see `../AI_GUIDE.md`. For GIGANTIC overview, see `../../../AI_GUIDE.md`.

**Location**: `gigantic_project-COPYME/subprojects/trees_species/BLOCK_gigantic_species_tree/`

## Where this fits

- Parent subproject: [`../AI_GUIDE.md`](../AI_GUIDE.md) — trees_species overview
- Parent project: [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- Sibling BLOCKs: [`../BLOCK_permutations_and_features/`](../BLOCK_permutations_and_features/) (next BLOCK; consumes the labeled tree this BLOCK produces) · [`../BLOCK_user_requests/`](../BLOCK_user_requests/) (query layer) · [`../BLOCK_de_novo_species_tree/`](../BLOCK_de_novo_species_tree/) (future alt input source)
- Workflow to run: [`workflow-COPYME-gigantic_species_tree/README.md`](workflow-COPYME-gigantic_species_tree/README.md)
- Reads from: `workflow-*/INPUT_user/species_tree.newick`

---

## CRITICAL: Surface Discrepancies - No Silent Changes

**The user is managing this project - you must surface discrepancies so the user can make decisions. Silent changes undermine project management.**

- NEVER silently do something different than requested
- NEVER assume you know better and proceed without asking
- ALWAYS stop and explain the discrepancy
- ALWAYS ask for clarification before proceeding

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview, directory structure | `../../../AI_GUIDE.md` |
| trees_species concepts, pipeline architecture | `../AI_GUIDE.md` |
| BLOCK_gigantic_species_tree concepts and troubleshooting (this BLOCK) | This file |
| Running the workflow (step-by-step runbook) | `workflow-COPYME-gigantic_species_tree/ai/AI_GUIDE.md` |
| Canonical Terminology (structure vs topology, resolved vs unresolved, etc.) | `../README.md` (Terminology section) |

---

## Purpose of BLOCK_gigantic_species_tree

`BLOCK_gigantic_species_tree` is a **standardization and labeling BLOCK**. It takes a raw user-provided species tree (Newick format, `Genus_species` at leaves, optional clade names at internals) and produces a fully standardized, labeled, validated species tree in all the canonical GIGANTIC formats.

**What it does**:
1. Validates the input tree (binary, unique names, reserved namespace un-collided, etc.)
2. Standardizes names (replaces invalid characters with underscores, emits a mapping table)
3. Standardizes branch lengths to `1.0` (GIGANTIC convention)
4. Fills in `ancestral_clade_NNN` names for any unlabeled internal nodes
5. Assigns `CXXX_` clade identifiers to every node
6. Emits three Newick format variants (simple, full, ids-only)
7. Generates a clade name ↔ clade ID lookup TSV
8. Renders an SVG visualization (soft-fail on tooling errors)
9. Cross-validates all outputs for consistency

**What it does NOT do**:
- Does not enumerate topology permutations (that's `BLOCK_permutations_and_features`)
- Does not run ancestral state reconstruction or OCL analyses (those are downstream)
- Does not build a species tree from sequence data (that's the future `BLOCK_de_novo_species_tree`)

---

## Position in the trees_species Pipeline

```
User provides initial species tree   OR   BLOCK_de_novo_species_tree (future)
           ↓                                          ↓
                   BLOCK_gigantic_species_tree (THIS BLOCK)
                   ─ validates and parses input
                   ─ standardizes names and branch lengths
                   ─ auto-names unlabeled internals as ancestral_clade_NNN
                   ─ assigns CXXX_ clade identifiers
                   ─ emits canonical Newick formats + clade map + visualization
                                    ↓
                   [fully labeled species tree, ready for downstream]
                                    ↓
                   BLOCK_permutations_and_features (existing)
                   ─ enumerates topology permutations for unresolved clades
                   ─ extracts phylogenetic blocks, paths, parent-child tables
                                    ↓
                    output_to_input/ → consumed by OCL pipelines
```

Most GIGANTIC users with a species set start here. The output of this BLOCK is the canonical labeled species tree that downstream BLOCKs and subprojects consume.

---

## Prerequisites

| Prerequisite | Why | How to verify |
|-------------|-----|---------------|
| Species tree in Newick format | This is the only required input | Check `workflow-RUN_*/INPUT_user/species_tree.newick` exists |
| `Genus_species` at leaves | GIGANTIC convention | See `workflow-COPYME-*/INPUT_user/README.md` for format specification |
| Binary tree (no polytomies) | This BLOCK refuses polytomies | Manually resolve or use `BLOCK_permutations_and_features` for unresolved clades |
| Conda environment | For NextFlow + ete3 visualization | `conda activate aiG-trees_species-gigantic_species_tree` (auto-created on demand by RUN-workflow.sh) |

---

## Key Concepts

### Ancestral Clade Auto-Naming

Unlabeled internal nodes in the input species tree are automatically named
`ancestral_clade_NNN` (where NNN is a 3-digit zero-padded sequential number).
The counter **only increments for unlabeled internals** — user-provided clade names are
kept as-is and do not consume numbers. Numbering follows **breadth-first order from
the root** of the species tree.

**Example**: User provides a species tree with 10 internal nodes, 7 of which are labeled
(`Metazoa`, `Bilateria`, etc.) and 3 of which are unlabeled. Script 002 assigns
`ancestral_clade_001`, `ancestral_clade_002`, `ancestral_clade_003` to the 3 unlabeled
internals in BFS order. The 7 user-labeled internals keep their names.

### Reserved Namespace

The name pattern `ancestral_clade_NNN` (where NNN is a 3-digit number) is **RESERVED**
by this BLOCK. Users cannot provide internal node names matching this pattern —
Script 001 will hard-fail with a collision error. This prevents ambiguity about
which names were user-provided vs auto-assigned.

The check happens **after** name standardization, so a user-provided name like
`"ancestral clade 001"` (with spaces) that standardizes to `ancestral_clade_001`
will also be caught.

### Clade ID Assignment

Every node in the species tree gets a `CXXX_` clade identifier prefix:
- **Leaves**: `C001`, `C002`, ..., `CNN` assigned in depth-first preorder traversal
- **Internal nodes**: `C(N+1)`, ..., `C(N+M)` assigned in breadth-first order from the root

The root of the species tree always gets the first internal ID (e.g., `C071` for a 70-leaf tree).

### Name Standardization

Invalid characters in any user-provided name are replaced with underscores during
Script 001. The allowed character set is `[A-Za-z0-9_]`. A mapping table is always
emitted (even if no changes were made) showing every input name alongside its
standardized form.

**This is a well-defined transformation**:
- Replace any character not in `[A-Za-z0-9_]` with `_`
- Collapse consecutive underscores to a single underscore
- Strip leading/trailing underscores

### Branch Length Standardization (EXCEPTION to "never destroy user data")

All user-provided branch lengths are **replaced with `1.0`** during Script 001.
This is the one place in GIGANTIC where user data is intentionally overwritten.

**Rationale**: GIGANTIC does not use branch lengths in any downstream analysis.
Standardizing here keeps species tree structures consistent across the framework
and prevents downstream consumers from relying on branch lengths that may or may
not be meaningful.

This is documented clearly in the INPUT_user README so users know to save their
original tree elsewhere if they need branch lengths for a different purpose.

### Three Newick Output Formats

| Format | Leaves | Internal nodes | Use case |
|---|---|---|---|
| **simple** | `Genus_species` only | unlabeled | Plain tree for external viewers, human reading, most downstream consumers that don't need clade IDs |
| **full** | `CXXX_Genus_species` | `CXXX_Clade_Name` | Canonical format for most GIGANTIC downstream pipelines; mirrors the species67 leonid-tree convention |
| **ids_only** | `CXXX` | `CXXX` | Compact structural format; requires the clade map TSV to interpret |

All three variants carry the same tree topology. The simple and ids_only variants
are derived from the full variant by stripping different label components.

### Soft-Fail Visualization (THE EXCEPTION to "hard-fail by default")

Script 005 (visualization) uses a soft-fail pattern instead of hard-fail. If ete3
rendering fails (import error, Qt/headless issues, memory problems, etc.), the
script creates a placeholder text file, logs a WARNING, and exits with code 0.
The pipeline continues.

**Rationale**: Visualization is a nice-to-have output. Nothing else in GIGANTIC
depends on the SVG file existing. Making it hard-fail would block the production
of the other (more important) outputs due to a tooling issue that is often
environment-specific.

This soft-fail pattern mirrors `trees_gene_families/.../STEP_2-phylogenetic_analysis/`
visualization scripts which encountered the same ete3/Qt headless issues.

---

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `Input newick file not found` | Missing `INPUT_user/species_tree.newick` | Place your species tree in `INPUT_user/species_tree.newick` |
| `Failed to parse input newick` | Malformed Newick syntax | Check for unmatched parentheses, missing commas, or stray characters |
| `Non-binary internal node` | Tree has polytomies | Resolve polytomies manually, or use `BLOCK_permutations_and_features` |
| `collide with the reserved ancestral_clade_NNN namespace` | User-provided name matches the reserved pattern | Rename the conflicting node(s) in your input tree |
| `Duplicate leaf names` | Two species have the same name (after standardization) | Rename to be distinguishable after underscore substitution |
| `name ... became empty after standardization` | Name contained only invalid characters | Use a name with at least one `[A-Za-z0-9]` character |
| Visualization placeholder instead of SVG | ete3 import failed or Qt headless issues | Not a hard error — check `5-output/5_ai-log-visualize_species_tree.log` for details. SVG can be generated offline if needed. |
| `Clade ID set mismatch` (Script 006) | Bug in Scripts 002/004 | Report — this indicates a framework inconsistency |

---

## Key Files

| File | Purpose | User Edits? |
|------|---------|-------------|
| `workflow-COPYME-*/START_HERE-user_config.yaml` | `species_set_name`, paths | **YES** (required) |
| `workflow-COPYME-*/INPUT_user/species_tree.newick` | Your species tree | **YES** (required) |
| `workflow-COPYME-*/INPUT_user/README.md` | Input format documentation | No |
| `workflow-COPYME-*/RUN-workflow.sh` | Local execution script | No |
| `workflow-COPYME-*/RUN-workflow.sh` | SLURM execution script | **YES** (account/qos) |
| `workflow-COPYME-*/ai/main.nf` | NextFlow pipeline definition | No (AI-generated) |
| `workflow-COPYME-*/ai/nextflow.config` | NextFlow settings | No (unless resource tuning needed) |
| `workflow-COPYME-*/ai/scripts/*.py` | 7 pipeline scripts | No (AI-generated) |
| `RUN-update_upload_to_server.sh` | Manage upload_to_server/ symlinks | No |

---

## Output Files (after a successful run)

Per workflow run copy (`workflow-RUN_N-gigantic_species_tree/`):

```
OUTPUT_pipeline/
├── 1-output/
│   ├── 1_ai-input_species_tree-canonical.newick      # Validated, standardized input
│   ├── 1_ai-input_user_name_X_gigantic_name.tsv       # Name mapping table
│   ├── 1_ai-validation_report.tsv                     # Validation check results
│   └── 1_ai-log-validate_input_species_tree.log       # Script 001 log
│
├── 2-output/
│   ├── 2_ai-species_tree-with_clade_ids_and_names.newick   # Fully labeled tree
│   ├── 2_ai-validation_report.tsv
│   └── 2_ai-log-assign_clade_identifiers.log
│
├── 3-output/
│   ├── 3_ai-{species_set}-species_tree-simple.newick
│   ├── 3_ai-{species_set}-species_tree-with_clade_ids_and_names.newick
│   ├── 3_ai-{species_set}-species_tree-clade_ids_only.newick
│   └── 3_ai-log-write_newick_variants.log
│
├── 4-output/
│   ├── 4_ai-{species_set}-clade_name_X_clade_id.tsv   # Clade map
│   └── 4_ai-log-generate_clade_map.log
│
├── 5-output/
│   ├── 5_ai-{species_set}-species_tree.svg            # OR:
│   ├── 5_ai-visualization-placeholder.txt             # (if ete3 failed)
│   └── 5_ai-log-visualize_species_tree.log
│
└── 6-output/
    ├── 6_ai-validation_report.tsv                     # Cross-validation summary
    └── 6_ai-log-validate_outputs.log
```

And in `ai/logs/`: timestamped run log.

---

## Downstream Publication

After a successful run, `RUN-workflow.sh` creates symlinks in
`trees_species/output_to_input/BLOCK_gigantic_species_tree/` pointing back to
the real files in `OUTPUT_pipeline/`. Downstream subprojects consume these
symlinks.

Expected symlinks:
- `{species_set}-species_tree-with_clade_ids_and_names.newick` → full format tree
- `{species_set}-species_tree-simple.newick` → simple format tree
- `{species_set}-species_tree-clade_ids_only.newick` → ids-only format tree
- `{species_set}-clade_name_X_clade_id.tsv` → clade map lookup

**Primary downstream consumer**: `BLOCK_permutations_and_features` (sibling BLOCK
within the same `trees_species/` subproject), which takes the full format tree
and enumerates topology permutations for user-specified unresolved clades.

---

## Questions AI Assistants Should Ask Users

| Situation | Ask the user |
|---|---|
| User wants to run the BLOCK for a new species set | "What should I use for `species_set_name`? (e.g., species70)" |
| User's tree has polytomies | "This BLOCK refuses polytomies. Would you like to resolve them manually, or pass the tree to `BLOCK_permutations_and_features` which handles unresolved clades via config?" |
| User's tree has branch lengths they want to preserve | "This BLOCK standardizes all branch lengths to 1.0 per GIGANTIC convention. Would you like to save a copy of your original tree elsewhere before running?" |
| Visualization soft-failed | "Script 005 hit a tooling issue and fell back to a placeholder. No downstream step depends on this — the other outputs are still valid. Would you like to investigate the ete3 issue, or proceed?" |
| User has a fully-resolved species tree but the topology is debated | "This BLOCK handles one specific tree topology. If you want to compare multiple topologies, run this BLOCK once per topology with different `species_set_name` values, or use `BLOCK_permutations_and_features` with the unresolved clades marked in its config." |
