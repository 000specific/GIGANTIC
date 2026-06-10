<!-- ============================================================================
AI:      Claude Code | Opus 4.8 | 2026 June 03
Human:   Eric Edsinger
Purpose: Record a defect found in the species70 candidate structure set produced
         by BLOCK_permutations_and_features (duplicate structure + clade-ID dedup
         failure), surfaced during ocl_outgroup_anchors exploration.
============================================================================ -->

# trees_species — Known Issues

## ISSUE 1 (2026-06-03): Duplicate structure in the species70 105-structure set + clade-ID dedup failure

### Summary

`structure_001` and `structure_004` have the **identical 5-clade topology**, so the
105-structure set produced for species70 contains only **104 distinct 5-clade
topologies** — it should contain exactly **105** (= (2·5−3)!! distinct rooted binary
topologies of the 5 unresolved clades: Ctenophora, Porifera, Placozoa, Cnidaria,
Bilateria). One true topology is therefore **duplicated** and one is **missing**.

### Evidence

Both structures resolve the 5 clades as `(Ctenophora,(Porifera,(Placozoa,(Cnidaria,Bilateria))))`:

| structure | Metazoa→ | next | next | tip pair |
|-----------|----------|------|------|----------|
| structure_001 | Ctenophora | Porifera | Placozoa | (Cnidaria,Bilateria) |
| structure_004 | Ctenophora | Porifera | Placozoa | (Cnidaria,Bilateria) |

But the **internal clade IDs differ** between the two (a Rule 6 violation — the same
clade should get the same `clade_id_name` across structures):

| grouping | structure_001 ID | structure_004 ID |
|----------|------------------|------------------|
| Porifera+Parahoxozoa side | `C087_Metazoa_Subclade_1` | `C147_Clade_147` |
| Placozoa+(Planulozoa) | `C091_Parahoxozoa` | `C144_Clade_144` |
| (Cnidaria,Bilateria) ancestor | `C096_Planulozoa` | `C140_Clade_140` |

Source: per-structure `parent_child_table.tsv` (consistent across the OCL inputs and
the `3-output` clade-ID newicks).

### Downstream symptom

When grouping the 105 structures by which single clade sits basal (pectinate splits),
the counts come out **Ctenophora 16 / Porifera 14 / Placozoa 15 / Cnidaria 15 /
Bilateria 15** (= 75) instead of a clean **15 each**. The extra Ctenophora-basal count
is the duplicate (004); the deficit on Porifera is the missing topology (a Porifera-basal
arrangement that was never generated).

### Likely root cause

One or both of:
- `BLOCK_permutations_and_features/.../ai/scripts/002_ai-python-generate_topology_permutations.py`
  — the canonical-form **deduplication** of generated topologies let a duplicate through
  (or dropped a distinct one).
- `.../ai/scripts/003_ai-python-assign_clade_identifiers.py`
  — the **canonical topological signature** that assigns/reuses `clade_id_name` failed to
  recognize structure_004's internal clades as the same as structure_001's, minting new
  provisional `C140/C144/C147 (Clade_NNN)` IDs instead of reusing `C087/C091/C096`.

The two symptoms (duplicate topology + mismatched internal IDs) most likely share a single
root cause in the canonical-signature logic.

### Impact

- The candidate-structure set is **incomplete** (missing one of the 105 true topologies)
  and **internally inconsistent** (a duplicate with non-matching clade IDs).
- **Cross-structure aggregation that keys on `clade_id_name`** (e.g. `occams_tree`-style
  ranking, any per-clade consensus across the 105) is unreliable for the affected clades,
  because the same clade carries different IDs in 001 vs 004.
- All downstream consumers ran on this set, including the `ocl_phylogenetic_structures`
  OCL orthogroups run (`workflow-RUN_1`, 105 structures).

### How to reproduce / verify

`research_notebook/research_ai/subproject-ocl_outgroup_anchors/005_ai-python-find_swapped_structure.py`
builds the induced 5-clade topology for each of the 105 structures from the parent-child
tables and reports: `distinct 5-clade topologies = 104`, with structure_001's topology
shared by `[structure_001, structure_004]`.

### Recommended next steps (not yet done)

1. Audit script 002 dedup and script 003 canonical-signature assignment on the species70 input.
2. Regenerate the structure set; assert exactly 105 distinct topologies and stable
   `clade_id_name` across structures (no `Clade_NNN` provisional IDs surviving where a named
   clade exists).
3. Re-run downstream (OCL etc.) on the corrected set before any quantitative cross-structure claims.

### RESOLUTION (2026-06-03)

Two fixes applied to the **COPYME** scripts (validated on `workflow-RUN_02-permutations_and_features`
via scripts 001→002→003):

1. **Script 002 — `extract_original_topology_from_tree` / `prune_to_labels`:** a node whose own
   label IS one of the 5 unresolved clades now collapses to a leaf (the clades are internal nodes
   with species beneath). Previously the function returned `None`, so the original tree was never
   matched and `structure_001` was duplicated. After fix: 002 finds the original (it was at
   alphabetical position 4 — exactly the old `structure_004`), removes it from the set, and places
   it as `structure_001`. Verified: **105 distinct topologies, no duplicates, structure_001 = the
   original.**

2. **Script 003 — `get_canonical_structure`:** the "is this an unresolved clade?" stop check was
   inside the leaf branch, so in structure_001's full species tree (where the 5 clades are internal)
   signatures recursed to species and never matched the skeleton structures' clade-name-level
   signatures — so the user's internal clade names were not reused. Moved the check to the top with
   an EXACT name match. Verified: **`Planulozoa` (C096) now reused across 15 structures,
   `(Bilateria,Cnidaria)` → `C096_Planulozoa` everywhere, 0 signatures map to >1 clade ID.**

Status: **fixes in COPYME, validated 001–003.** Pending: full pipeline regenerate (004–010),
refresh `output_to_input`, and OCL rerun on the corrected 105.
