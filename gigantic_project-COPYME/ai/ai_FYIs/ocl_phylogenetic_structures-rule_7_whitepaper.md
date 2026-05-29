# Phylogenetic Blocks
### Event Blocks, Inheritance Blocks, and a Five-State Vocabulary for OCL Analysis in the GIGANTIC Framework

**Authors**: Eric Edsinger (concept), Claude Code (drafting)
**Date**: 2026 April 14
**Status**: Proposed convention — candidate for Rule 7 of `AI_GUIDE-project.md`

---

## Abstract

Any analysis that maps the history of a feature onto a species tree eventually needs to name two different things: the edges of the tree itself, and what a specific feature is doing on each edge. The phylogenetic vocabulary in common use — *branch*, *lineage*, *stem*, *edge* — is ambiguous about whether the parent and child nodes are included in the named object, and it collapses biologically distinct situations (the absence of a feature before it has originated, versus the absence of a feature after it has been lost) into a single topological category. GIGANTIC's Origin-Conservation-Loss (OCL) analysis needs more precision than this.

This paper introduces a naming scheme built on two ideas. A **phylogenetic block** is a single parent-to-child edge of a species tree structure — a segment of the tree that includes the parent node, the child node, and the edge that joins them, with no intervening nodes. A **phylogenetic block-state** is a phylogenetic block paired with a specific feature's state on that block, drawn from a five-state vocabulary refining classical Dollo: **Inherited Absence (A)**, **Origin (O)**, **Inherited Presence (P)**, **Loss (L)**, **Inherited Loss (X)**. The five states split cleanly into two kinds: **phylogenetic event blocks** (O and L, where a feature's state changes between the parent and child endpoints) and **phylogenetic inheritance blocks** (A, P, X, where the state is the same at both endpoints and has been inherited across the block). A single identifier form carries both the tree anchor and the feature's state: `parent_clade_id_name::child_clade_id_name-LETTER`.

---

## 1. Motivation

### 1.1 What an edge represents

An edge on a species tree carries two layers of meaning at once, and keeping them straight matters for everything that follows.

The first layer is **phylogenetic**: the edge is a relationship in the tree data structure between a parent node and a child node, with an associated phylogenetic distance that can be expressed in branch length, elapsed time, or number of substitutions — whatever the tree was built from. This is the edge as a structural fact.

The second layer is **evolutionary**: that same edge stands for all the actual biological change that occurred in the lineage as it diverged from the parent's state toward the child's state over time. Gene gains, gene losses, amino-acid substitutions, morphological novelties, expression shifts — a single edge on a species tree silently contains however much of each happened in however long the real lineage persisted. Per Rule 1 of `AI_GUIDE-project.md`, the edge as a tree object is phylogenetic; what it represents in biology is evolutionary.

A species tree itself is a phylogenetic object. The feature-history inferences we draw from combining a feature's distribution with a species tree — where it arose, where it was lost, where it was conserved — are evolutionary. The distinction is load-bearing: the same edge can carry one origin event, ten loss events, or a thousand silent substitutions, and the tree structure doesn't tell you which.

For details on how GIGANTIC distinguishes species-tree **topologies** from **structures**, and how OCL analysis assumes a fully resolved species tree structure while handling ambiguity in the input by generating every fully resolved structure consistent with the ambiguous nodes, see `planning-occams_tree/whitepaper.md`.

### 1.2 Why the existing vocabulary doesn't cut it

The words we usually reach for when talking about tree edges are *branch*, *lineage*, *stem*, and *edge*. None of them says precisely what GIGANTIC needs.

**Branch** is generic and silent about parent-child endpoint inclusion: does "the Metazoa branch" include the Metazoa node, the parent node, both, or neither? Writers use it all three ways, often in the same paper.

**Lineage** is close to what we want for origins, but it carries an implicit continuous-process connotation — a lineage *flows* through time — which doesn't fit the discrete, per-feature state assignment that OCL needs.

**Stem** is a real paleontological term with a specific meaning (the branch leading from the divergence with a sister group down to a crown group's most recent common ancestor), and it comes attached to the crown/stem/total-group framework of systematic paleontology. GIGANTIC is not doing that work.

**Edge** is graph-theoretically precise but says nothing about what biology the edge represents.

None of these words distinguishes a block where a feature hasn't yet originated (absence upstream of its first appearance) from a block where the feature was once present and then lost (continued absence downstream of a loss event). Topologically these two situations look identical — parent absent, child absent — but biologically they are opposite. A feature that hasn't originated is not a "lost" feature. Without a vocabulary that separates the two, OCL analysis either over-counts losses (by treating pre-origin absence as loss) or under-counts them (by collapsing everything absent into one bucket). Neither is acceptable.

GIGANTIC needs a five-way distinction where standard tree vocabulary offers two or three.

### 1.3 The five-state vocabulary

GIGANTIC adopts the five-state event vocabulary from the companion Occam's Tree framework (`planning-occams_tree/whitepaper.md`), which refines the classical Dollo present/absent dichotomy into the full enumeration of parent/child state pairs with their evolutionary histories:

| State | Parent has the feature? | Child has the feature? | Biological meaning |
|---|---|---|---|
| Inherited Absence | no | no (pre-origin) | the feature has not yet arisen in this lineage |
| Origin | no | yes | the feature first appears here — an **event** |
| Inherited Presence | yes | yes | the feature is conserved across this block |
| Loss | yes | no | the feature is first lost here — an **event** |
| Inherited Loss | no (post-loss) | no (post-loss) | the feature was lost upstream; absence continues |

Two events (Origin, Loss) flanked by three inheritances (Inherited Absence, Inherited Presence, Inherited Loss). Every block-feature pair falls into exactly one of these five states.

The important move in this vocabulary is that **Inherited Absence and Inherited Loss are named as distinct states even though their parent-child presence patterns are identical.** The distinction is historical, not local: Inherited Absence lives upstream of the feature's origin (the feature has never existed in this part of the tree), while Inherited Loss lives downstream of a loss event (the feature did exist here once). Standard tree vocabulary can't encode this difference in an edge identifier. GIGANTIC's scheme can.

---

## 2. Definitions

### 2.1 The phylogenetic block

A **phylogenetic block** is a single parent-to-child edge of a species tree structure — a segment of the tree that includes the parent node, the child node, and the edge that joins them, with no intervening nodes between them.

Two properties follow directly from this definition, and both matter.

**A block is atomic.** The parent-to-child relationship is the smallest step in the tree; there is no "half-block" below it. Any reference to a relationship between two clades that are not directly connected is a **path** through the tree, not a block. A path is realized as a sequence of parent-child blocks through the intervening nodes of clades.

*For example*: if a particular species tree structure places the clades Holomycota, Holozoa, Filasterea, and Metazoa along a chain Holomycota → Holozoa → Filasterea → Metazoa, then there is no Holozoa-Metazoa block in that structure. The path between Holozoa and Metazoa is realized as two parent-child blocks: Holozoa-Filasterea and Filasterea-Metazoa. In a different, more coarsely resolved structure where Holozoa is the direct parent of Metazoa, the Holozoa-Metazoa block would exist.

**A block is feature-agnostic.** It exists as a structural fact about the species tree, independent of any particular feature. Orthogroups, HMM-based annotations, morphological traits, expression profiles — none of them change the block. The block is there, available as an anchor, for whatever feature we want to analyze on it.

**Highlight — blocks as the unit of resolution.** Phylogenetic blocks are the unit at which OCL analysis resolves evolution onto the tree. A block captures "what happened between a parent clade and its direct child," but *how much* actually happened — how much real time elapsed, how many substitutions accumulated, how many genes were gained or lost along the way — is cryptic and variable from block to block. Two blocks of equal visual length on a displayed tree can represent wildly different amounts of evolutionary change. The block is where we *can* localize an event; within-block resolution is not available from the tree alone.

### 2.2 The phylogenetic block-state

A **phylogenetic block-state** is a phylogenetic block paired with a specific feature's state on that block. Every block has exactly one block-state per feature.

Where a block is feature-agnostic, a block-state is feature-specific: the same tree edge has different block-states for different features, depending on each feature's phylogenetic distribution when mapped onto the species tree. The Holozoa-Metazoa block in a given structure is a single structural entity, but for one orthogroup it might be in state O (origin event), for another in state P (inherited presence), and for a third in state A (inherited absence) — all at once, depending on the orthogroup.

The five possible states — Inherited Absence (A), Origin (O), Inherited Presence (P), Loss (L), Inherited Loss (X) — are exactly the five described above in §1.3. Each letter is short, stable, and directly encodes one of the five cases.

### 2.3 Event blocks and inheritance blocks

The five block-states split into two kinds, and this split is biologically meaningful.

A **phylogenetic event block** is a type of phylogenetic block on which a feature's state is **different** at the parent and child endpoints. The only two ways this can happen are:

- the feature is absent at the parent and present at the child — an **Origin** event (state O), or
- the feature is present at the parent and absent at the child — a **Loss** event (state L).

A **phylogenetic inheritance block** is a type of phylogenetic block on which a feature's state is **the same** at both the parent and child endpoints of the block. The state has been inherited across the block rather than changed on it. The three possibilities are:

- both parent and child absent, and the feature has not yet originated in this lineage — **Inherited Absence** (state A);
- both parent and child present — **Inherited Presence** (state P; this is what the classical literature calls conservation);
- both parent and child absent, but the feature was previously present somewhere upstream and has been lost — **Inherited Loss** (state X).

The event/inheritance split tracks the biological distinction between evolutionary change and evolutionary persistence. On an inheritance block, nothing has happened to this feature between the parent clade and the child clade — the state has simply been inherited. On an event block, something has happened: either the feature has newly appeared, or it has newly disappeared.

**Highlight — event blocks anchor inferences to evolutionary reality.** When GIGANTIC identifies a phylogenetic event block for a feature within a species tree structure, what that identification actually claims is this: at some point within the real evolutionary time and biological events that this block represents on the tree, a change in the feature's state occurred between the parent clade's state and the child clade's state. The tree can tell us *which block* — which parent-child step — contains the change. It cannot tell us where within the block the change happened, how many changes happened, or how long it took. The block is the resolution; the event is the inference we draw from the two endpoint states.

### 2.4 Plain-language summary

In everyday language:

- A **phylogenetic block** is one parent-to-child step of a species tree: the parent clade, the child clade, and the edge between them.
- A **phylogenetic event block** is a block on which a feature's evolutionary history has a change — it newly appeared (origin) or newly disappeared (loss).
- A **phylogenetic inheritance block** is a block on which a feature stays in whatever state it was in upstream — absent because it hasn't arisen, present because it's been retained, or absent because it was lost earlier.

### 2.5 Phylogenetic paths and phylogenetic path-states

The block framework extends naturally from a single parent-child step to a full lineage walk.

A **phylogenetic path** is a sequence of consecutive phylogenetic blocks — the walk across the species tree from the conceptual biological parent of the species-tree root down to one species. Each species in the structure has exactly one phylogenetic path. Blocks are the atomic unit; a path is a chain of blocks laid end-to-end.

Every path begins at **`C000_OOL`** — Origin Of Life — which GIGANTIC treats as the conceptual biological parent of any rooted species tree. Users do not add OOL to their species tree; `trees_species` synthesizes it automatically. The motivation is biological, not computational: every real clade ultimately descends from OOL, so giving the species-tree root an incoming block `C000_OOL::<root_clade_id_name>` is an accurate representation of the fact that the feature history ancestral to the sampled tree is unresolvable within the sample. Every feature's origin block, every species's path, and every block-state classification then falls out of the same uniform framework — there is no special case for the root.

A **phylogenetic path-state** is a phylogenetic path paired with a specific feature's state along each block of the path — the concatenated five-state letters in OOL-end-to-species-end order. For example, the path-state `AAAOPLXX` reads as: A A A (feature absent on the first three blocks; these are ancestral to the feature's origin clade), O (origin on this block), P (inherited presence on the next block), L (loss on this block), X X (continued inherited absence after the loss on the final two blocks, terminating at the species).

Path-states are **feature-specific** — the same path carries different path-states for different features. A path-state is the compact fingerprint of a feature's inferred evolutionary history along one species's lineage: where the feature originated, where it was conserved, and where it was lost, all read in a single string.

Valid path-state sequences follow the regular pattern `A* [O [P* [L X*]?]?]?`: zero or more A's, an optional O, zero or more P's, an optional L, and zero or more X's. This sequence constraint is enforced as a validation check in the OCL pipeline. Deviations indicate a computation bug upstream.

---

## 3. Identifier Structure

GIGANTIC names each tree-related object with a canonical string identifier, built up from the clade-level identifier `clade_id_name` (format `CXXX_Clade_Name`, e.g. `C082_Metazoa`; see Rule 6 for the full specification).

### 3.1 Clade identifier

A clade is named by its `clade_id_name`. Examples: `C082_Metazoa`, `C001_Fonticula_alba`, `C069_Holozoa`.

### 3.2 Block identifier

A phylogenetic block is written by joining its parent and child `clade_id_name`s with the `::` delimiter:

```
parent_clade_id_name :: child_clade_id_name
```

Example: `C069_Holozoa::C082_Metazoa`.

Both endpoint clades appear in the identifier, reflecting that both the parent node and the child node are part of the block. The `::` delimiter has been GIGANTIC's block-naming convention from the beginning of the project; its reuse here is deliberate continuity.

A block identifier is feature-agnostic. It names a tree-structural fact and does not say anything about what any specific feature is doing on the block.

### 3.3 Block-state identifier

A phylogenetic block-state is written by extending the block identifier with a hyphen-prefixed state letter:

```
parent_clade_id_name :: child_clade_id_name - LETTER
```

Example: `C069_Holozoa::C082_Metazoa-O` — read as "on the Holozoa-Metazoa phylogenetic block, this feature is in state O (Origin), so the feature is absent at the Holozoa parent and present at the Metazoa child."

The letter codes and their meanings:

| Letter | State | Parent has the feature? | Child has the feature? | Kind |
|---|---|---|---|---|
| **A** | Inherited Absence | no | no (pre-origin) | inheritance |
| **O** | Origin | no | yes | event |
| **P** | Inherited Presence | yes | yes | inheritance |
| **L** | Loss | yes | no | event |
| **X** | Inherited Loss | no (post-loss) | no (post-loss) | inheritance |

The hyphen is used as the state-suffix delimiter because it does not conflict with either of the other two delimiters already in scope: the underscore (which appears inside a `clade_id_name`) and the double colon (which separates the two clade names in the block). Parsing is unambiguous: split on the final hyphen to separate the block identifier from the state letter.

The letter ordering A → O → P → L → X traces the canonical life-cycle of a feature through evolutionary history: pre-origin absence, origination, post-origin persistence, loss, post-loss absence. Reading the letters in order tells a story.

### 3.4 The three-level identifier hierarchy

| Identifier | Form | Example | Feature-dependent? |
|---|---|---|---|
| Clade | `clade_id_name` | `C082_Metazoa` | no |
| Phylogenetic block | `parent::child` | `C069_Holozoa::C082_Metazoa` | no (tree-structural) |
| Phylogenetic block-state | `parent::child-LETTER` | `C069_Holozoa::C082_Metazoa-O` | yes (feature-specific) |

Clade, block, and block-state form a clean nesting. A block is identified by its two endpoint clades. A block-state is identified by a block together with a state letter.

---

## 4. Prose Conventions

Verbal references in GIGANTIC documentation, code comments, and human-readable output should match the number of clade names in the prose form to the number of clades actually contained in the named object — and should avoid language that imposes direction or agency onto the static tree structure.

### 4.1 Full forms

Use the full forms in formal prose or at first mention:

- **Phylogenetic block**: *the Holozoa-Metazoa phylogenetic block*. Both clade names joined by a hyphen; both parent and child endpoints are contained, and both appear.
- **Phylogenetic block-state**: *the Holozoa-Metazoa phylogenetic block in state O for orthogroup OG0000001*. The block, the state letter, and the feature in scope are all explicit.
- **Phylogenetic event block**: *the Holozoa-Metazoa origin event block for OG0000001* (for state O), or *the Metazoa-Placozoa loss event block for OG0002345* (for state L).
- **Phylogenetic inheritance block**: *the Metazoa-Bilateria inherited-presence block for OG0000001* (for state P).

### 4.2 Short forms

When context has already made the subject clear, shorter forms are fine:

- *the Holozoa-Metazoa block* (drops "phylogenetic")
- *the Holozoa-Metazoa origin* (event clear from context)
- *this block is in state P for the orthogroup* (if the orthogroup has been named recently)

### 4.3 Phrasings to avoid

Several phrasings sound natural but are technically misleading:

- *"the block entering Metazoa"* — a block is a static structural object, not an agent with motion. It doesn't enter anything.
- *"the block between Holozoa and Metazoa"* — "between" in English generally excludes the endpoints (the zone *between* two points does not include them). A phylogenetic block includes both endpoint clades, so "between" understates what the block actually contains.
- *"the feature is conserved across this block"* — in common biological usage, "conserved across X" means "present across parallel members of X" (a pattern observed across sibling lineages). Applied to a single parent-to-child block, it collides with the usual meaning.

When direction across a block is genuinely analytically meaningful — as in a calculation that walks from parent to child or from child to parent — the direction belongs in the verb, not in the block's identifier:

- *scoring the block from parent to child as a conservation vs. loss comparison*
- *tracing a path from a tip back toward the root*

---

## 5. Use in OCL Analysis

For a given feature, on a given species tree structure, every phylogenetic block in that structure has exactly one block-state in {A, O, P, L, X}. The full block-state assignment for one feature is a partitioning of every block in the structure into one of the five categories. Aggregated across features, this is the per-structure OCL accounting.

### 5.1 How each state shows up

- **Inherited Absence (A) blocks** lie upstream of the feature's origin. They contribute no events to OCL totals; they exist in the accounting as evidence that the feature had not yet arisen in this part of the tree.
- **Origin (O) blocks** are where the feature first appears. Each feature has exactly one origin block per species tree structure under minimum-set Dollo-parsimonious origin assignment.
- **Inherited Presence (P) blocks** are where the feature is conserved. They are the primary evidence of continued presence across descent.
- **Loss (L) blocks** are where the feature is first lost. A feature can have zero, one, or many loss blocks per structure, depending on its phylogenetic distribution.
- **Inherited Loss (X) blocks** lie downstream of a loss event on the same lineage. They represent the continued absence that follows a loss.

### 5.2 Structural invariants

Several invariants constrain how the five states can appear on a single feature's history within a single species tree structure:

1. Exactly one origin per structure: each feature has exactly one block in state O, located at the minimum-set Dollo-parsimonious point.
2. Blocks upstream of the origin, on the root-to-origin path, are all in state A.
3. The block immediately downstream of the origin is in state P, unless it is itself a loss block (state L).
4. Downstream of a loss (state L), every block on that descendant sub-path is in state X until a terminal tip is reached. No state-P blocks appear downstream of an intervening loss.
5. The union of states A and X accounts for all blocks where the feature is absent at both the parent and child endpoints. These two states collapse to the same parent-child presence pattern but remain biologically distinguished by their upstream history.

### 5.3 A worked example

Consider an orthogroup that arises at Metazoa and is retained in all its descendants except Placozoa, where it is lost:

| Block (tree structural) | State | Block-state identifier |
|---|---|---|
| Root to Basal | A | *upstream block*`-A` |
| Basal to Holozoa | A | `C068_Basal::C069_Holozoa-A` |
| Holozoa to Metazoa | **O** | `C069_Holozoa::C082_Metazoa-O` |
| Metazoa to Bilateria | P | `C082_Metazoa::C010_Bilateria-P` |
| Metazoa to Cnidaria | P | `C082_Metazoa::C020_Cnidaria-P` |
| Metazoa to Placozoa | **L** | `C082_Metazoa::C030_Placozoa-L` |
| Placozoa to any descendant | X | *(per-structure)* |
| Bilateria to each of its children | P | *(per-structure)* |

Reading the states in order along the Metazoa-to-Placozoa path tells a coherent story: the orthogroup arose (O), was conserved for a while (P) — and then, on the Placozoa edge, it was lost (L), with continued absence (X) propagating to every Placozoa descendant.

---

## 6. Implementation in GIGANTIC

### 6.1 Script 002 — origin determination for `orthogroups_X_ocl`

Script 002 emits, per orthogroup, two columns describing where the orthogroup originates on the species tree structure:

- **`Origin_Phylogenetic_Block`** — the tree-structural block that enters the origin clade. Example value: `C069_Holozoa::C082_Metazoa`.
- **`Origin_Phylogenetic_Block_State`** — the same block with the state letter for origin. Example value: `C069_Holozoa::C082_Metazoa-O`.

The two columns carry the same tree-structural information; the block-state column adds the explicit state classification.

### 6.2 Script 003 — per-block per-feature state classification

Script 003 iterates over every phylogenetic block in the structure (excluding terminal self-loops, where the parent and child are the same leaf — an artifact of the `parent_child_table` generation, not a true block). For each (block, feature) pair the script asks two questions:

- Is the feature present at the parent clade? ("Present" in the TEMPLATE_03 actually-present sense — at least one descendant species of the parent carries the feature.)
- Is the feature present at the child clade? (Same test, applied to the child's descendants.)

The combination of answers determines one of four of the five states directly — conservation (P), loss (L), and absence-at-both (A or X). The A-vs-X distinction requires consulting the feature's origin block (from Script 002): if the current block lies on the root-to-origin path, the absence is Inherited Absence (A); if it lies on a sub-path downstream of a loss, the absence is Inherited Loss (X). Origin (O) is identified directly from Script 002's output.

The per-block per-feature state classifications aggregate into the summary statistics that Script 003 currently produces (conservation, loss_at_origin, continued_absence, loss_coverage), extended to include the A-vs-X split.

### 6.3 Column renaming convention (decision 2c)

The rename preserves informational content while aligning with the new vocabulary:

| Previous column name | New column name | Values |
|---|---|---|
| `Origin_Clade_Phylogenetic_Block` | `Origin_Phylogenetic_Block` | `parent::child` |
| *(new)* | `Origin_Phylogenetic_Block_State` | `parent::child-O` |

Downstream readers (Scripts 003, 004, 005) that consumed the old column name will be updated to consume the new names.

---

## 7. Summary

GIGANTIC distinguishes **phylogenetic blocks** (parent-to-child edges of a species tree structure, naming a tree-structural fact) from **phylogenetic block-states** (a block paired with a specific feature's state on that block, naming a feature-specific fact). The five block-states — **A** (Inherited Absence), **O** (Origin), **P** (Inherited Presence), **L** (Loss), **X** (Inherited Loss) — refine classical Dollo into a vocabulary that separates pre-origin absence from post-loss absence, and that names every parent-child presence pattern exactly once. Block-states split into **phylogenetic event blocks** (O, L, where a feature's state changes between the parent and child endpoints) and **phylogenetic inheritance blocks** (A, P, X, where the state is the same at both endpoints). A single identifier form — `parent_clade_id_name::child_clade_id_name-LETTER` — encodes both the tree anchor and the feature's state in one compact, parseable string, and carries the full vocabulary without needing special-case shorthands.

---

## Appendix A. Relationship to Existing Terms

| Existing term | Relation to GIGANTIC block / block-state |
|---|---|
| Branch | Informal synonym for a block; ambiguous about whether parent and child endpoints are included. GIGANTIC replaces with the precise term. |
| Lineage | Connotes temporal continuity through a region of the tree; overlaps with block but emphasizes process rather than structure. |
| Stem / stem lineage | Paleontological term embedded in a crown/stem-group framework that GIGANTIC is not using. In a fully resolved binary tree without fossil taxa, a stem lineage coincides with a single block. |
| Edge (graph theory) | A phylogenetic block is a graph-theoretic edge plus the biological and phylogenetic layers that come with being on a species tree. |
| Origin event, Loss event | Retained in GIGANTIC as synonyms for event blocks in states O and L respectively. |
| Conservation | Retained as the informal term for Inherited Presence (state P). |
| Continued absence | In the earlier TEMPLATE_03 three-event model this term collapsed states A and X; in the five-state vocabulary the two are separated. |

## Appendix B. Notation Reference

| Object | Identifier form | Example |
|---|---|---|
| Clade | `CXXX_Clade_Name` | `C082_Metazoa` |
| Phylogenetic block | `parent_clade::child_clade` | `C069_Holozoa::C082_Metazoa` |
| Phylogenetic block-state (general) | `parent_clade::child_clade-LETTER` | `C069_Holozoa::C082_Metazoa-O` |
| Origin event block | `parent_clade::child_clade-O` | `C069_Holozoa::C082_Metazoa-O` |
| Loss event block | `parent_clade::child_clade-L` | `C082_Metazoa::C030_Placozoa-L` |
| Inherited Absence block | `parent_clade::child_clade-A` | `C068_Basal::C069_Holomycota-A` |
| Inherited Presence block | `parent_clade::child_clade-P` | `C082_Metazoa::C010_Bilateria-P` |
| Inherited Loss block | `parent_clade::child_clade-X` | `C030_Placozoa::(descendant)-X` |

## Appendix C. State Life-Cycle Diagram

For a given feature on a given species tree structure, the block-state sequence along any root-to-tip path follows one of a few patterns. The five states form a directed automaton: **A** leads only to **A** or **O**; **O** leads only to **P** or **L**; **P** leads only to **P** or **L**; **L** leads only to **X**; **X** leads only to **X**. Features cannot re-originate without a second origin event (which would appear as a separate **O** block, and in GIGANTIC's Dollo-parsimonious framing would not be assigned to the same feature).

```
  A  →  A  →  A  →  O  →  P  →  P  →  P  →  (tip)         persistent-presence path
  A  →  A  →  A  →  O  →  P  →  L  →  X  →  X  →  (tip)    present-then-lost path
  A  →  A  →  A  →  A  →  A  →  A  →  A  →  (tip)          feature never originates in this lineage
```
