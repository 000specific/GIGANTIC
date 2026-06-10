<!-- ============================================================================
AI:      Claude Code | Opus 4.8 | 2026 June 03
Human:   Eric Edsinger
Purpose: One-page design brief for the proposed `ocl_outgroup_anchors`
         subproject. Captures the crystallized thesis from the 2026-06-03
         design session so the next session can pick up in ~30 seconds
         without unzipping the transcript.
Scope:   Design/brainstorm only. NOTHING built on disk yet. This is a
         research_notebook sandbox doc (free-form per gigantic_conventions §1).
Source:  Full session transcript ->
         research_notebook/research_ai/sessions/20260603_073344-claude_code-claude_opus_4_8-f3db1e8d.jsonl.gz
         (+ 3 paper-read sub-agent transcripts, same dir, same session id)
============================================================================ -->

# Design Brief — `ocl_outgroup_anchors`

**Status:** design/brainstorm only. Nothing built. An empty
`subprojects/ocl_outgroup_anchors/` dir already exists (name confirmed by
user — NOT "output"; it is "outgroup").

## The thesis (one paragraph)

Use **origins of loss, anchored against deep/diverse outgroups**, as
high-power, **branch-length-free**, long-branch-attraction-immune characters
for placing **unresolved clades** on a species tree. A feature that was
present in the ancestor of a candidate clade but is **unanimously absent
across that clade** is a single stem-loss — a **synapomorphy** uniting
"everything that lost it." These characters are informative by their
*rarity and hard-to-fake-ness*, not by a rate×time product we cannot know,
so they sidestep the unknowable-branch-length problem that (correctly)
worried us.

## Why it is rigorous, not "just parsimony / just-so"

- It is a claim about **character power/reliability**, not a ranking
  heuristic. No branch lengths, no ad-hoc normalization needed.
- It has a model backstop: a **gain/loss model of evolution** (asymmetric
  two-state Markov / **stochastic Dollo** / birth–death) is the feature
  analog of the substitution model. Parsimony is its rate-free limit. The
  model formalizes "loss gets harder as N grows" automatically (likelihood
  of unanimous absence under any retention is low without a real stem loss),
  and yields likelihood/significance/posterior support over candidate trees.
- The strongest existing evidence on this exact node (Schultz/Simakov/Rokhsar
  2023, chromosomal synteny → ctenophore-sister) is *the same kind of
  argument*: alignment-free, outgroup-polarized, rare near-irreversible
  shared-derived change, scored with an asymmetric-rate Bayesian model.

## The two densities (two different jobs)

1. **Outgroup density = COVERAGE of the ancestral repertoire** (not vote-
   counting). Losses are sporadic everywhere, so any one outgroup lineage
   has dropped some ancestral features; diverse outgroup sampling catches
   each ancestral feature **at least once**. The anchor is **existential**:
   one outgroup occurrence + one ingroup occurrence places the feature at
   their MRCA (same OR-logic that pushes origins deep). More outgroup clades
   → more complete **denominator** of ancestral features the clade *could*
   have lost.
2. **Candidate-clade density + BREADTH** makes the loss hard to fake.
   Unanimous absence across many, **phylogenetically spread** species is
   improbable unless there was a single stem loss; patchy/convergent/
   retained-but-undetected alternatives collapse as sampling grows.

## The artifact direction (key result) and the one real control

- Detection failure on divergent sequences inflates **apparent LOSS**
  (a real feature looks absent). Ctenophores are highly divergent, so this
  artifact predicts they should show **more** loss. Observed: on structure_001
  orthogroups, Ctenophora ≈ **1700** losses (~5 spp) vs sibling ≈ **3500**
  (~50 spp). The artifact runs **opposite** the observed signal → the
  low-ctenophore-loss finding is **conservative** (truth likely more extreme),
  not threatened. Sibling's high loss is not explicable by detection failure
  (less divergent side). LBA inflates false *presence* (origins);
  divergence inflates false *absence* (losses) — so the **loss signal is
  LBA-immune**.
- **Residual control (narrowed & flipped):** the real risk is **false
  RETENTION** — a divergent ctenophore protein mis-binned *into* an ancestral
  orthogroup, faking presence and artificially lowering loss. Rarer
  (divergent seqs usually drop out, not precisely mis-cluster). So the
  detection check is: **verify ctenophore RETENTIONS are genuine orthologs,
  not mis-assignments** — NOT "are the losses real."

## The deliverable model (what we actually build)

A **zone-stratified topology evaluation**, not a single global score. For
every (feature × candidate tree), classify into:

- **CLEAR-SIGNAL zone** — ancestral presence anchored by diverse outgroup
  coverage + unanimous absence across a dense, broad candidate clade +
  retentions detection-verified.
- **ARTIFACT / AMBIGUITY zone** — thin outgroup coverage, sparse/narrow
  clade sampling, or unverifiable detection.

Then evaluate **all 105 structures** (or any chosen set) on the **clear-signal
characters only**, **quarantine** the ambiguity zones explicitly, and
**highlight the tree(s) the clear-signal zones cohere on.** Resolve what the
clean signal supports; report the rest as honestly unresolved. The
confidence stratification **is** the product (this is the project's
no-silent-artifacts stance, operationalized).

## Strongest-character recipe

Feature **present** across a diverse outgroup + **absent** across a dense,
broad candidate clade + **detection-verified** retentions = a high-power,
branch-length-free **loss synapomorphy** — the alignment-free analog of a
synteny fusion.

## Prospective sampling design (the method prescribes its own data)

Power scales with the phylogenetic density of the clades being placed.
Ctenophores were historically the thinnest-sampled (where signal is weakest
and the detection blind spot worst); this analysis has **the most ctenophore
genomes ever** in a genome-scale phylogeny → highest-leverage input. Future:
**10× and EQUALIZE** the clades flanking unresolved nodes — equalize on
**breadth** (spread across the clade's deep splits), not headcount (50 close
tips ≠ 5 deeply-divergent). Unlike sequence trees (where added taxa can
*worsen* LBA), adding well-spread taxa here **monotonically** strengthens the
loss signal, shrinks the detection blind spot, and improves outgroup
coverage. The tool can therefore prescribe where to sequence next.

## Literature grounding (read 2026-06-03)

- **Schultz et al. 2023, Nature (PMC10232365)** — synteny → ctenophore-sister;
  ALGs coded 0/1/2, 7 derived fusions (4 irreversible "fusion-with-mixing")
  unite non-ctenophore animals, polarized by 3 unicellular outgroups,
  asymmetric-rate Bayesian, posterior 1.0; argued LBA-immune.
- **Copley 2025, MBE msaf321** — statistical rebuttal: null must respect
  **phylogenetic non-independence**; significance must account for size;
  only ~2 fusions survive a correct test; even "irreversible" changes can be
  convergent. **Design constraints for us if we ever count rather than
  model.**
- **Schultz & Simakov 2026, Annu. Rev. Anim. Biosci.** — "evolutionary genome
  topology" manifesto (state-space of karyotypes, irreversibility).
- Context: King & Steenwyk 2025 *Science* (sequence-based sponge-sister) was
  **retracted Jan 2026**. The node is genuinely open.

## Next concrete thread (smallest honest test — start here)

Orthogroups + the **basal metazoan split** only:
1. Confirm inputs on disk: structure_001 OCL orthogroup output
   (`ocl_phylogenetic_structures/BLOCK_orthogroups_X_ocl/.../OUTPUT_pipeline/structure_001/`),
   trees_species clade→species mappings, unicellular-outgroup membership.
2. Pull clear-signal loss-origin characters (present in ≥1 diverse unicellular
   outgroup; unanimously absent across Ctenophora; retentions
   detection-verified).
3. Check whether they discriminate **ctenophore-sister vs sponge-sister**,
   and map clear-signal vs artifact/ambiguity zones.
Pass = a rigorous core. Fail = the honest limit located (either answer is the
goal).

## Open / parked

- Define the OCL "shared derived change on a candidate stem" synapomorphy
  unit precisely.
- STEP vs BLOCK scoping for the subproject (resolved base case + unresolved
  105-structure case).
- Candidate GIGANTIC vocabulary: *phylogenetic density* (species count in a
  clade); *horizontal / vertical phylogenetic resolution* (spread across /
  along time); *clear-signal vs artifact/ambiguity zones*.
- Precedent to reuse: `z_parsimony_tree_structures` already ranks the 105
  structures by summed `Loss_Events` (the whole-tree-sum cousin of this).

---

## ADDENDUM (2026-06-03, later same session)

### A. Direction correction — the signal is a SHARED LOSS (synapomorphy)

For "**Clade 1 basal**" to be a *valid* (synapomorphy-based, not symplesiomorphy)
inference, the diagnostic character is: **present in outgroup → present in
Clade 1 → SHARED-absent across *all* of Clade 2.** A loss shared across the
whole of Clade 2 is a derived character uniting Clade 2 (its single-loss
explanation requires Clade 2 monophyly), which makes Clade 1 the outsider.
The signal lives in **Clade 2's shared loss** (apomorphic), NOT in Clade 1's
retention (symplesiomorphic, non-grouping — the trap we kept circling). The
density/breadth gates are load-bearing here: to call a loss "shared across
all of Clade 2" you need Clade 2 densely + broadly sampled.

**Two siblings + outgroup is symmetric** — "which is basal" is undefined
without a 3rd ingroup lineage. The discriminating signal is multi-clade and
is extracted by holding the **outgroup + a stable parent clade** fixed
(Rule 6 stable `clade_id_name`, e.g. `C082_Metazoa`) and letting diagnostic
shared-loss characters vote on the child arrangement **across the 105
structures** — walk node by node.

### B. "Run everything, interpret via A" (user preference)

Do NOT pre-gate. Compute OCL for everything, then read confidence from the
quality criteria (A): clade density, within-clade breadth (horizontal) and
depth (vertical) resolution, outgroup presence/commonness, detection-
verification. Zone names: **Diagnostic / Suggestive / Ambiguous.** Ideal is
BALANCED representation across the clades; a density asymmetry whose loss
trend runs *counter* to it (smaller clade, fewer shared losses) is a
robustness booster, not a requirement.

### C. Prior work EXISTS and left off exactly at "loss apomorphies, untested"

`z_parsimony_tree_structures/parsimony_tree_structures-staging-2026may11/`
(BLOCK_ocl_orthogroups) has a 14-script pipeline.
- Headline ranking (scripts 002→003→004) **SUMMED per-orthogroup
  `Loss_Events`** per structure + bootstrap. It RAN: winner = **structure_045**
  (best in 91.7% of bootstraps); user input tree structure_001 ranked ~89th.
- It used **raw summed losses, NOT clean loss apomorphies.** The user's
  notation `F[s_001(U+,(A+,(B-,C-)))]=1 loss` vs `F[s_002]=2` is
  **clade-binarized Dollo**, started in `010_*clade_binarized_parsimony.py`
  (6 OTUs = unicell + 5 clades) and `013_*co_occurrence_parsimony.py`
  (synapomorphy counting), but **never tested clean on the full 105.** Loss
  apomorphies = the untested frontier (user recollection confirmed).
- **Incomplete:** run halted at script 005 validation (orthogroup-count
  mismatch in structure_003); only 94/105 completed.
- **Central blocker (real, not mechanical):** losses are **non-independent**
  (co-loss via assembly fate, physical clustering, pathway co-loss) → ~200k
  orthogroups may be only ~50–100 *effective* characters. Whitepaper crux:
  *"the independence argument is about origins, not absences."* Same issue
  Copley raised for synteny. Sensitivity analysis flagged
  "required for publishability," **never run.**
- The occams `TODO.md` already designs the zone idea: a **4-of-5-clade
  representation filter** (4/5 = discriminating, 5/5 = controls, <4/5 =
  LBA-risk) + per-feature **topology-invariant / topology-discriminating /
  not-applicable** classification. The perspectives draft is the
  **per-structure query layer only**; cross-structure ranking lives here.

### D. Placozoa-at-base — anchoring removes ONE scoring bias, it is NOT a cure

Top raw-sum trees often put **Placozoa basal** (not ctenophores or sponges) —
uncommon and suspicious. There are **two independent artifact sources**, and
anchoring only touches one:

- **(a) Scoring bias [anchoring removes this].** Placozoa is **gene-poor**;
  raw-sum counts **L** but not **A** (pre-origin absence is free). For
  animal-novelty genes (absent in unicells), a gene-poor taxon's absence is a
  counted **L** if nested but a **free A** if it branches *before* the gene
  originated — i.e., at the base. So basal placement re-labels novelty-
  absences L→A and lowers the score → raw-sum pulls reduced-genome taxa to
  the root (gene-content analog of LBA). Scoring only **outgroup-present
  (ancestral)** features makes state A impossible (origins all pre-animal),
  so every absence is a real L and basal placement earns no discount — this
  scoring bias vanishes.
- **(b) Data truth [anchoring does NOTHING].** If Placozoa's gene-poorness is
  itself an artifact (incomplete assembly / detection), then placing it
  "derived" via anchored scoring is just as wrong as placing it basal — same
  bad data, different label. Anchoring removed a *scoring* bias, not a *data*
  problem. (User's correction — the earlier "cure" framing was wrong.)

**The 4 placozoan genomes are the test for (b)** — density thesis applied to
Placozoa: if 4 independently-assembled genomes all lack the same ancestral
features, assembly incompleteness can't explain it → gene-poorness is REAL.
(Placozoa is far less divergent than ctenophores, so the risk is assembly
completeness, which 4 genomes addresses, not detection failure.)

**But even REAL gene-poorness does not give branching position.** Total-loss
count (raw OR anchored) is a **derivedness proxy, not topology** — a clade can
be truly gene-poor and branch early, or gene-poor and branch late. And a
gene-poor taxon **spuriously shares losses with everyone** (convergent-loss
homoplasy), so it gets pulled toward whichever clade it co-loses with most.
=> The only valid topology signal is the **shared-loss apomorphy** (a *single*
Dollo loss uniting a *specific* group), and gene-poor taxa require explicit
**loss-rate control** so their many (partly convergent) losses aren't over-
credited. This is the non-independence / loss-rate-heterogeneity blocker made
concrete; it is exactly the sensitivity analysis the occams notes flagged as
required and never ran. **Placozoa = the hardest stress test of the method,
not a taxon anchoring fixes.**

### E. Sharpened morning target

1. **First test (scoring-bias check, NOT a cure):** re-score *anchored*
   (outgroup-present features only) vs *unanchored* on existing structures;
   see whether removing the A-vs-L discount moves Placozoa off the base. Read
   the actual top-structure topologies (incl. what structure_045 is) from the
   newick/registry. NOTE: moving Placozoa is necessary, not sufficient — the
   real placement needs shared-loss apomorphy + loss-rate control (steps 3-4).
2. Verify Placozoa gene-poorness is REAL across the 4 genomes (rules out
   assembly artifact — data-truth check (b)).
3. Fix the 94/105 validation halt so the full set is scored.
4. Run **clade-binarized loss-apomorphy Dollo** (script-010 style) as the
   headline, on outgroup-anchored features, classified by the 4/5 +
   diagnostic-zone filters.
5. Handle **non-independence / loss-rate heterogeneity** honestly (effective-
   character count / event-level dedup / permutation null; down-weight
   gene-poor taxa's elevated loss rate) — don't assume it away.
6. Decide scoping: extend/promote `z_parsimony_tree_structures` vs stand up
   `ocl_outgroup_anchors` as its own subproject (STEP vs BLOCK).
