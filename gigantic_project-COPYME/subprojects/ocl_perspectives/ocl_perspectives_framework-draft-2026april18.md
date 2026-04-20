# OCL Perspectives Framework

**Subproject name**: `ocl_perspectives`
**Status**: DRAFT — 2026 April 18
**Authors**: Eric Edsinger (framing + Group A seed) + Claude Code (formalization + draft)
**Purpose**: Formal post-OCL framework for processing OCL outputs into
interpretive perspectives on how features map onto species trees.

## Relationship to `moroz_innovations`

`moroz_innovations` (built 2026-04-18) implements Leonid's operational
innovation criteria (any-species / all-species set-membership tests).
These criteria are **not founded in phylogenetics** — they do not
reference the species tree topology or OCL block-state transitions.

`ocl_perspectives` (this framework) provides the phylogenetically rigorous
alternative, and captures all the evolutionary patterns Leonid cares about
(and more), while respecting the species tree structure.

**Deprecation plan**: `moroz_innovations` kept available during the
transition so downstream work/handoffs continue to function. Once
`ocl_perspectives` is built and delivering the equivalent (via Group C
perspectives in particular), `moroz_innovations` is deprecated and
eventually deleted. Add a deprecation note to `moroz_innovations/README.md`
pointing to `ocl_perspectives` when the latter is ready.

Each perspective is a **named, Boolean-composable query** over OCL state
identifiers, carrying a specific evolutionary interpretation. The
formalism lets users pick perspectives off a menu, and the framework
stays composable and extensible.

---

## 1. Vocabulary

### 1.1 OCL five-state vocabulary (GIGANTIC convention — unchanged)

| Letter | Name | Definition |
|---|---|---|
| `A` | Inherited Absence | Both parent and child absent, pre-origin |
| `O` | Origin | First appearance entering child |
| `P` | Presence / Conservation | Inherited presence (both parent and child) |
| `L` | Loss | Active loss (parent has it, child doesn't) |
| `X` | Inherited Loss | Both parent and child absent, post-loss upstream |

### 1.2 OCL state identifier format

```
ocl_<STATE>-<block_id>::<feature_id>
```

Examples:
- `ocl_O-C082_Metazoa::C086_Ctenophora::OG000228` — OG000228 arose in the Metazoa → Ctenophora phylogenetic block (evolutionary span)
- `ocl_P-C082_Metazoa::C086_Ctenophora::annogroup_pfam_1` — annogroup_pfam_1 conserved across the Metazoa → Ctenophora phylogenetic block
- `ocl_L-C086_Ctenophora::C017_Beroe_ovata::OG001234` — OG001234 lost in the Ctenophora → Beroe_ovata phylogenetic block

**Atomic. Composable.** Each identifier encodes a single (state, block, feature) triple. Perspectives are Boolean operations over sets of identifiers.

### 1.3 Feature areas

**Homology-based** (feature identity rooted in inferred shared ancestry):
- Orthogroups (OrthoFinder, etc.)
- HMM-based annotations (Pfam, InterPro families)
- Gene families
- Gene groups
- One-direction homologs
- Synteny blocks

**Non-homology-based** (feature identity from other biological properties):
- Taxonomy (species-level classification)
- Gene sizes

Perspectives may apply differently (or not at all) across these areas —
see the guards section (§6).

### 1.4 Clade identifier (Rule 6)
`CXXX_Name`, e.g. `C082_Metazoa`.

### 1.5 Phylogenetic block (Rule 7) / Evolutionary span

Two names for the same Parent::Child edge, through different lenses
(Rule 1 discipline):

- **Phylogenetic block** — the edge as a **data structure** on the species
  tree, format `Parent_Clade_ID_Name::Child_Clade_ID_Name`,
  e.g. `C082_Metazoa::C086_Ctenophora`.
- **Evolutionary span** — the same edge viewed as the **biological period**
  it represents (the real evolution that occurred between the parent and
  child clade's emergence in nature).

**Preferred prose phrasing** for origin / conservation / loss claims
(replaces awkward phrasings like "arose entering Ctenophora from Metazoa"):

- "arose **in the Metazoa → Ctenophora phylogenetic block**"
- "arose **during the Metazoa → Ctenophora evolutionary span**"
- "conserved **across the Metazoa → Ctenophora phylogenetic block**"
- "lost **in the Ctenophora → Beroe_ovata phylogenetic block**"

Use `phylogenetic block` when the framing is data/topology.
Use `evolutionary span` when the framing is biological reality.
The arrow notation (`Parent → Child`) makes directionality visually
explicit and avoids the "entering from" confusion.

---

## 2. Group A — Clade-Feature Origins

Perspectives anchored on where a feature's origin state `O` falls relative to a target clade.

### A1 — Feature Originates at Clade's Entry Block
**Formal**: `ocl_O-{Parent_of_Clade}::{Clade}-{feature_id}` exists.
**Interpretation**: evolutionary innovation defining the clade. "What arose at the Ctenophora origin?"

### A2 — Feature Originates at Clade's Entry Block AND Is Present in All Clade Species
**Formal**: A1 AND every phylogenetic block inside the clade's subtree has state `O` or `P` for the feature (zero `L` / `X` anywhere below).
**Interpretation**: perfectly-conserved clade innovations — evolved here and retained universally since. Phylogenetic analogue of "innovations_all_species," rigorized.

### A3 — Feature Originates at Clade's Entry Block AND Is Lost in at Least One Descendant
**Formal**: A1 AND ≥1 `ocl_L` or `ocl_X` identifier for this feature on a block inside the clade's subtree.
**Interpretation**: imperfect innovations — evolved at the clade but not universally retained. Complement of A2.

### A4 — Feature Originates on a Specific Phylogenetic Block
**Formal**: `ocl_O-{user_specified_block}-{feature_id}` exists.
**Interpretation**: edge-specific innovation. "What arose on *this* edge?" — finer than A1. Useful when the transition matters more than the landing clade (e.g., `C082_Metazoa::C086_Ctenophora` vs. `C082_Metazoa::C091_ParaHoxozoa`).

### A5 — Feature Originates Strictly Within Clade's Subtree (Not at Clade's Entry)
**Formal**: `ocl_O-{block}-{feature_id}` exists where the block's child is a clade strictly inside the target's subtree (not the target itself).
**Interpretation**: post-divergence innovations specific to lineages within the clade. "What arose *inside* Ctenophora after it separated from sister clades?"

### A6 — Feature Originates on the Path to Clade (Inherited Ancestry)
**Formal**: `ocl_O-{block}-{feature_id}` exists where the block lies on the root-to-clade path.
**Interpretation**: accumulated ancestral innovations the clade inherited. "What evolutionary history did Ctenophora walk in with?"
**Guard**: orthogroups (see §6).

### A7 — Feature Originates Prior to Clade AND Is Present at Clade's Entry Block
**Formal**: `ocl_O-{block}-{feature_id}` exists where block is on the root-to-clade path (exclusive of clade's entry block), AND `ocl_P-{Parent_of_Clade}::{Clade}-{feature_id}` exists.
**Interpretation**: ancestral features that survived the clade's entry (were not lost at origin). Starting point for joint retention perspectives (Group C).
**Guard**: orthogroups.

---

## 3. Group B — Clade-Feature Retention and Loss

Perspectives anchored on `P` / `L` / `X` state patterns within a clade's subtree, agnostic to origin.

### B1 — Feature Fully Retained Within Clade
**Formal**: every phylogenetic block inside the clade's subtree has state `O` or `P` for the feature. Zero `L` / `X` in subtree.
**Interpretation**: perfect within-clade retention, regardless of origin placement.

### B2 — Feature Fully Lost Within Clade
**Formal**: at least one `ocl_L` exists at or within the clade (the triggering loss), and every descendant block is in state `X` (no re-gain possible under OCL model). Equivalently, every terminal species in the clade's subtree has no presence.
**Interpretation**: total clade-specific extinction. The feature was present entering the clade but has been eliminated across every descendant.

### B3 — Feature Partially Retained Within Clade
**Formal**: at least one `ocl_P` AND at least one `ocl_L` or `ocl_X` inside the clade's subtree.
**Interpretation**: mixed retention. Candidate for breakdown by sub-clade or species.

### B4 — Feature Lost at Clade's Entry
**Formal**: `ocl_L-{Parent_of_Clade}::{Clade}-{feature_id}` exists.
**Interpretation**: the feature was lost at the clade's origin block. Clade-defining loss.

### B5 — Feature Lost on a Terminal Species Branch Within Clade
**Formal**: `ocl_L-{subclade_parent}::{species}-{feature_id}` exists for at least one species in the clade's subtree.
**Interpretation**: lineage-specific loss. Terminal-branch innovation-via-loss.

### B6 — Feature Conservation Rate Above Threshold Within Clade
**Formal**: `count(ocl_P in subtree) / count(ocl_P + ocl_L + ocl_X in subtree) >= threshold`. Threshold is user-config.
**Interpretation**: parametric filter for "mostly retained" features. Useful when binary retention is too strict.

---

## 4. Group C — Joint Origin × Retention (Leonid's Questions, Rigorized)

Perspectives combining Group A and Group B. The post-OCL analogues of Leonid-style clade-innovation questions.

### C1 — Clade-Defining Perfectly-Retained Innovation
**Formal**: A1 AND B1.
**Interpretation**: strong clade innovations — evolved here, kept universally. Phylogenetic analogue of "innovations_all_species." (Logically equivalent to A2 as stated.)

### C2 — Clade-Defining Innovation With Any Retention
**Formal**: A1 AND (B1 OR B3) — origin at clade AND at least one `P` in subtree.
**Interpretation**: clade innovations with at least partial retention. Phylogenetic analogue of "innovations_any_species" but strictly more informative — OCL origin anchoring forbids features present outside the clade (which Leonid's `any` version also forbids), AND retains feature-has-survived-to-at-least-one-species semantics.

### C3 — Ancient Feature Retained Only in Clade (Clade as Sole Refuge)
**Formal**: A6 (origin is ancestor of clade) AND B1-restricted-to-clade AND for every other descendant-of-origin clade not on the path to the target, B2 (fully lost within).
**Interpretation**: ancestral features that have survived only within this clade. "The clade is now the sole refuge." Biologically striking pattern.
**Guard**: orthogroups.

### C4 — Ancient Feature With Clade-Specific Loss (Clade-Defining Discard)
**Formal**: A6 AND B2 — ancient origin AND totally lost within clade.
**Interpretation**: the clade specifically discarded an ancestral feature. Defining losses of the clade lineage.
**Guard**: orthogroups.

### C5 — Ancient Feature Retained Intact in Clade While Variable Elsewhere
**Formal**: A6 AND B1-restricted-to-clade AND (B3 or B1) restricted to non-target descendants.
**Interpretation**: the clade is a stable reservoir for ancestral features that other lineages handle more variably. Milder form of C3 — not sole refuge, but conservative.
**Guard**: orthogroups.

---

## 5. (Deferred) Group D — Path-State and Per-Species Analyses

Placeholder — moved to a separate proposal or a future expansion of this framework. These use the per-feature-per-species AOPLX letter strings directly rather than block-level aggregates, and likely deserve their own BLOCK with visualization primitives attached.

Candidates:
- D1: per-species lineage-specific loss profile (L on terminal block)
- D2: per-block gain/loss heatmap
- D3: feature life-history trace (expand a feature's full AOPLX walk across all species)

---

## 6. Guards: when perspectives apply

Some perspectives are only interpretable for certain feature areas.

### Orthogroup guard (applies to A6, A7, C3, C4, C5)

Orthogroup identity is dataset-bounded. Saying "this orthogroup originated at the root" is largely a framing artifact — orthogroup identity emerges from sequence clustering of the extant species set, so claims about pre-root history are weakly grounded at best.

Behavior: when a Group A6/A7 or Group C3/C4/C5 perspective is applied to orthogroups, **compute the result anyway but annotate outputs as "applicability caveat: orthogroup identity is dataset-bounded"** rather than silently suppress. This keeps the user informed and preserves data for inspection.

### Non-homology-based guard (applies broadly)

Taxonomy and gene-sizes as features don't have origins in the sequence-evolution sense. OCL perspectives may still be mechanically computable but the biological interpretation diverges.

Behavior: per-area handling in each workflow's Script 001. Document the interpretive caveat clearly in output README files per run.

---

## 7. Architecture

### 7.1 Subproject layout

Proposed new subproject: `ocl_perspectives/`

```
gigantic_project-COPYME/subprojects/ocl_perspectives/
├── README.md
├── AI_GUIDE-ocl_perspectives.md
├── BLOCK_clade_origins/               (Group A)
│   └── workflow-COPYME-clade_origins/
├── BLOCK_clade_retention_and_loss/    (Group B)
│   └── workflow-COPYME-clade_retention_and_loss/
├── BLOCK_origin_retention_joints/     (Group C)
│   └── workflow-COPYME-origin_retention_joints/
```

Cross-structure perspectives (old Group E) live in their own subproject
per Eric's note.

### 7.2 Per-BLOCK workflow config pattern

Each workflow exposes a menu of perspectives via config YAML:

```yaml
run_label: "species70_clade_origins_run1"

target_clades: [ Metazoa, Ctenophora, Porifera, Placozoa, Cnidaria, Bilateria ]
target_structures: [ structure_001 ]

perspectives:
  A1_origins_at_clade:
    enabled: true

  A2_origins_at_clade_all_retained:
    enabled: true

  A3_origins_at_clade_with_loss:
    enabled: true

  A4_origins_at_specific_block:
    enabled: false
    blocks: [ "C082_Metazoa::C086_Ctenophora" ]

  A5_origins_within_subtree:
    enabled: true

  A6_origins_on_path_to_clade:
    enabled: false
    # orthogroup-guard-sensitive; set true only if you understand the caveat

  A7_origin_prior_and_present_at_clade:
    enabled: false

feature_sources:
  orthogroups:
    enabled: true
    output_to_input_base: "../../../orthogroups_X_ocl/output_to_input/BLOCK_ocl_analysis"
    run_label: "species70_X_OrthoHMM"
    ...

  annotations:
    enabled: true
    ...
```

### 7.3 Shared utility: `utils_ocl_state_space.py`

Primitive operations over OCL state identifiers. Exposed to every BLOCK.

```python
# Iteration
get_state_identifiers( structure_id, feature_area, state_filter = None )
    # Yields ocl_<STATE>-<block>::<feature_id> streams

# Boolean composition
intersect( stream_a, stream_b )
union( stream_a, stream_b )
difference( stream_a, stream_b )

# Filtering
filter_by_state( identifiers, state_letter )
filter_by_clade( identifiers, clade_id_name, mode )
    # modes: entry_block, inside_subtree, on_path_to, at_or_within
filter_by_feature_area( identifiers, area )
filter_by_block( identifiers, block_id )

# Perspective registry
PERSPECTIVES = {
    'A1_origins_at_clade': perspective_a1_origins_at_clade,
    'A2_origins_at_clade_all_retained': perspective_a2_...,
    ...
}
```

Each perspective is a function taking (structure_id, target_clade, feature_area, config) → Iterable[ row_dict ].

### 7.4 Output conventions

Per perspective × feature_area × structure, one TSV:

```
OUTPUT_pipeline/structure_{NNN}/1-output/
    1_ai-structure_{NNN}-A1_origins_at_clade-orthogroups.tsv
    1_ai-structure_{NNN}-A1_origins_at_clade-annotations.tsv
    1_ai-structure_{NNN}-A2_origins_at_clade_all_retained-orthogroups.tsv
    ...
```

Plus a per-structure summary pivot table (perspective × clade × feature_area count) at:
```
1_ai-structure_{NNN}-summary_counts.tsv
```

### 7.5 Integration with existing subprojects

Inputs come through the canonical `output_to_input/` pattern (now working,
after today's symlink fix):

- Reads `ocl_output_to_input/BLOCK_ocl_analysis/{run_label}/structure_NNN/4_ai-*-complete_ocl_summary.tsv`
- Reads `trees_species/output_to_input/.../9_ai-clade_species_mappings-all_structures.tsv`
- Reads `trees_species/output_to_input/.../Species_Parent_Child_Relationships/` for subtree walks
- Path_states TSVs read only when Group D perspectives (deferred) are eventually added

---

## 8. Open questions for review

1. **Orthogroup guards** — annotate-and-compute vs. suppress? Draft proposes annotate-and-compute.
2. **C1 vs A2 overlap** — C1 as stated is logically identical to A2. Keep both for discoverability (A2 anchored in "origin," C1 anchored in "joint query")? Or collapse?
3. **Group D placement** — separate BLOCK in this subproject, or defer to a dedicated path-state subproject (per-species analyses have a different flavor)?
4. **Group B numbering** — B6 (threshold) is parametric; worth a separate subgroup (B6, B7, ... as parametric variants)?
5. **Perspective naming discipline** — current draft uses `A1_origins_at_clade` etc. Any preferred shorter or longer scheme?
6. **Cross-subproject atlas** — should there eventually be a top-level "perspective atlas" doc listing every perspective across every subproject with its formal definition + interpretation, for grep-and-find?
7. **Logical expressions in config** — should perspectives support AND/OR/NOT composition in config (e.g., `A1 AND B3`), or keep them as fixed named bundles? Fixed-named is simpler to document but less flexible.

---

*End of draft. Review when fresh; iterate as needed.*
