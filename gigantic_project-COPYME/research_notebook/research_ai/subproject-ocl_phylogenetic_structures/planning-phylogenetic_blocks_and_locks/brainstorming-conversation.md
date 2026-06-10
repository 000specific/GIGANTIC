# Brainstorming Conversation — Phylogenetic Blocks and Locks / Block-States

**Participants**: Eric Edsinger (user), Claude Code (assistant, Opus 4.6 1M-context)
**Date**: 2026 April 14
**Scope**: Verbatim conversation from singleton-orthogroup accounting through the naming of phylogenetic blocks, block-states, and the five-state vocabulary (A/O/P/L/X), up to the point of first whitepaper drafting.

---

## User

Ok - how are singleton species orthogroups handled in blocks and paths throughout the scripts

## Assistant

### Singletons (single-species orthogroups) in blocks and paths

**Origin assignment (Option A)**: for a singleton containing species `S`, origin = `S`'s leaf `clade_id_name` (e.g. `C048_Schmidtea_mediterranea`). This is the degenerate MRCA — intersecting one species' path with itself returns its full path; the deepest node is the leaf.

**Per script:**

**Script 001** — Both representations include singletons:
- The leaf appears as a row (or the tail) of `parent_child_table` and as the last element of its own path in `phylogenetic_paths`.
- Terminal **self-loop** rows (`parent_clade_id_name == child_clade_id_name` at leaves) exist as structural placeholders.

**Script 002 — determine_origins:**
- Singleton → Option A code path: origin looked up in `clade_names___clade_id_names`, skipped if species absent from this structure's mapping.
- `Origin_Clade_Phylogenetic_Block`: the block where the leaf is the child (`<parent_internal>::<leaf>`), not the self-loop.
- `Origin_Clade_Phylogenetic_Path`: the leaf's full root-to-leaf path.

**Script 003 — quantify_conservation_loss:**
- Self-loops **excluded** from the transition set (`if parent == child: continue`).
- A singleton's origin is the leaf itself. The leaf has no children in the filtered block set → no parent→child transitions downstream of origin exist.
- Result: `total_inherited_transitions = 0` → all rates fall into the explicit zero-division guard (`= 0.0`). Singletons contribute **zero events** to conservation/loss/continued-absence.
- Ancestor clades on the leaf's path do NOT count the singleton as inherited (origin is the leaf, not an ancestor — no ancestor has `origin_clade_id_name` in its path).

**Script 004 — comprehensive_ocl_analysis:**
- Per-clade presence: only the leaf clade has the singleton present (descendant set = {leaf}; orthogroup species = {leaf} → intersection non-empty).
- Origins-summary per clade: singletons count toward the **leaf clade's `origins_count`**.
- Per-species summary: `species_specific` = count of orthogroups whose origin equals that species' leaf `clade_id_name` → singletons drive this column.

**Script 005 — validate_results:**
- CHECK 6: origin `C048_Schmidtea_mediterranea` ∈ path `[C068_Basal, ..., C048_Schmidtea_mediterranea]` → passes trivially.
- Cross-script counts: singletons present in origin/path totals but absent from block-transition totals (consistent with Script 003's zero contribution).

**Net effect**: singletons are represented as real biological entities in origins/paths/per-clade/per-species views, but are **invisible to conservation/loss metrics** — correctly, since they have no evolutionary transitions below their origin in the observed data.

---

## User

This is what I want to get into:

Ancestor clades on the leaf's path do NOT count the singleton as inherited (origin is the leaf, not an ancestor — no ancestor has origin_clade_id_name in its path).

if there are sibling leaf/tip species_A and speciesB - and they have a MRCA node connecting them. Then orthogroups containing only species_A originate on the block going from the MRCA to species_A leatf/tip but not including the MRCA.

## Assistant

Yes — exactly right. Let me confirm and map it to the code.

### Origin = edge, shorthand = child node

An orthogroup's origin is biologically an **edge (block)**, not a point. Placing it at a node is a naming convention: GIGANTIC uses the **child endpoint** of the origin block as the origin identifier.

**Sibling-leaf singleton example:**
```
        MRCA (C090)
        /    \
   speciesA   speciesB
   (C001)     (C002)
```
Orthogroup present only in speciesA:
- **Origin block (biological truth)**: `C090_MRCA :: C001_speciesA` — the edge, MRCA excluded.
- **Origin node (code shorthand)**: `C001_speciesA` (child endpoint of that edge).

The MRCA is excluded because speciesB lacks the orthogroup — inferring presence at MRCA would require a loss in speciesB (2 events vs. 1).

### How the code realizes this

**Script 002:**
- Origin `clade_id_name` = `C001_speciesA` (leaf, via Option A).
- `Origin_Clade_Phylogenetic_Block` = `C090_MRCA::C001_speciesA` — the block lookup returns the edge **into** the origin node. So the origin block is emitted correctly.

**Script 003's "inherited at clade C iff origin ∈ C.path" test:**
- speciesA's path = `[..., C090_MRCA, C001_speciesA]` → contains origin ✓ → speciesA inherits.
- MRCA's path = `[..., C090_MRCA]` → does NOT contain `C001_speciesA` ✗ → MRCA does NOT inherit.
- speciesB's path = `[..., C090_MRCA, C002_speciesB]` → does NOT contain `C001_speciesA` ✗ → speciesB does NOT inherit.

This is precisely the sibling asymmetry you described, enforced by the path-membership test.

**Transition accounting in Script 003:**
When the block `C090_MRCA::C001_speciesA` is evaluated for this orthogroup:
- `parent_inherited` check: is orthogroup in MRCA's inherited set? **No** (MRCA doesn't have the leaf in its path).
- Loop `continue` — the origin block itself is **never counted** as conservation or loss.

This generalizes: **for every orthogroup, the block leading into its origin node is excluded from its transition tally.** That's correct — there is no prior state to compare "parent has" vs. "child has" on the edge where the gene first appears.

### The node-as-edge-shorthand is consistent across origins

Same logic for a multi-species orthogroup originating at internal clade `C082_Metazoa`:
- Origin node: `C082_Metazoa`
- Origin block: `<parent>::C082_Metazoa` (the edge into Metazoa)
- Parent of Metazoa does NOT inherit → parent::Metazoa block not counted.
- Metazoa DOES inherit → Metazoa::children blocks ARE counted.

**So the origin node in the code is really "the child endpoint of the origin block," and the three invariants hold uniformly for singletons and multi-species orthogroups:**
1. The origin node has the orthogroup inherited.
2. The origin node's parent does not.
3. The block into the origin node contributes zero transitions.

---

## User

ok - that is great to hear in such clear detail. But then how do we define phylogenetic blocks? On the one hand it is tempting to make them simply parent-to-child blocks - as this is a critical relationship in the tree. However, from a origins standpoint we want to consider the block as everything in parent-to-child minus the parent.

Should there be another term for this distinct thing?

## Assistant

Yes — you've hit a real distinction that deserves its own name. This is a classical phylogenetics concept.

### The two things you're distinguishing

| Framing | Extent | Use case |
|---|---|---|
| **Edge as a bidirectional relationship** (`Parent :: Child`) | Both endpoints participate equally. Comparing states. | Conservation/loss scoring — inherently needs **both** parent state and child state. |
| **Edge + child, excluding parent** | Half-open "downstream zone." Assigning provenance. | Where an origin can live (gene arose somewhere along this zone, we localize it to the terminus). |

### The established term is "stem"

Phylogenetics and paleontology already have a term for exactly your "edge minus parent" concept: **stem** (or **stem lineage** / **stem branch**).

- **Stem of clade C** = the branch leading to C, terminating at C, excluding C's parent.
- **Crown of C** = C and everything inside it.
- **Stem + crown** = the total group rooted at C.

This is the standard literature usage (e.g., "the stem lineage of Metazoa," "crown Bilateria"). It already carries the exact semantics you want:
- The stem of `C001_speciesA` = the edge from MRCA down to speciesA, minus MRCA.
- An orthogroup "originating on the stem of C" means it arose somewhere along that edge — we don't know exactly where, so we name it by the stem's terminus (C).

### Proposed GIGANTIC mapping

| GIGANTIC term | Definition | Primary user |
|---|---|---|
| **Phylogenetic block** | Parent→child edge as a directed relationship (`Parent_Clade_ID_Name :: Child_Clade_ID_Name`). Both endpoints participate. | Script 003/004 transition scoring (conservation/loss/continued-absence). |
| **Phylogenetic stem** | The edge + child node, excluding the parent. Named by its terminus (the child `clade_id_name`). The zone where an origin lives. | Script 002 origin assignment; the "origin clade" concept. |

**They refer to the same tree edge, viewed differently.** The block `MRCA::speciesA` and the stem of `speciesA` are the same piece of tree — but block framing puts both endpoints in play (scoring), while stem framing treats the parent as "not yet" (origin-capable zone).

### What this would clarify in the code

The current field **`Origin_Clade_Phylogenetic_Block`** is slightly misleading by this framing — it names the block (relational) when what we really mean is the stem (origin-zone). More honest name:
- `Origin_Stem_Clade_ID_Name` = the terminus of the stem = the origin node itself (`C001_speciesA` or `C082_Metazoa`), OR
- `Origin_Phylogenetic_Stem` = the stem named as `Parent::Child` but explicitly labeled as a stem, not a transition block.

And the three invariants I listed earlier can be restated cleanly:
1. An orthogroup originates **on the stem** of its origin clade.
2. That stem corresponds to the block **entering** the origin clade — and that block is **never** scored as a transition for that orthogroup.
3. Blocks **leaving** the origin clade (origin's children) are the first scored transitions.

### Recommendation

Adopt **stem** as a first-class GIGANTIC term alongside block, at the same Rule tier as Rules 1–6. Something like:

> **Rule 7: Block vs. Stem**
> A **phylogenetic block** is a parent→child edge treated as a directed relationship between both endpoints (used for transition scoring). A **phylogenetic stem** is the same edge treated as "edge + child, parent excluded" (used for origin localization). Same tree edge, different semantic framing.

If you agree, I'd:
1. Add Rule 7 to both CLAUDE.md files and `AI_GUIDE-project.md`.
2. Update trees_species + orthogroups_X_ocl READMEs/AI_GUIDEs.
3. Rename `Origin_Clade_Phylogenetic_Block` → `Origin_Phylogenetic_Stem` (or similar) in Script 002 output and propagate through 003/004/005.

Want me to draft Rule 7 for review first?

---

## User

is stem a commonly used phylogenetic term already - does it match this definition if so?

## Assistant

Honest answer: **partially.** Let me be precise, because I may have oversold it.

### What "stem" actually means in the literature

**Stem lineage / stem branch** is a real, established term, but it carries specific baggage from paleontology/systematics (Jefferies, Hennig):

- **Crown group** of C = last common ancestor of all *extant* members of C + all its descendants.
- **Stem group** of C = extinct lineages more closely related to crown-C than to its sister group, but outside the crown.
- **Stem lineage** of C = the single lineage running from the divergence with C's sister down to the crown-C MRCA.
- **Total group** = crown + stem.

In a fully resolved binary species tree with only extant leaves (GIGANTIC's case), the stem lineage of clade C does reduce to "the branch from C's parent to C, excluding the parent." So the definitions **do** coincide in our setting — but the term's literature usage lives inside a richer framework (crown-vs-stem taxonomy, often with fossils) that GIGANTIC isn't engaging with.

### The more common term is actually "branch"

In origin-assignment contexts — Dollo mapping, gene-family emergence, trait evolution — the literature overwhelmingly uses **branch**:
- "The gene arose on the Metazoa branch."
- "Character originated on branch *X*."
- "Long-branch attraction," "branch-specific rates."

"Branch" is generic, widely understood, and directionally implicit (a branch leads to its terminal clade). It matches your "edge + terminus, parent excluded" reading without the crown/stem connotations.

### Honest comparison for GIGANTIC

| Term | Match to your concept | Caveat |
|---|---|---|
| **stem** / **stem lineage** | Good in a resolved binary tree | Imports crown/stem-group framework that GIGANTIC doesn't use; may mislead paleontology-literate readers. |
| **branch** | Equally good, simpler | Slightly generic — but that's fine; "phylogenetic branch" is standard. |
| **lineage** | Similar | Sometimes implies a temporal continuum rather than a discrete edge. |

### Revised recommendation

I'd lean toward **"phylogenetic branch"** over "stem" for GIGANTIC, because:
1. It's the term the origins/Dollo literature actually uses.
2. It avoids the crown/stem baggage.
3. It pairs cleanly with "phylogenetic block" as a different framing of the same underlying tree edge: **block = edge as relation between both endpoints; branch = edge as descent-carrying lineage terminating at the child.**

If you like the framing but want a term less ambiguous than "branch," **"phylogenetic descent-edge"** or **"child-rooted edge"** are less standard but more self-documenting.

Want me to draft Rule 7 with "branch" instead of "stem," and note both terms in the definition for readers familiar with either literature?

---

## User

branch is something not restrict to parent-to-child depth on the tree.

Stem is complicated by stem groups - we could clarify by parent-child block and parent-child stem - but maybe something that avoids plant terminology - because then what about roots and leaves etc.

I prefer tip over leaf for example. And while sibling and sister have distinct means in phylogenetics - I prefer sibling, parent, child as more generalized. But we should probably be careful and accurate and use sibling and sister relationship on a tree in accordance with the literature.

SO

I came up with block as parent-to-child on the tree - can we find a term that is outside plant analogy / not commonly used in evolutionary biology/phylogenetics for parent-to-child without the child. Its such an important feature for considering the origins of features mapped onto trees, I feel like there must be a definition already - or we should create one in our specific context and highlight its importance as a term

## Assistant

Short honest answer: **there is no widely adopted, unambiguous standard term for this exact concept.** The literature papers over it. Your instinct that GIGANTIC should coin one is correct.

### Why it's gone unnamed

Most phylogenetic work that needs this concept either (a) calls it "branch" and accepts the ambiguity about endpoints, or (b) works with continuous branch-length measures where endpoint inclusion is irrelevant. The asymmetry between parent and child only *matters operationally* when you're explicitly placing origins on a tree — which is exactly GIGANTIC's OCL core business. So the gap is real and it's worth filling.

### Criteria you've implied

1. Non-botanical (no stem / branch / root / leaf / crown / trunk).
2. Not overloaded with an existing evolutionary-biology meaning.
3. Carries the "directed, terminating at child, parent excluded" semantics.
4. Pairs cleanly alongside your coinage "phylogenetic block."
5. Dignified enough to stand as a first-class Rule in GIGANTIC.

### Candidates (honest tradeoffs)

| Term | Pros | Cons |
|---|---|---|
| **phylogenetic advent** | Latin *ad-venire* = "to come to / arrive." Evokes "coming into being" — exactly the origin semantics. Not overloaded in biology. Dignified. | Slight theological connotation (Advent). Unfamiliar in phylo — needs definition on first use. |
| **phylogenetic onset** | Temporal, clean, common-English. | Medical connotation (disease onset). Less directional. |
| **phylogenetic arc** | Graph-theoretic term for a *directed* edge. Formally precise. | Too abstract; readers may default to "arc of time" or geometric arc. |
| **phylogenetic tract** | Non-botanical, underused in biology, neutral. | Generic; doesn't carry origin semantics on its own. |
| **phylogenetic inception** | "Moment/place of beginning." Origin-oriented. | Slightly pretentious; "inception" is now pop-culturally loaded. |
| **origin-block** (sub-type of block) | Pairs with your "block." Self-documenting. | Overloads "block" with two definitions; risks the exact confusion we're trying to avoid. |

### My recommendation: **phylogenetic advent**

An **advent** in GIGANTIC would be:
> The parent→child edge of a species tree, treated as the half-open zone extending *from* the parent (excluded) *to and including* the child. Named by its child terminus. The locus where a novel feature can originate: features present at the advent's child but absent at its parent originate somewhere along it.

Paired with block:
> **Block** is the same tree edge framed as a bidirectional parent↔child relationship (used for conservation/loss transition scoring, where both endpoints must be compared).
>
> **Advent** is the same tree edge framed as a half-open origin zone (used when localizing where a feature first arose on the tree).

Same edge, two framings with distinct operational purposes. This is the same pattern as block vs. stem in the standard literature, but with fresh non-botanical vocabulary unique to GIGANTIC.

### If you adopt it

I'd add **Rule 7: Block vs. Advent** to CLAUDE.md + `AI_GUIDE-project.md`, propagate through trees_species + orthogroups_X_ocl docs, and rename `Origin_Clade_Phylogenetic_Block` → `Origin_Phylogenetic_Advent` in Script 002 output (with 003/004/005 readers following).

Want me to draft Rule 7 for review?

---

## User

just toying around with ideas:

phylogenetic chunk is a parent-to-child segment of a tree
phylogenetic hunk is a parent-to-child segment of a tree without the parent

clever? childish?

## Assistant

Honest answer: **clever rhyme, but leans childish for a published framework.**

**Problems:**

1. **The rhyme doesn't encode the distinction.** "Chunk vs. hunk" gives you no semantic hook for which includes the parent. Users will flip a coin every time they recall which is which. Compare to "block vs. advent" where *advent* literally means "coming to / arrival" — the word itself tells you it's the origin-zone.

2. **"Hunk" carries colloquial baggage.** Slang meaning (attractive person), informal register ("hunk of cheese"). In a GIGANTIC paper methods section — "the orthogroup originated on the phylogenetic hunk leading to Metazoa" — it'll draw a smirk, not a nod. Leonid reading it in a manuscript might wince.

3. **Dignity gap.** Your other GIGANTIC Rules (1–6) use precise, weighty vocabulary: *phylogenetic, evolutionary, structure, topology, hierarchy, origin*. Chunk/hunk breaks tone. A reader scanning CLAUDE.md hits Rule 7 and downshifts a register.

**What's right about the instinct:**
- Fresh, non-botanical, non-overloaded. ✓
- Memorable. ✓
- Coined specifically for GIGANTIC. ✓

**Synthesis — keep the spirit, upgrade the register:**

If you like the "short concrete noun" vibe over Latinate abstractions, better candidates are:

| Pair | Comment |
|---|---|
| **block** / **slab** | Slab = a solid piece; could carry "partial block" meaning. Physical but not botanical. |
| **block** / **shard** | Shard = a broken-off piece. Encodes "part of a block." Slightly evocative. |
| **block** / **wedge** | Wedge terminates at a point — natural match for "terminating at child." |
| **block** / **run** | Genealogical/lineage feel without botany. "The run leading to Metazoa." |

Still, I'd stand by **advent** as the strongest — it's the only candidate where the word itself means "where the new thing arrives," which IS what the concept is for. The others are geometric; advent is semantic.

**TL;DR**: chunk/hunk is fun but won't age well. If you want short+concrete, try **block / wedge**. If you want self-documenting, **block / advent**.

---

## User

I think you missed the logic - chunk to hunk you lose one of the two endpoints in the word

## Assistant

You're right, I was wrong about that. The mnemonic is self-documenting in exactly the way I claimed it wasn't:

**c**hunk → hunk: drop the **c** = drop the parent endpoint.

That's genuinely clever. The letter loss encodes the endpoint loss. I missed it entirely and dismissed the pair on a false premise.

### Reassessing with the mnemonic in view

**Chunk / hunk now has:**
- Fresh, non-botanical ✓
- Not overloaded in phylogenetics ✓
- Self-documenting via letter loss ✓ (the thing I got wrong)
- Memorable (rhyme + visual) ✓
- Coined specifically for GIGANTIC ✓

This moves chunk/hunk from "clever but weak" to "genuinely well-designed." The mnemonic is doing real work.

### What remains honest to flag

One concern survives: **register**. "The orthogroup originated on the phylogenetic hunk leading to Metazoa" still reads informally to a reader expecting a Latinate-heavy methods section. Whether that's a problem depends on how much you want GIGANTIC's voice to match conventional journal prose vs. be distinctively GIGANTIC.

Looking at your existing Rule 1–6 vocabulary (phylogenetic, evolutionary, structure, topology, clade_id_name) — it's Latinate and formal. Chunk/hunk would be a tone shift. Not wrong, just a choice you'd be making explicitly.

### Three ways to handle the register question

1. **Keep chunk/hunk** — embrace the tonal shift as GIGANTIC's voice. The mnemonic pays for itself. In-house tools can afford personality.

2. **Dignify the mnemonic pattern** — find another letter-loss pair with more formal register. Honestly, most pairs like this don't work as well. *Chunk/hunk* is unusually clean.

3. **Use chunk/hunk internally, translate for publication** — CLAUDE.md and code use chunk/hunk; papers use "phylogenetic block" / "origin-assigning edge" or similar. Adds friction.

I'd now nudge toward option 1. The mnemonic is strong enough that the tonal cost is worth paying, especially in an AI-native framework where self-documenting vocabulary is a feature, not a bug. Worth the bit of personality.

Want me to draft Rule 7 with chunk/hunk?

---

## User

I think chunk and hunk have too much baggage to be taken seriously - but I really like the loss of one of the endpoints in the word - ideally on the left side to replicate parent-to-child

## Assistant

This constraint is genuinely hard. Letter-drop word pairs on the left that are (a) both real English, (b) both dignified, (c) neither biologically loaded, (d) semantically matching the concept — that combination is rare. Chunk/hunk is a tight rhyme specifically because it's a tight rhyme; most other candidates fail one of the criteria. Let me offer the few that survive:

### Candidates that pass your constraints

**bridge / ridge**
- *Bridge* = structure explicitly spanning two endpoints — natural fit for "block as bidirectional parent↔child relationship."
- *Ridge* = an asymmetric line/crest — can carry the directional "leads to a summit" flavor for child-terminated half-edge.
- Drop `b` → ridge. Left-letter mnemonic intact.
- Dignified, non-botanical, not phylogenetically overloaded.
- Weakness: ridge's asymmetry is topographic (up-slope vs down-slope), not endpoint-exclusion — the mnemonic has to carry more weight than the semantics.

**avenue / venue**
- *Avenue* = thoroughfare connecting places — bidirectional, relational.
- *Venue* = the site where an event occurs — fits "where origins happen."
- Drop `a` → venue. `a` = ancestor, nice symbolic bonus.
- Dignified, non-biological.
- Weakness: slightly urban-flavored; "phylogenetic avenue" is unusual imagery.

**passage / assage**
- *Assage* isn't a word. Dead.

**stretch / tretch**, **span / pan**, **tract / ract**
- Either the short form isn't a word, or the word exists but semantics collapse (pan → cooking vessel).

### Honest assessment

- **bridge / ridge** is my top pick. Dignified, widely understood, left-letter-drop, not phylogenetically loaded. The semantic match isn't as tight as chunk/hunk (where "hunk of" naturally reads as "piece of"), but it's defensible: a bridge connects two points; a ridge runs toward a summit.

- **avenue / venue** is a close second — the semantics are actually *better* (venue = where-it-happens = where-origin-is), but the imagery is more metropolitan than geological.

- Chunk/hunk remains the tightest mnemonic we've surfaced. If you definitely want to drop it, bridge/ridge is the most conservative replacement.

### One more angle worth considering

You could invert the naming burden: keep **block** and coin a single non-paired term for the half-open entity — something short, dignified, and intentionally GIGANTIC-specific, where the fact that it has no matching "longer form" is itself a signal that it's a distinct primitive. Candidates: **advent**, **onset**, **origin-zone**, **terminus-edge**. These give up the letter-drop mnemonic but sidestep the rare-pair problem entirely.

Which trade-off do you prefer: a clever-but-imperfect word pair (bridge/ridge, avenue/venue), or a single coined term that doesn't try to pair with block at all?

---

## User

I mean the difference between parent-to-child and parent-to-child without parent is literally a single point - in mathmatics a half-open segment versus a segment

## Assistant

You've just found the actual right answer. The distinction is a topological one and has a precise mathematical name: **half-open**.

- Block as both-endpoints = closed segment `[parent, child]`
- Block minus parent = half-open segment `(parent, child]`

The difference is exactly one point (the parent), measure zero, but structurally meaningful — which is exactly the situation we're in.

### Clean naming using standard math

| Term | Meaning |
|---|---|
| **(closed) phylogenetic block** | `[parent, child]` — both endpoints. Default "block." Used for conservation/loss scoring (both states compared). |
| **half-open phylogenetic block** | `(parent, child]` — child-closed, parent-open. Used for origin localization (the parent doesn't yet have the feature). |

Or the snappier pair, using `(half-block` as a shorthand for the half-open case:

| Term | Meaning |
|---|---|
| **block** | closed `[parent, child]` |
| **half-block** | half-open `(parent, child]` |

### Why this actually resolves the whole discussion

1. **No neologism needed.** "Half-open" is textbook topology — every mathematically literate reader knows it on first encounter.
2. **No retrofit.** The meaning *is* "the edge minus one endpoint." That's literally what half-open means.
3. **Non-botanical, non-phylogenetically-overloaded, dignified.** ✓ ✓ ✓
4. **Honest about the asymmetry.** The parent-open side is where the feature doesn't yet exist; the child-closed side is where it does. That's the biology, mapped onto the topology.
5. **Mnemonic is structural, not letter-based.** Closed vs. half-open is a real distinction, not a rhyme.
6. **Generalizes.** If someone ever needs the symmetric variant `(parent, child)` (fully open) or `[parent, child)` (parent-closed, child-open — rarely), the same vocabulary extends naturally.

### How it reads in practice

> "Orthogroup OG0000001 originates on the half-open block `C090_MRCA :: C001_speciesA` — the parent-open side excludes MRCA (absent in speciesB), the child-closed side includes speciesA (where the feature is locked in)."

> "For the block `C090_MRCA :: C001_speciesA`, the half-open form is the origin-capable zone; the closed form is the conservation/loss transition."

### Rule 7 draft

> **Rule 7: Closed vs. Half-Open Phylogenetic Block**
> A **phylogenetic block** is a parent→child edge on a species tree structure, written `Parent_Clade_ID_Name :: Child_Clade_ID_Name`. By default "block" refers to the **closed block** `[parent, child]` — both endpoints included — which is the atomic unit of conservation/loss transition scoring (parent state vs. child state are both evaluated).
>
> A **half-open block** `(parent, child]` is the same edge with the parent endpoint excluded. It is the origin-capable zone: a feature (orthogroup, annotation, trait) originates on a half-open block, named by its child terminus, because the parent does not yet have the feature (one more event than origination would otherwise be required).
>
> Three invariants:
> 1. A feature originates on a half-open block, named by its child `clade_id_name`.
> 2. The half-open block of the origin corresponds to the closed block entering the origin clade — which is **never scored as a transition** for that feature (no prior state to compare).
> 3. Closed blocks leaving the origin clade are the first scored transitions.

Want me to codify this as Rule 7 in both CLAUDE.md files and propagate through the `AI_GUIDE-project.md`, trees_species, and orthogroups_X_ocl docs?

---

## User

NO - you are being to jumpy and reactive. No pressure here - lets keep exploring! Its ok to be creative and silly and see what bubbles up.

I actually really like your thinking around lock for block and lock - the gene originates in the metazoan lock - a lock is literally a segment (of contained water) - and lock implies things are secure - where know it arose in exactly this region of the tree.

but relax and lets keep playing around with things - I also like your emphasis on the dignity gap - precise, weighty vocabulary is very gigantic and I like that feel for it. so block/lock >> chunk/hunk

but lets keep thinking outloud

## Assistant

Fair. Let me actually keep thinking with you instead of trying to close it out.

### On lock defending itself

Sitting with it longer, the lock imagery may be stronger than I credited:

- A **canal lock** is literally a contained water segment between two gates — a physical half-open zone. When the upstream gate closes and the downstream opens, a vessel transitions *through* it to a new level. That's a surprisingly clean map onto "the zone where a feature transitions from absent to present."
- **Locks in** — the feature originates here and, by Dollo-ish reasoning, stays present along the child-ward direction. Locked in = committed to the descendant lineage.
- "The orthogroup is locked in at the Metazoa lock" reads naturally. No hedging.

Also: technical vocabulary is *coined*. "Phylogenetic block" isn't a retrofit of standard English "block" — it's GIGANTIC defining a term. Defining "phylogenetic lock" as "the half-open version of a phylogenetic block" is the same move. The canal-lock and padlock senses don't need to literally mean half-open segment — they just need to be evocative enough that the defined meaning sticks. Both senses do that work.

### Letter-drop survey, honestly reported

I ran through the alphabet adding left letters to short English words. Pairs that survive all the filters (both real, dignified, non-botanical, not overloaded, meaningful):

| Pair | Drop | Notes |
|---|---|---|
| **block / lock** | b | Your pick. Strong on all axes once we own the GIGANTIC coinage. |
| **bridge / ridge** | b | Structural, but ridge is topographic not zone-like. |
| **knave / nave** | k | Unexpectedly strong — nave = the main body of a cathedral leading toward the altar, inherently directional. But knave means rogue/jack, sullied. |
| **plane / lane** | p | Lane carries "leads to" directionality for the half-open zone. Plane is geometric, weak for block. |
| **haven / aven** | h | Haven = refuge (good), aven = vertical cave shaft (obscure geology term). Too obscure for aven. |
| **dwell / well** | d | Well = source of welling-up. Dwell = to reside. Semantically interesting but dwell-as-noun is awkward. |

The rest either fail "both real" (ract, tage, rcade), fail "dignified" (hunk, rump, gimp), or the short word carries the wrong baggage (race, rain, read, rust, hare, lice).

### One curious observation

The short words that semantically *want* the "zone-of-origin" meaning — **site, niche, nook, cove, den, nest, haven, port, seat, well** — almost none accept a meaningful left-letter addition that yields a real "block-like" relational long word. The vocabulary for "place where something lives" doesn't pair with the vocabulary for "relationship between two points" via simple morphology. That's probably why no one else has coined this pair — the linguistic raw material isn't there.

Which means the path forward is basically:
1. **Own the block/lock coinage** — accept that lock is defined by GIGANTIC and let the canal/padlock senses do memorability work.
2. **Abandon letter-drop and pair block with a semantically native term** (advent, or maybe something else we haven't surfaced yet).
3. **Keep playing** and see if a left-field candidate emerges.

### Playing further

A few more curiosities that bubbled up:

- **niche / iche** — iche is nothing. But *what if* a GIGANTIC coinage were **biniche** or **coniche**? Nope, too contrived.
- **vault / ault** — a vault is a covered architectural arch OR a leap. Semi-directional. Nothing drops into "ault."
- **trellis / rellis** — trellis is botanical. Fail.
- **channel / hannel** — channel is nice for block (directional passage). No hannel.
- **corridor / orridor** — same issue.

There's one weirder move worth noting: some languages compound their directional-vocabulary differently. German has *Gang* (passage) and *Schleuse* (lock), Latin has *aditus* (approach) and *limen* (threshold). If GIGANTIC wanted to go full coinage, a Latinate pair like **transitus / limen** ("the transit, the threshold") could work — the threshold is literally the half-open entry. Too foreign? Maybe. But dignified as anything.

No pressure to decide. Where does your gut go when you sit with it?

---

## User

also - I do NOT like advent - too religious

and given the different of a single point - I think the two terms should be clearly related in a visual or at least definitional sense

## Assistant

Noted — advent gone, and the religious ring is fair (Advent calendar, Advent of Christ). And the visual/definitional-relation criterion actually sharpens things a lot.

### Two ways to satisfy "clearly related"

**Visual relation** (spelling twins):

| Pair | Shared letters | Drop | Notes |
|---|---|---|---|
| **block / lock** | 4 of 5 (`_lock`) | b | Rhymes, same rhythm, canal-lock imagery. Strongest visual in my survey. |
| **trail / rail** | 4 of 5 (`_rail`) | t | Rhymes. Trail = connecting path; rail = directional line. Weaker native semantics than lock but visually tight. |
| **bridge / ridge** | 5 of 6 (`_ridge`) | b | Visual tight but ridge is topographic, not origin-zone. |

**Definitional relation** (morphological derivation from "block" itself):

| Pair | Form | Notes |
|---|---|---|
| **block / half-block** | English prefix | Self-documenting ("literally half of a block"). Plain but precise. "Half-block" doesn't specify which half — ambiguity may bother you. |
| **block / semi-block** | Latinate prefix | Slightly more dignified than half-. Same ambiguity. |
| **block / hemi-block** | Greek prefix | Scientific register. "Hemi" pairs well with structural anatomy (hemisphere, hemiparesis). Most dignified of the three. |
| **block / open-block** | Math-native | Points at the half-open topology directly. "Open" could confuse (open at which end?). |
| **block / post-block** | Latin "after" | "Post-parent zone" — after the parent endpoint. Directionally clear. |
| **block / tip-block** | Tip-ward | Names the retained side (the tip/child). Unambiguous. |

### The tradeoff

**Visual (block/lock)**: punchy pair, strong visual tie, but the semantic pull for "lock = half-open zone" is a defined GIGANTIC meaning rather than native English.

**Definitional (block/half-block, block/tip-block, block/hemi-block)**: the meaning is transparent — reader sees it and gets it — but the pair is less memorable. "Hemi-block" won't stick in your ear the way "block and lock" will.

### A third option — hybrid

Use a morphological derivation that also happens to carry phonetic weight:

- **block / blocket** — a diminutive, "small block." Doesn't carry half-open meaning.
- **block / blockus** — invented Latinate. Pretentious.
- **block / unblock** — verb, wrong meaning.
- **block / bloc** — drop `k`. Bloc = coalition. Doesn't fit.

None of these beat the two main paths.

### What I'm genuinely stuck on

The visual+native-semantic version of this pair may just not exist in English. You either accept a defined meaning (block/lock with GIGANTIC's coinage doing the work), or you use transparent morphology (block/hemi-block) at the cost of some zing.

A middle path I hadn't fully weighed: **hemi-block** actually grows on me the more I sit with it. It's:
- Visually related to block (contains "block")
- Definitionally transparent (hemi = half, from Greek)
- Scientifically registered (hemiplegia, hemisphere, hemichordate — Greek hemi- is native to biology/medicine)
- Unambiguous about its relationship to block
- No religious, botanical, or over-casual baggage

"The feature originates on the hemi-block leading to Metazoa." It reads clinical and precise. Not as punchy as block/lock, but trades punch for transparency.

Where's your ear pulling — toward block/lock's phonetic tightness, or toward hemi-block's definitional cleanness?

---

## User

the trouble with hemi is the loss is too large.

the two enties are nearly identical - they differ by only a single ancestral point

## Assistant

That's a sharp reframe. You're saying the naming should reflect the *measure* of the difference — which is infinitesimal, not half.

That criticism kills hemi-/semi-/half- immediately. Those prefixes advertise "50% loss" when the actual loss is one point on a continuum. Linguistic false advertising.

### This criterion actually re-elevates block/lock

Look at what block → lock does visually:

```
block
 lock
```

You lose **one letter out of five** (20% by glyph count, which is already overstated vs. the true measure-zero difference — but it's the *smallest* letter-level change English gives you while still yielding two real words). The shared `lock` substring visually declares "these are the same thing" and the dropped `b` is the infinitesimal parental endpoint peeled off.

Compare to hemi-block:
```
block
hemi-block
```
The visible transformation adds FOUR letters and a hyphen, screaming "major modification." It lies about the magnitude of the change.

So the user's consistent criterion (visual proximity reflecting conceptual proximity) actually points *back* to block/lock — and against the hemi/semi family.

### What other options preserve near-identity visually?

| Option | Visual change | Honest? |
|---|---|---|
| **block / lock** | drop `b` (left) | Yes — minimal, left-side, parent-shaped |
| **block / bloc** | drop `k` (right) | Wrong side (would mean losing the child) |
| **block / blok** | swap one letter | No, blok isn't a word |
| **block / block°** | add a degree mark | Minimal visual but typographic, not a word |
| **block / block′** (block-prime) | add prime | Math-notation feel, not English |
| **block / block\*** | add asterisk | Footnote-feel, not a name |
| **block / sub-block** | add prefix | Prefix suggests containment relationship |
| **block / child-block** | compound | No letter loss but adds 6 chars + hyphen |

Nothing beats block/lock on this specific criterion.

### The deeper structural point

What you're really articulating is a design principle: **the size of the name change should match the size of the concept change.** A measure-zero concept difference deserves a minimum-possible name difference. English lets you:

- Change one letter and still have two real words → **block / lock**.
- Change nothing visible except a diacritic/superscript → typography, not vocabulary.

Anything bigger than one letter is overstating the conceptual distance.

Of the whole survey, only block/lock meets this while also being two real words, both dignified, both semantically defensible when defined as GIGANTIC terminology.

I think you've been gravitating toward the right answer from early in this conversation — the "stretch" worry may have been about the canal-lock metaphor feeling forced, but the *structural* fit (minimal glyph change, left-side drop = parent dropped, rhyming monosyllables) is as tight as English allows.

Worth sitting with a bit more, or does this feel like convergence?

---

## User

so a phylogenetic block is a parent-child segment of a tree - composed of the two nodes or node-tip and the edge in between. Segments in mathematics are defined as a line with two end-points. In our case an edge with two endpoints I guess. and a phylogenetic lock is the parent-child segment beginning at the first non-parent point of the phylogenetic block.

Visually we might imagine the lock as open at one and and terminating at the child node/tip. Or we might imagine it is having two end points but now the parent end point is replaced by the next point over from it. We could call the phylogenetiec lock point maybe. it is the direct non-parent point on a tree when traversing parent to child

or what do you think

## Assistant

Yes — you're articulating the topological structure precisely, and the naming follows it. Let me formalize with you and flag one wrinkle.

### The mathematical structure

- **Phylogenetic block** = closed segment on the tree: the edge plus both endpoints (parent node, child node/tip).
  - Notation: `[P, C]`
  - Two endpoints, one edge between them.

- **Phylogenetic lock** = half-open segment: the same edge, the child endpoint retained, the parent endpoint removed.
  - Notation: `(P, C]`
  - Topologically: the block minus a single point (the parent).

This is textbook interval topology applied to a tree edge. Clean and honest.

### Your two visualizations

**Option A**: Lock as a segment with *one* endpoint (the child) and the other side simply "open" — no point there at all, just the interior of the edge spilling out toward where the parent used to be.

**Option B**: Lock as a segment with *two* endpoints, where the parent has been "replaced by the next point over" — some infinitesimally-close-to-parent stand-in point.

Option A is the standard mathematical framing (half-open interval). Option B is intuitive but runs into a real problem.

### The wrinkle on Option B

The idea of "the next point over from the parent" sounds intuitive but **isn't mathematically well-defined on a continuous edge.** On a real-number interval like `(0, 1]`, there is no "first point after 0" — for any candidate point ε > 0, the point ε/2 is smaller. The reals are dense; there is no successor.

If we treat tree edges as continuous (as branch lengths usually imply), a lock has no "starting point." It has an **open boundary** — a conceptual threshold at the parent side where membership drops off, but no actual point.

If we treat tree edges as discrete/atomic (the edge is a single unit, no internal points), then "the next point" is just the child. In which case the "lock-point" collapses into the origin clade itself.

### The "lock-point" question — two readings

Your proposed term "phylogenetic lock-point" = "the direct non-parent point when traversing parent to child" can mean:

**Reading 1**: The lock-point *is* the child endpoint — the named clade terminating the lock. This is what we currently call `Origin_Clade_ID_Name`. In this reading, "lock-point" is a synonym for "the origin clade as a point on the tree."

**Reading 2**: The lock-point is a *virtual* point just past the parent — a conceptual placeholder for "where the lock begins." This is mathematically fictional on a continuous edge but pedagogically useful.

### Honest recommendation

I'd leave **block** = closed segment (two endpoints + edge) and **lock** = half-open segment (edge + child endpoint, parent excluded). No extra "lock-point" primitive — adding it introduces either redundancy (Reading 1 duplicates "origin clade") or a mathematical fiction (Reading 2 names a point that doesn't exist).

If you want a term for the open-boundary side of a lock, something like **lock-threshold** or **lock-cusp** works as a descriptor for "the place where the lock *begins* but no point sits there." But I'd only introduce it if you find yourself actually needing to refer to it — and I suspect most analysis references only the child (closed) endpoint, so the open side doesn't need a name.

### What does get named

In practice we've been naming locks by their child endpoint (the only well-defined point on a lock). That's consistent with how origin assignment works:

> "Orthogroup OG0000001 originates on the lock of `C082_Metazoa`" — the child clade uniquely identifies the lock.

The parent-side openness is understood from context: "the lock of X" always means `(parent(X), X]`. No second name needed.

Does this match what you were building toward, or were you thinking of "lock-point" as doing real work beyond what the child endpoint already does?

---

## User

Ok - I'm liking and disliking your details BUT

if a phylogenetic block is a parent-to-child segment with parent and child nodes (lets just treat tips as nodes for simplicity here) as endpoints and a lock is the same unit minus the parent endpoint - then it makes a lot of sense to refer to the phylogenetic lock based on the child name. But also - and this goes back to when I first concieved of blocks - it might even be in the crayon code or current gigantic code or documentation - a block should be named based on the parent and child names.

structurally the naming I came up with I think was:

phylogenetic block: parent_name::child_name
and now we could extend this to be:
phylogenetic lock: ::child_name

## Assistant

Oh — that's actually very clean. You've just solved the visual-relation problem by re-using the notation you already invented.

### The extended naming scheme

```
phylogenetic block:  parent_name :: child_name
phylogenetic lock:   :: child_name
```

The visual absence of text before `::` directly renders the topological absence of the parent endpoint. No new vocabulary, no new punctuation, no retrofitted metaphor — the notation itself **is** the topology.

### Concrete examples

| Entity | Notation |
|---|---|
| Block entering Metazoa | `C069_Holozoa::C082_Metazoa` |
| Lock of Metazoa | `::C082_Metazoa` |
| Block entering speciesA (sibling-leaf singleton case) | `C090_MRCA::C001_speciesA` |
| Lock of speciesA | `::C001_speciesA` |

The parent endpoint is literally edited out. One glance tells you whether you're looking at a block (transition-scorable) or a lock (origin-assignable).

### What this gets right

1. **Visual identity = conceptual identity.** The `::` persists because the edge persists; the parent name drops because the parent endpoint drops. Measure-zero conceptual change ↔ measure-zero notational change (one name field blanked).

2. **Reuses convention you already established.** No invention, no drift. If block is `parent::child` in the crayon code, lock is the natural syntactic extension.

3. **Self-describing in output tables.** A `Origin_Phylogenetic_Lock` column with values like `::C082_Metazoa` is unambiguous at a glance. No reader has to look up what the format means — the missing left side speaks.

4. **Composable with string parsing.** `lock = "::" + child_name`. A block's corresponding lock is the block with its parent prefix blanked. Script can construct one from the other trivially.

5. **Symmetric closure of the algebra:**

   | Form | Meaning | Used? |
   |---|---|---|
   | `parent::child` | closed block `[P, C]` | Yes — transitions |
   | `::child` | parent-open lock `(P, C]` | Yes — origins |
   | `parent::` | child-open form `[P, C)` | Rarely, if ever |
   | `::` | fully open `(P, C)` | Never |

   You have a complete four-form system even if only two forms see use.

### Practical reads

- "The orthogroup originates on the lock `::C082_Metazoa`" — reads naturally.
- "Lock of Metazoa" as a shorthand — also natural.
- Tables show `::C082_Metazoa` and the eye immediately parses "parent-excluded, child-retained."

### Small practical note

In code/output, keeping the `::` explicit in the string (rather than just writing `C082_Metazoa` alone) is worth it, because the `::` is the signature that this is an *edge-terminated-at-clade* not a *clade-as-node*. It visually distinguishes:
- `C082_Metazoa` → the clade node itself
- `::C082_Metazoa` → the half-open edge terminating at the clade
- `C069_Holozoa::C082_Metazoa` → the closed edge

Three distinct entities, three visually distinct strings. Good discipline.

### One thing worth checking

You mentioned this might be in the crayon code or current GIGANTIC docs. If `::` is already established as the block-naming delimiter in trees_species or elsewhere, then extending to `::child` for locks is pure continuity — no migration burden, just a new entity that slots into existing syntax. Worth a quick grep when you're ready to codify this.

This is probably the cleanest landing point we've reached. The canal-lock imagery still pays semantic dividends when *introducing* the term, but the notation itself doesn't lean on the metaphor — it's doing its own topological work.

---

## User

I think we definitely go with the identifer structure for block and lock - and leave open the idea that we might come up with better terms in the coming days - but I do want to push back on your verbal descriptions or understand better why you are phrasing things the way you are.

Block entering Metazoa
Lock of Metazoa
Block entering speciesA
Lock of speciesA

I'm not sure what I am not liking - but for example - blocks do not enter -they just sit there and exist. they are blocks.

and there is no reason to force traversal from parent to child - there can be reasons to traverse a block from child to parent.

lets start here on how to talk about blocks and locks

## Assistant

Fair pushback on both counts — "entering" was sloppy on my part. Let me rebuild the verbal conventions cleanly.

### What's wrong with my phrasing

- **"Block entering Metazoa"** — gives the block an implied agency and direction (it's going somewhere, moving toward a destination). Blocks don't move; they are.
- **"Lock of Metazoa"** — possessive is fine if Metazoa uniquely determines the lock, but I was inconsistent about when to invoke it.
- Forcing parent→child traversal in the verb — you're right that traversal is something an *analysis* does, not something the *structure* does. The structure is bidirectional.

### Cleaner separation: structure vs. analysis

**Structural reference** (direction-neutral, treats block/lock as static entities):

- **Block**: `parent_name::child_name`. Verbally:
  - "the block `C069_Holozoa::C082_Metazoa`" (just cite the identifier)
  - "the block between Holozoa and Metazoa" (symmetric, endpoint-listing)
  - "the block with endpoints Holozoa and Metazoa" (fully explicit, structural)

- **Lock**: `::child_name`. Verbally:
  - "the lock `::C082_Metazoa`" (cite)
  - "the lock at Metazoa" (locative, no agency)
  - "Metazoa's lock" or "the lock of Metazoa" (possessive — legitimate because a clade uniquely determines one lock; see below)

**Analytical reference** (directional only where the analysis actually imposes direction):

- "scoring the block `P::C` as a parent→child transition" — direction named explicitly, belongs to the analysis, not the block.
- "walking from leaf to root along path `[C, ..., P, root]`" — traversal is a verb performed by the walker.
- "inheriting across block `P::C` from parent to child" — direction explicit in the verb, not baked into the structure.

The point: direction is an *act*, not a *property* of the structure.

### Why "Metazoa's lock" is unambiguous but "Metazoa's block" isn't

For any non-root clade C:

- **C is the child endpoint of exactly one lock**: `::C`. There is no other. So "C's lock" uniquely refers to `::C`.
- **C participates in one block as the child** (`parent(C)::C`) **and in zero-or-more blocks as the parent** (`C::child₁`, `C::child₂`, ...). So "C's block" is ambiguous.

This means lock possessives are safe and natural ("Metazoa's lock"), while block references should use the identifier or the endpoint-listing form ("the block between Holozoa and Metazoa").

### Revised everyday phrasing

| Situation | Direction-neutral phrasing |
|---|---|
| Pointing to a specific block | "the block `Holozoa::Metazoa`" or "the block between Holozoa and Metazoa" |
| Pointing to a specific lock | "the lock `::Metazoa`" or "Metazoa's lock" |
| Describing an origin | "orthogroup OG0000001 originates on Metazoa's lock" |
| Describing a transition | "the orthogroup is conserved across the block `Holozoa::Metazoa` (parent-to-child)" — direction named by the verb, structure named neutrally |
| Walking up from a tip | "tracing the path from speciesA to the root traverses the blocks `speciesA's block, parent(speciesA)'s block, ...` in child-to-parent order" — direction is in "traverses," not in the blocks themselves |

### Small honesty note

Some phrases I'd retire from my own vocabulary going forward:
- "block entering X" → "block with child endpoint X" or "X's block as-child"
- "block leading to X" → same
- "lock into X" → "lock at X"
- "downstream of the block" → "on the child side of the block" (explicit which side)

Does this align with how you want to talk about them, or is there more directionality sneaking into my phrasing that you want to call out?

---

## User

this is incorrect - "the block between Holozoa and Metazoa" (symmetric, endpoint-listing)
it is not between - it includes Holozoa and Metazoa

I think in short form it would be the Holozoa-Metazoa phylogenetic block (C069_Holozoa::C082_Metazoa)

## Assistant

You're right — I was loose. "Between" excludes the endpoints; a block **contains** both endpoints plus the edge. So the verbal short form should include both names, as you've done.

### Corrected verbal conventions

| Entity | Identifier | Verbal short form |
|---|---|---|
| Block (closed, both endpoints included) | `C069_Holozoa::C082_Metazoa` | **the Holozoa-Metazoa phylogenetic block** |
| Lock (half-open, only child endpoint included) | `::C082_Metazoa` | **the Metazoa phylogenetic lock** |

The prose `-` and the identifier `::` serve parallel roles (both connect endpoint names), and the number of names in the short form matches the number of endpoints actually contained in the entity:

- Block contains two endpoints → two names in the prose form (`Holozoa-Metazoa`).
- Lock contains one endpoint → one name in the prose form (`Metazoa`).

The structural truth is rendered directly in how many clade names appear.

### Why this phrasing is structurally honest

- "The Holozoa-Metazoa phylogenetic block" — both clades are part of it. Naming both is accurate, not redundant.
- "The Metazoa phylogenetic lock" — only Metazoa is part of it. Naming only the child is accurate; adding Holozoa would misdescribe the entity (Holozoa is *not* in the lock).

So "between" was wrong for the block, and "Holozoa-Metazoa phylogenetic lock" would be wrong for the lock. Both errors would falsely describe the endpoint membership.

### Informal still OK

For brevity, when context is clear:

- **Block**: "the Holozoa-Metazoa block" (drop "phylogenetic")
- **Lock**: "Metazoa's lock" or "the Metazoa lock" (drop "phylogenetic", possessive OK since a clade uniquely determines one lock)

But the full form — "the Holozoa-Metazoa phylogenetic block" / "the Metazoa phylogenetic lock" — should be the default when writing precisely.

### Updated phrasings from my earlier list

| I previously said | Revised |
|---|---|
| "block entering Metazoa" | "the Holozoa-Metazoa phylogenetic block" (or Metazoa's lock, if the origin-zone reading was intended) |
| "lock of Metazoa" | "Metazoa's lock" or "the Metazoa phylogenetic lock" |
| "the block between Holozoa and Metazoa" | "the Holozoa-Metazoa phylogenetic block" |

Does this feel right as the canonical prose convention?

---

## User

Block (closed, both endpoints included)

would it be ok to define things as

Lock (half-closed, only child endpoint included)

then it is closed and half-closed

## Assistant

Yes — and it's actually a slightly better choice for GIGANTIC than "half-open." Here's why.

### "Half-closed" and "half-open" are synonyms in topology

Both terms describe the same object — an interval with one endpoint included and one excluded. Mathematics literature uses them interchangeably, though "half-open" is marginally more common in English textbooks. Neither is more rigorous than the other.

### Why "half-closed" fits GIGANTIC better

1. **Root-word consistency.** "Closed / half-closed" share the same root word. "Closed / half-open" uses two opposing roots, which introduces needless cognitive noise. The pair is cleaner when the words are morphologically related.

2. **Emphasizes what's *retained* rather than what's *missing*.** A lock's defining feature is that the child endpoint is present — the feature is secured there. "Half-closed" foregrounds the closure (the contained part); "half-open" foregrounds the absence (the missing parent). For biology, where we care about where features are locked in, foregrounding the closure is semantically apt.

3. **Harmony with the `::child` notation.** The identifier advertises presence (the child name is written) and absence (the parent side is blank). "Half-closed" verbally emphasizes the presence side; "half-open" would emphasize the absence side. Consistent framing across notation and prose.

4. **Terminology reinforces the metaphor.** "Lock" carries closure/securement connotations; "half-closed" extends that register naturally. "Half-open" would work against it slightly.

### Updated definitions

| Entity | Topology | Endpoints |
|---|---|---|
| **Block** | closed | both endpoints included |
| **Lock** | half-closed | only child endpoint included |

### Small caveat worth noting

Mathematically, "half-closed" doesn't specify *which* half — both `(P, C]` and `[P, C)` are half-closed. For full precision in the Rule 7 definition, we'd still write "half-closed at the child endpoint" or "child-closed, parent-open." But in prose after the term is defined, "half-closed" alone is fine since GIGANTIC only ever uses the child-closed variant.

This is a genuine improvement over "half-open" for your context. Adopting it.

---

## User

Ok - can you write a 2-3 page white paper on all of this - ignore all of our exploratory creativity and focus on the motivation/gap - and our solution and both mathematical-ish definition, phylogenetic-ish definitions, common/colloquial/general usage - and identifer structures etc etc.

---

*[Conversation transcript ends here — the next step was the assistant's first drafting of `whitepaper.md`. Subsequent rounds of feedback led to the development of the event block / inheritance block vocabulary, the five-state letter system (A/O/P/L/X), and the `parent::child-LETTER` block-state identifier scheme, which are documented in the current `whitepaper.md`.]*
