# STEP_2-occams_tree — Brainstorming Notes

**Date**: 2026-04-14
**Participants**: Eric Edsinger + Claude (Opus 4.6, Claude Code session)
**Purpose**: Design conversation for `STEP_2-occams_tree`, a planned post-processing step
that consumes STEP_1's per-structure OCL summaries and ranks candidate species trees
by total-loss minimization. This document preserves the exploratory dialogue verbatim
so nothing is lost as we iterate. Not a specification — a working draft of thinking.

---

## Session begins — user prompts for brainstorm

### Eric
> Ok - lets work on brainstorming STEP_2 - what are your impressions so far and I can work on gettings us fully aligned with my thinking/framework - and see what you think

### Claude
Here's where my thinking is — partly confident, partly fuzzy. Let me lay it out so you can redirect:

**What I think STEP_2 does (basic version):**
- Input: the 105 `complete_ocl_summary.tsv` from STEP_1
- Per orthogroup × per structure: loss count (probably "loss at origin" events, not "continued absence")
- Aggregate per structure → total-loss score
- Rank structures by ascending total loss → structure_001 (user's input tree) lands somewhere in the ranking
- Output: `structure_ranking.tsv` + maybe `per_orthogroup_structure_matrix.tsv`

**What I'm less sure about (open design questions):**

1. **What counts as a "loss"** — loss_at_origin only, or also continued_absence weighted less, or a composite?
2. **Weighting** — raw count? or weighted by clade depth, orthogroup size, species count affected?
3. **Normalization** — raw loss count can bias toward trees that just make fewer things possible. Divide by total blocks? By conservation events?
4. **Significance** — is structure_007 really better than structure_008, or noise? Some confidence indicator on the ranking vs. pure ordinal.
5. **Whole-tree vs per-orthogroup winners** — one output: "best tree overall." Another output: "for each orthogroup, which tree fits best" — the second surfaces heterogeneity (different orthogroups support different topologies).

**Where I think the novelty lives (partly a guess):**

Not in the occam's-razor idea itself (standard parsimony territory) but in the **specific combination**:
- Orthogroup presence/absence as characters
- Genome-scale (150k+ orthogroups)
- Using OCL's clean loss-at-origin vs continued-absence distinction (most parsimony methods don't separate these)
- Constrained to structurally meaningful topologies (the 105 from trees_species resolutions), not unconstrained tree search
- Can flag heterogeneity — does the data tell one story, or do different orthogroup classes tell different stories?

**What I'd want to hear from you:**
- Is the scoring fundamentally loss-count-based, or something different?
- Do you envision STEP_2 outputting a single "winner" or showing the distribution of evidence?
- How much does "weight by biology" matter (depth, size, species count) vs. starting with clean raw counts?
- Is STEP_2 supposed to be reusable across `_X_ocl` flavors (orthogroups, annotations, etc.) or specific to orthogroups?
- Is there a STEP_2 parallel in GIGANTIC_0 I should look at?

Your turn — correct me where I'm off and fill in what I'm missing.

---

### Eric
> I think that is a pretty good technical start on things - and you raise important technical questions we need to address in detail!
>
> But let me give you more on the motivation and novelty side of things - why it could be useful as a new tool in resolving species trees and understanding evolution at genome-scale across species and for specific biological systems etc.
>
> And it is really just an idea in my head - so please as you gain understanding of my thinking - be a critical devil's advocate to ensure the ideas hold up as rigors and potentially informative - rather than half-baked and a poor choice of direction in analysis.

### Claude
Understood — devil's advocate mode engaged.

I'll push on things like:
- Claims of novelty (what's actually new vs. existing phylogenomic methods like ASTRAL, Dollo parsimony, gene tree reconciliation)
- Whether the signal from orthogroup presence/absence is clean enough to resolve contested nodes (deep nodes like ctenophore-sister vs sponge-sister have been fought over precisely because genomic data is noisy)
- Whether "minimum losses" is the right parsimony criterion (biological losses aren't uniformly probable — some lineages are prone to gene loss, which could bias the score toward tree topologies that cluster loss-prone lineages conveniently)
- Whether 105 structures is enough resolution (what about topologies not in that set?)
- Whether structure_001 having any particular rank is scientifically meaningful or just a quirk of how the pipeline orders

I'll try to make the pushback specific and technical, not rhetorical. Fire away with the motivation.

---

### Eric
> Ok - so phylogenetic signal in sequences - aligned and used to build species trees - can be problematic for certain nodes in organismal evolution - including deeper nodes or nodes including taxa that are rapidily evolving - rates of evolution are greatly different across species and genes etc.
>
> 3D structure offers a means of seeing deeper into the twilight zone of sequence alignment - so some gains can be made there - the so far limitations are problematic and depth of gains ultimately limited I would imagine.
>
> Synteny is a novel phylogenetic signal that has proposed resolution of the sponge vs ctenophore debate - but really in a sense it is like fossils or pre-genomics species phylogenetics. Unique things are hard to argue with when shared in a precise manner. Its too early to know how powerful this will be for other phylogenetic challenges in the field - or if it will hold up over time. I love it - and was a postdoc with Dan Rokhsar and when Oleg Simakov was visiting his lab - but TBD for general use and broad applications or not.

### Claude
Tracking so far:

- **Sequence-based phylogenetics:** rate heterogeneity across species and genes makes deep nodes and fast-evolving taxa unreliable — the classical failure mode
- **3D structure:** pushes past the sequence twilight zone but has ceiling (structure is itself under selection and converges; not everything has a resolvable fold in databases)
- **Synteny:** novel signal class; Rokhsar/Simakov work on sponge/cteno. Treating unique shared configurations as quasi-fossil evidence — rare/derived states carry weight because they're unlikely to convergently arise

Pushback I'm holding in reserve (not to interrupt your flow, just registering):
- On synteny-as-fossil — persistent-state evidence isn't quite like single-observation fossils; the analogy may overstate the epistemic weight
- On sequence methods — they DO account for rate heterogeneity (partition models, mixture models, LG+C60, etc.); the critique has to be that even with accounting, deep nodes stay contested, which points to signal limitation, not method limitation

Continue — where does orthogroup loss parsimony fit into this landscape? What gap does it address that the three above don't?

---

### Eric
> The challenge with sequences is getting the alignments right - it can just get really messy - especially if you are going deep and broad in the species set.
>
> From another direction - there is a LOT of homology-based data generated in genome projects that is rarely leveraged beyond specific biological questions - maybe 0.1-1% is utilized if that out of a full interproscan annotation with all of its tools - plus TM and signalp tools etc. They are informative - even at scale in providing a framework - but the phylogenetic signal that brought a annotation to a sequence is rarely if ever then used to solve a phylogenetic problem beyond a specific biological feature for a limited subset of annotations.

### Claude
Now I see the shape of the argument — and I like parts of it and want to pressure-test others.

**What I find compelling:**
- Annotation data IS under-leveraged phylogenetically. Billions of compute-cycles go into generating these annotations; the downstream phylogenetic use is a tiny fraction of their information content
- HMMs (InterProScan, Pfam) can detect homologs past the sequence-alignment twilight zone — that's their whole point. So annotation-derived signal can reach deeper than raw alignment
- Scale argument: 150k orthogroups × 70 species is a genome-scale character matrix. Even noisy per-orthogroup signal might aggregate to clean collective signal
- The OCL loss-at-origin vs continued-absence distinction is sharper than standard gene-content phylogenetics, which usually just tallies shared presence

**Devil's advocate concerns I'd want to hear addressed:**

1. **Circularity** — orthogroups are computed with their own models (OrthoHMM, OrthoFinder); annotations come from HMMs trained on known homology relationships. Using these as independent phylogenetic characters conflates "observed data" with "prior homology inference." How much of the signal is truly independent from what went into the annotation pipeline?

2. **Absence ambiguity** — a species "missing" a Pfam domain could be: real loss, incomplete genome, failed annotation (HMM drift past detection), or rapid evolution. The parsimony score treats these as equivalent. In practice, trees that happen to cluster genome-assembly-poor species together might score better by accident.

3. **Prior art** — "gene content phylogeny" goes back decades in microbes (COG-based). How is this materially different from "OCL-based gene content phylogeny"? The differentiator has to be more than scale.

4. **Synteny contrast** — synteny's power is rare + derived. Annotation presence/absence is common + ubiquitous. Those are different epistemic regimes. Does this work more like a statistical signal (law of large numbers across many orthogroups) or more like synteny's "unique events are unambiguous" logic?

Keep going — what's the deeper motivation?

---

### Eric
> All interesting/great points we need to come back to!
>
> Focusing for now on orthogroups - people will use sequences from some orthogroups to build species trees - like using BUSCO Metazoa for example - these are single gene orthogroups where the gene is conserved across nearly all species without duplication nearly all of the time. But again, you then have the mess of alignment and tree building off of the mess of alignment.
>
> HOWEVER
>
> The orthogroup itself should be a robust evolutionary feature of the species set. Given how it was derived, it is highly likely that the orthogroup as an entity is a real product of evolution - and so its sequences are closely homologous and species and their sequences are likely fully represented across the species tree for most orthogroups - with everything in general. There are always scattered exceptions but highly likely for all all things in general.
>
> Also in general - loss of an orthogroup after its origin in a species tree should be fairly uncommon. It does happen - and I think it happens a lot more than is commonly appreciated but notheless, it is uncommon and even might be considered rare - something we might quantify later within GIGANTIC I think - as another STEP or BLOCK here or elsewhere.
>
> Given all this - if you have the true species tree and you have mapped orgins, conservation, and loss of an orthogroup (or any feature evaluated in a homology context across all species of a species set) onto the tree - any changes in the train that change branching after the origin of the orthogroup or feature will most likely impose additional losses of the orthogroup or feature.
>
> This is a very general thing - any specific instance of an orthogroup will behave based on the actual data / specifics of its actual evolution across the species set.
>
> HOWEVER
>
> if we have hundreds or even a thousand or more independent orthogroups or features - and we score across all possible species topologies of relevance - I think it should be the case that the true species tree will have the fewest number of losses overall.
>
> Or something like this!

### Claude
This is coherent and the logic tracks. The core claim — true tree minimizes forced extra losses — is a valid parsimony argument. But let me push on four specific things:

**1. "Losses are rare" is load-bearing and contestable.** Loss rates are highly heterogeneous across lineages. Cteno genomes in particular show extensive lineage-specific loss — they're exactly the kind of clade where this method could be misled. Parsimony under high-loss regimes has known failure modes (analog to long-branch attraction). The method needs to either (a) be robust to rate heterogeneity, (b) explicitly model it, or (c) flag uncertainty when rates are high.

**2. Independence assumption is probably wrong.** 1000 orthogroups is NOT 1000 independent observations:
- Orthogroups share genome-assembly fate (incomplete assembly → many co-absent)
- Physical clustering (losses in same chromosome region co-occur)
- Pathway-level loss (you lose one, the rest become dispensable)
- The "effective number of independent characters" could be ~50–100, which changes the law-of-large-numbers math materially.

**3. This looks a lot like Dollo parsimony.** Dollo is specifically designed for presence/absence characters where gain is rare/unique and loss is possible multiple times. That's exactly the orthogroup-origin scenario. So the question is: is this a new method, or is it **"Dollo parsimony applied rigorously to modern genomic orthogroups at scale, using the OCL framework's loss-at-origin vs continued-absence distinction"**? The latter is still valuable and defensible, but the novelty framing should be about data + rigor + scale, not a new parsimony principle.

**4. Validation test:** Before claiming this resolves contested nodes, show it recovers KNOWN-resolved nodes. Mammals are well-resolved, arthropods are well-resolved. Run this on species70 and ask: does it correctly place primates, or does it place some cteno-species-equivalent loss-heavy lineage wrongly? If it fails on settled relationships, the deep-node claim is moot.

**What I think holds up:**
- Alignment-independence is a real and valuable niche
- Scale (genome-wide orthogroup matrix) is a real advantage over traditional parsimony
- The OCL distinction (loss_at_origin vs continued_absence) is a meaningful refinement — standard Dollo doesn't make this

**What I think needs careful claiming:**
- Not "new method" — "rigorous application of Dollo-style parsimony with modern genomic data + refined event accounting"
- Sensitivity analysis to lineage-specific loss rates is table stakes before publishing
- Discordance flagging is probably more scientifically honest than picking a "winner"

Your thoughts on the lineage-specific-loss concern specifically? That's the one I think could kill it if unaddressed.

---

### Eric
> 1: I think it might be robust to a lot of the lineage specific heterogenity and losses. For two reasons - one is that it is not counted losses of species or ancestral species nodes in particular. It is just summing losses across the entire tree. Its fine if some species are high loss on the true species tree. The second is that clustering pulls in homologs at the level of e-3 or -5 or something very relaxed and promiscuous - and then in comparisons refines things into orthogroups. So we have a lot of confidence that the set of sequences are deeply homologous / accurately homolgous and that all sequences that should be included are likely included. (To an extent - singletons are problematic, as they might be rapidly evolving sequences that belong in an orthogroup - but again the robustness to this is that even still, I think the accurate species tree will have the fewest losses -but we might want to discuss or model this somehow).
>
> Anyways - if the orthogroups or feature is largely accurate sets sequences or feature units across the species tree - then we can leverage the phylogenetic signal withOUT alignment and tree building - which are messy and problematic - but we still get to leverage the phylogenetic signal.
>
> 2. 1000 orthogroups are 1000 independent origins in evolution - the other traits are not relevant to this independence - they may generate noise, like artefacts related to assemblies - but the orthogroups or features are independent in actual evolution of the species set - at least in terms of their origins in evolution - biology might be linked across orthogroups but again, this is not relevant I don't think.
>
> 3. I'm not trying to claim a new parsimony prinicple - just a new approach to species tree phylogenetics/phylogenomics.
>
> 4. That is a great idea!
>
> I stil disagree on this -Not "new method" — "rigorous application of Dollo-style parsimony with modern genomic data + refined event accounting" - it is a framework and approach that is very unique I think. the algorithm of parsimony or occams razor or dollo specifically is classic to ancient in human thinking - probably neandertals and maybe even liviing primates and mice utilize it - who knows - octopus?
>
> I'm not clear what you mean here - Sensitivity analysis to lineage-specific loss rates is table stakes before publishing - I'm not familiar with the phrase "table stakes before publishing"
>
> Even if you pick a winner - there might be a tie - this happens all the time in tree building and sensitivity analyses for them!  and there are approaches to address this that might be used in a parallel manner.

### Claude
Your responses are good — let me recalibrate:

**Point 1 (lineage heterogeneity):** You're partially right and I under-credited you. Losses that appear under ALL 105 candidate trees cancel out of the ranking — what matters is topology-dependent loss differences. A high-loss lineage's raw loss count contributes to the score's magnitude but not necessarily its ranking bias. I'd still want to see this quantified (split losses into topology-invariant vs topology-contingent and confirm heterogeneity lives mostly in the former), but the logic is defensible.

**Point 2 (independence):** You made a distinction I missed — you're talking about independence of **origins**, not independence of **loss events**. Origins are genuinely independent evolutionary events. Loss correlation is real but biases score magnitude more than ranking. I partly retract my concern. Partly — because co-loss across correlated orthogroups can still bias ranking toward trees where the correlation-generating lineages happen to cluster. But you're right that the origin-independence framing is the right unit of analysis.

**Point 3 (novelty framing):** You're right, I was reductive. Parsimony/Dollo is the algorithmic kernel — ancient, uncontroversial. The **framework** is:
- Orthogroup-as-evolutionary-feature (alignment-free phylogenetic unit)
- OCL's refined event accounting (loss_at_origin vs continued_absence)
- Systematic evaluation against enumerated meaningful topologies from trees_species
- Genome-scale aggregation with per-feature traceability

That IS novel as an integrated approach. Comparing to "molecular phylogenetics uses likelihood": the statistical principle is classical, but the framework around it (substitution models, partitioning, etc.) is where the field lives. Same shape here.

**"Table stakes":** Poker term — the minimum you have to put in to be dealt into the hand. Figuratively: the bar below which reviewers won't take a submission seriously. A sensitivity analysis to heterogeneous loss rates would be a reviewer's first concern — without it, manuscript gets bounced before substantive evaluation. Not optional; not nice-to-have; the price of entry.

**Ties and uncertainty:** Totally tractable. Borrow from tree-building tradition — bootstrap-analog: subsample orthogroups, compute loss scores, see which trees stably rank high; confidence bands around top-ranked trees; "structure_007 is best with 95% of subsamples" vs "best tie between 3 structures."

**New concern I'd want to raise:** The 105 candidate topologies are constrained by the user's INPUT tree. If the user's input tree has a wrong non-unresolved branch (say, a misplaced genus deep inside a "fixed" clade), none of the 105 topologies contain the true tree, and the method will confidently pick the best-among-wrong. How do we defend against this? Are the "fixed" parts of the input tree always trustworthy?

---

### Eric
> I want to continue on all of your points here -but for a start I will start at the end.  New concern I'd want to raise....
>
> I think it doesn't matter as along as the user tree is accurate in including all species per ambiguous node - the evaluation is specific to all possible topologies given ambiguity in specific nodes. Swapping clades at those nodes does not impact anything inside the nodes - and the structure inside the nodes doesn't matter. So as long as the user has high confidence all species are within the correct clades of undersolved nodes - then it should be great, regardless of incorrect toplogies within the clades of unresolved nodes. Even, you could tree the clades of unresolved nodes as themselves fully unresolved.

### Claude
Good catch, you're right. Let me walk through the logic:

Since the 105 candidate topologies only permute the unresolved nodes (Ctenophora/Porifera/Placozoa/Cnidaria/Bilateria for species70), the fixed-internal-clade topology appears **identically** in every candidate. Any error inside a fixed clade is a constant term across all 105 scores — it inflates absolute loss counts but cancels out of the ranking. The method's answer for "which of the 105" is unaffected.

The **residual concern** that your framing points toward is different and narrower:

**Species-to-clade assignment** errors (e.g., a placozoan mis-classified as cnidarian) — those DO affect ranking, because they misplace leaves in a way that persists across every candidate tree's accounting of loss. All 105 scores are wrong in the same way → best-among-wrong.

And you already said the right response: as long as the user has high confidence on species-to-clade membership, the method is robust to internal-clade topology errors. That's a meaningfully lighter bar than "get the whole tree right," which is the whole point.

Your "could treat internal clades as also unresolved" extension is interesting — it would just generate more candidate topologies without changing the logic. Good to know the framework scales.

Retracting my concern. Moving on — continue with the other points whenever ready.

---

### Eric
> POINT 1 - I'm actually not saying this in the way you say it "Losses that appear under ALL 105 candidate trees cancel out of the ranking". We might be saying the same thing but what I want to highlight is that specific sequence or feature heterogenity of homologs across a species tree is not relevant to the methodology - and the methodology is actually robust to it. VS sequence alignment is highly sensitive to it at the level of sequence change. Only in cases where sequences evolve so fast that even the relaxed thresholds of HMMs or blast fail to detect a sequence homolog/ortholog at all will it impact the accuracy of the orthogroup species set - but this should be infrequent and again shouldn't impact things too much or not at all (have to think it through more) - for the orthogroup containing with most species the highly divergent species is absent and topologies that move it to an outgroup position will remove this articial loss improving the score of the incorrect tree.  On the other hand the second orthogroup formed of just sequence or sequences from the rapidly evolving species will not be impacted by any changes in topology.
>
> A more problematic orthogroup would be one formed of different rapidly evolving species pulled together by long-branch attaction at the level of the blast or hmm threshold.  For this reason, we might require use of orthogroups/features that have all ambigous clades represented - or all but one of the ambigous clades represented  - both of which would avoid this situation

### Claude
Right — I was reframing your claim as ranking-invariance when your actual point is deeper: the **unit of analysis** is the orthogroup-as-entity, and sequence-level heterogeneity doesn't propagate into that unit the way it does into alignment. That's the structural advantage of the approach: you sidestep the sequence-level rate heterogeneity problem by not operating on sequences at all. Cleaner framing; I'll hold that.

**On your LBA-at-clustering concern — that's sharp.** The failure mode you describe is:
- Rapid-evolving species fail HMM detection → artificial absence → score inflates for wrong topologies that place that species as outgroup
- *Worse*: rapid-evolvers from multiple lineages pass relaxed thresholds together, forming a phantom orthogroup that carries false signal

This is real long-branch attraction at the clustering stage. I hadn't fully articulated it.

**On your proposed filter — "all unresolved clades represented" (or all-but-one):** Good instinct, but note a subtle point:

- **All 5 clades represented**: the orthogroup was present at the LCA of all 5 → its parsimony score is *identical or near-identical* across all 105 topologies. These orthogroups carry no differentiating signal — they're confirming but not discriminating.
- **All-but-one (4/5 clades)**: this is where the signal actually lives. The missing clade must have either lost it or never had it, and WHERE that missing clade sits in a candidate topology changes the implied loss events. Best discriminating orthogroups.
- **Fewer than 4**: more discriminating signal *per orthogroup* but higher LBA risk.

So the filter strategy might be: **weight or gate by representation pattern**. The 4/5 orthogroups are the sweet spot. The 5/5 orthogroups act as noise-reducing "controls" that should score equal across topologies (if they DON'T, that itself is a diagnostic flag).

**New question that I'd want to raise:** What fraction of the 150K orthogroups pass a 4/5 or 5/5 filter? If it's a tiny slice (say, <5%), the effective-N drops, and you're back to a smaller signal pool — still at genome scale, but worth quantifying. Also: broadly-conserved orthogroups skew toward ancient core-biology genes, which is a different bias (phylogenetic signal from housekeeping might differ from signal in lineage-specific innovations).

Good sharpening of your point. Your turn.

---

### Eric
> Orthogroups (in this case) that originate inside the clade of an ambiguous node have no relevant phylogenetic signal and will not change across all topologies. Similarly, orthogroups/homology features that originate before the deepest ambiguous node will be not change across topologies.
>
> It is only orthogroups that arise between the two that provide phylogenetic signal. And in orthogroups, this number might drop to not so many.
>
> HOWEVER
>
> similar to how phylogenetics was being done in the 90s - where different kinds of data types were being leveraged on the tree - we can pull all genomic annotations evaluated across all species in the species set - so orthogroups, pfam domains, synteny blocks, etc etc we would need to be careful that different tools are not reevaluating the same thing - so SMART and Pfam and GO might overlap in annotating the same feature - but orthogroups and Pfam might be seen as distinct ?  Not sure - but we can probably increase our numbers in this manner

### Claude
Right — only the "between" zone carries signal. Let me sharpen your three cases:

| Origin zone | Phylogenetic signal for 105 topologies |
|-------------|----------------------------------------|
| Before deepest ambiguous node (all 5 clades have it) | Zero — invariant across topologies |
| Inside a single clade | Zero — clade-internal events don't depend on clade position |
| **Between** deepest ambiguous node and clade roots | **All** the signal lives here |

That middle zone is the effective-N that actually matters for ranking. For orthogroups alone, this will indeed be a fraction of 150K — maybe 5–20K depending on distribution, needs measurement.

**Feature-pooling idea is good and has prior art — but with caveats:**

Pooling heterogeneous features onto a tree is basically "total-evidence" or "supermatrix" phylogenetics — established since the 90s, exactly as you remembered. The hard part is independence. Here's a rough hierarchy I'd sketch:

- **Truly orthogonal** (measure different biological dimensions):
  - Orthogroups (sequence homology clusters)
  - Synteny blocks (physical arrangement — "where")
  - 3D/fold (structure)
- **Partially independent** (can be independent when carefully defined):
  - Pfam domains at the **per-domain** level for multi-domain proteins — a protein can lose one domain while keeping others; that's a distinct evolutionary event from losing the whole orthogroup
- **Not independent** (redundant with upstream sources):
  - GO terms (mostly inherited from Pfam/InterPro)
  - SMART vs Pfam (extensive overlap in domain calls)
  - SignalP/TM (function of sequence itself)

**Your double-counting instinct is right.** A workable rule: for each feature type, ask "what biological event's presence/absence does this measure?" If two feature types measure the same event (e.g., SMART and Pfam both catching the same kinase domain call), they're one vote, not two.

**Open design question:** do we *deduplicate* (pick one representative feature per biological event) or *weight down* (count redundant features fractionally)? Deduplication is cleaner but loses information. Weighting is more informative but harder to justify rigorously.

Where are you on that tradeoff — clean-and-defensible, or information-rich-and-calibrated?

---

### Eric
> Open design question: I'm not sure what you are saying here. In general, clean and rigorous is my preference

### Claude
Sorry, let me clarify with a concrete example:

Say a gene has a kinase domain. Pfam detects it. SMART also detects it. Both tools independently annotate the same biological feature. Two choices:

**Deduplicate** (your preference, based on "clean and rigorous"):
- Pick one canonical source (say, Pfam) as the authoritative caller for kinase domains
- Ignore SMART's annotation of that same kinase
- Clean, defensible: "one biological event = one character in the parsimony matrix"
- Cost: throws away cases where SMART catches something Pfam misses (or vice versa)

**Weight down:**
- Count the kinase domain once, but if both Pfam and SMART detect it, give it weight 1.5 or similar "confidence-weighted" score
- More information-rich but requires justifying the weighting scheme

**Clean-and-rigorous → deduplicate.** Locked in.

Implementation implication: we'd need a mapping of "which annotation tool is authoritative for which kind of feature" — a deduplication rule set. Simpler than it sounds: Pfam for domains, orthogroups for gene families, synteny blocks for physical arrangement, etc. A handful of non-overlapping categories rather than a hairy reconciliation problem.

Moving on — continue the brainstorm or want to pivot?

---

### Eric
> I think we do it at the level of data selection - given HMM annotations of domains - what single tool will we use - pick one. More sophisticated means might be brought to bear - sequences that only one tool annotations are included from any tool and all tools are given a rank order when more than one tool annotates a sequence - and we think the tools are operationally very similar in what they are evaluating

### Claude
That's clean and the right level of pragmatism. Let me restate to confirm:

**Dedup rule at data-selection level:**
1. Per category of annotation (e.g., "domain annotation", "signal peptide", "transmembrane"), define a canonical **rank order** of tools — e.g., `Pfam > SMART > SUPERFAMILY > PRINTS` for domains
2. For each sequence, check what each tool annotated:
   - If only one tool in the category hit it → include that annotation
   - If multiple tools in the same category hit the same feature → include only the highest-ranked tool's call
3. Different categories (domain vs signal peptide vs fold) are independent and ALL pass through — no cross-category deduplication needed

Result: for each sequence × feature, exactly one canonical presence/absence call per feature, drawn from the best tool that saw it.

**Implementation implication:** we need a documented annotation-tool-category table for GIGANTIC. Something like:

| Category | Rank-ordered tools |
|----------|---------------------|
| Domain | Pfam > SMART > SUPERFAMILY > PRINTS > ... |
| Signal peptide | SignalP > ... |
| Transmembrane | TMbed > DeepTMHMM > ... |
| Fold class | ... |
| Orthogroup | OrthoHMM > OrthoFinder > Broccoli (or however you want) |
| Synteny | (whatever tool you use) |

The rank order is an editable artifact — reviewer could ask "why Pfam over SMART?" and we'd answer in documentation.

Sound right? And is this rank-order table something we document in STEP_2's README, or does it live upstream (maybe in annotations_hmms or a project-level standard)?

---

### Eric
> I like this summary of this part of things - all of this is in STEP_2 - we don't need to think about documentation yet - still lots more brainstorming to do - but lets make a brainstorming.md file - and copy all of this conversation so far exactly in that document - and we can then continue

### Claude
_[This file is the result of that request. Continuing the brainstorm below.]_

---

## Continuing the brainstorm

### Eric
> You said: Point 2 (independence): You made a distinction I missed — you're talking about independence of origins, not independence of loss events. Origins are genuinely independent evolutionary events. Loss correlation is real but biases score magnitude more than ranking. I partly retract my concern. Partly — because co-loss across correlated orthogroups can still bias ranking toward trees where the correlation-generating lineages happen to cluster. But you're right that the origin-independence framing is the right unit of analysis.
>
> For losses and absences - there are three situations to consider - I'm forgetting my terminology but you might know from the code here - or the documentation. But I think it is absent, lost, missing - but lets discuss and refine these now.
>
> absent/absence is when an orthogroup or homology feature is not present because it has not yet appeared in the species tree in actual evolution. I made this term up - not sure what is used in the literature for mapping features onto species trees - can you research this and see if there is anything.
>
> lost/loss is used somewhat abiguously in the literature - there is the origin of the loss and then there are later mroe recent clades that also do not have the orthogroup or feature - and people will say these clades have lost it - which is true it is missing from the genome or the species etc - but the origin of the loss was earlier - and we carry about the origins of when features appear and when they are lost.  SO I use lost/loss for the node at which a feature is originally lost in a species tree - and missing for more recent clades that have inherited this loss - but I don't like the term missing - it seems to suggest a lack of certainty but we have high certainity that the loss is real - just that the loss occured in a deeper node

### Claude
Researching the terminology landscape, then GIGANTIC's own existing vocabulary, then proposing refinements:

**Literature conventions I can find:**

| Concept | Common terms in literature |
|---------|----------------------------|
| Feature never originated yet in this lineage (pre-origin) | "ancestral absence", "pre-origin absence", "primary absence", "not yet originated" |
| Node where a feature is first lost | "loss", "loss event", "gene loss event", "loss_at_origin" (less common) |
| Descendant inherits a prior loss | "secondary absence", "continued absence", "derived absence", "inherited absence", "descended loss" |

No widely-adopted canonical term for #1 (pre-origin absence) — you weren't alone in needing to coin. It's usually described as "not yet originated" rather than named as a state. **"Ancestral absence"** is the closest thing to a published convention.

**GIGANTIC's own vocabulary (already in STEP_1 code):**

The TEMPLATE_03 dual-metric tracking in script 003 uses exactly two of the three states:
- `loss_at_origin` = node where the feature is first lost
- `continued_absence` = descendants of a loss inheriting it

The third state (pre-origin absence) isn't given a name in the code — it's implicit in "orthogroup is not inherited in this lineage yet." Script 003 excludes these from loss accounting, which is correct.

**Proposed three-state system for STEP_2:**

| Your term | State meaning | Suggested refinement |
|-----------|---------------|----------------------|
| "absent/absence" | Pre-origin — feature hasn't arisen yet | **"Pre-origin absence"** or **"ancestral absence"** — both better than bare "absent" which reads ambiguous |
| "lost/loss" | Node where feature is first lost | **"loss_at_origin"** (already in GIGANTIC code) |
| "missing" (you dislike) | Descendant inheriting a prior loss | **"continued absence"** (already in GIGANTIC code, and exactly captures what you mean without the uncertainty flavor "missing" carries) |

**I'd argue for:**
1. **Pre-origin absence** (or ancestral absence — your preference) for state 1
2. **Loss** (or loss_at_origin when being formal) for state 2
3. **Continued absence** for state 3 — replaces "missing"

The word "missing" does carry a "we don't know if it's really gone" connotation, which isn't what you mean. "Continued absence" is already what the code calls it; it's neutral, descriptive, and captures the inheritance relationship directly.

**If we want maximum visual distinctness (for color-coding / UI later):**

| State | Short label | Color semantics (suggestion) |
|-------|-------------|------------------------------|
| Pre-origin absence | `pre_origin` | neutral (gray) — "not yet there" |
| Loss | `loss` | loss event color (red) — the moment of change |
| Continued absence | `inherited_loss` | faded loss color — the consequence |

Your reaction to dropping "missing" in favor of "continued absence"?

---

### Eric
> I greatly dislike this -Your reaction to dropping "missing" in favor of "continued absence"?
>
> I think we need words that are distinct around the evolutionary origin of the feature
>
> Inherited Abscence
> Lost/Loss
> Inherited Loss
>
> or something like this maybe?

### Claude
Much better. Your proposal has a clean symmetry — both "not-present" inheritance states get an `Inherited_*` prefix, distinguished by what's being inherited:

- **Inherited Absence** = inherited from the pre-origin state (never existed in this lineage)
- **Loss** = the node where the feature is first lost
- **Inherited Loss** = inherited from a derived loss state (existed, got lost upstream)

The "absence" vs "loss" word choice carries the distinction: absence = pristine never-had-it, loss = derived was-lost. The `Inherited_` prefix marks the state as ancestor-carried (no event at this node) vs. the node being where the event happened.

**Extending this to the full 5-state vocabulary for symmetry:**

| State | Meaning | Event or inheritance? |
|-------|---------|-----------------------|
| **Inherited Absence** | Pre-origin; feature has not yet arisen | inheritance |
| **Origin** | Node where feature first appears | event |
| **Inherited Presence** | Descendant of origin; conservation | inheritance |
| **Loss** | Node where feature is first lost | event |
| **Inherited Loss** | Descendant of a loss; "continued absence" | inheritance |

Two event states (Origin, Loss), three inheritance states (the three "Inherited_*"). Clean pairing:

- Pre-origin side: Inherited Absence → Origin → Inherited Presence
- Post-origin-loss side: Inherited Presence → Loss → Inherited Loss

**Mapping to existing GIGANTIC_1 code vocabulary (STEP_1 TEMPLATE_03):**

| New proposed term | Current code term |
|-------------------|-------------------|
| Inherited Absence | (no name in code — implicit) |
| Origin | "origin" |
| Inherited Presence | "conservation" |
| Loss | "loss_at_origin" |
| Inherited Loss | "continued absence" |

**Implications if we adopt:**
1. STEP_2 vocabulary uses the new terms natively (clean)
2. Eventually (separate work, not now) — migrate STEP_1 code terms to match, for project-wide consistency
3. Add `Inherited Absence` as an explicit accounted-for state (STEP_1 currently lumps it with "not inherited, ignored" — but maybe it should be counted for diagnostics?)

**Your reaction:**
- Does the 5-state full vocabulary fit what you had in mind?
- Is `Inherited Presence` the right pair for `Inherited Absence`/`Inherited Loss`, or would you rather keep `Conservation` to signal it's the "good" outcome?

---

### Eric
> I love the 5 states!  This may cause significant refactoring of STEP_1
>
> I think - outloud - to simplify terms
>
> Absence
> Origin
> Conservation
> Loss
> Gone

### Claude
The appeal is obvious — five one-word labels, readable, speakable. Let me raise three tensions before you lock it in:

**1. "Absence" alone is ambiguous.**
Without surrounding context, "absence" could mean any of the three not-present states. It doesn't immediately signal "pre-origin." Your `Inherited Absence` earlier was unambiguous; plain `Absence` loses that clarity.

**2. "Gone" is informal.**
Scientifically valid (like "species X has gone extinct"), but it reads colloquial in tables, figures, legends, and paper prose. Reviewers might flag it. Not a dealbreaker but worth choosing consciously.

**3. The symmetry you liked is lost.**
Your `Inherited_*` scheme paired the two "inherited" states explicitly:
- Inherited Absence ↔ Inherited Loss (both inheritance)
- Origin ↔ Loss (both events)

The simplified set breaks that:
- Absence | Origin | Conservation | Loss | Gone

Now `Conservation` sits alone as the only "Inherited" on the presence side, while `Absence` and `Gone` don't have an obvious shared structural relationship on the absence side. A reader has to know that `Absence` = pre-origin and `Gone` = post-loss — those words don't pair or signal that.

**Possible middle grounds:**

| Option | Flavor |
|--------|--------|
| A: Absence, Origin, Conservation, Loss, **Gone** | Your simplified; ambiguous absence + informal |
| B: **Pre-origin**, Origin, Conservation, Loss, **Post-loss** | Fully unambiguous, scientific, loses single-word elegance |
| C: **Absent**, Origin, Conservation, Loss, **Extinct** | Extinct is evocative but overloaded (species extinction vs orthogroup extinction) |
| D: **Naive**, Origin, Conservation, Loss, **Erased** | "Naive" for pre-experience is used in immunology — carries "not yet encountered" meaning well |
| E: **Inherited Absence**, Origin, Conservation, Loss, **Inherited Loss** | Your previous 5-state — verbose but crystal clear |

**My recommendation:** Option E. The two "Inherited" states being two-word is a small price for the clarity and symmetry. For tables where space is tight, you can always abbreviate: `IA | O | C | L | IL` as a secondary short code.

What lands for you?

---

### Eric
> In terms of accuracy - Conservation includes the origin of something.
>
> SO while I hate it, high accuracy would be
>
> Inherited Absence
> Origin
> Inherited Presence
> Loss
> Inherited Loss

### Claude
You're right and it's a real issue. "Conservation" in biology conventionally means "the feature is present across clades" — which includes the origin. Using it as a STATE label for just the post-origin descendants muddles the event/state distinction that the rest of the vocabulary takes pains to keep clean.

Option E (`Inherited Absence | Origin | Inherited Presence | Loss | Inherited Loss`) is the accurate answer. The symmetry is crisp:

| Absence side | Presence side |
|--------------|---------------|
| Inherited Absence (inherited state) | Inherited Presence (inherited state) |
| — | Origin (event) |
| Loss (event) | — |
| Inherited Loss (inherited state) | — |

Two events flanked by three inherited states, clean semantic pairs.

**For the aesthetic tax of the longer labels:** we can mitigate where readability matters most:

- **Figures/narrow tables**: use the shorthand `IA | O | IP | L | IL` with a legend row or caption
- **Code/column headers**: `inherited_absence | origin | inherited_presence | loss | inherited_loss` (snake_case) — matches existing GIGANTIC code conventions
- **Prose/documentation**: full names for unambiguity
- **Informal discussion (meetings, chat)**: people can still say "conservation" as long as they know it's colloquial for `inherited presence`; or "absence" / "gone" in casual speech

So formal vocabulary = Option E, everyday shorthand = whatever rolls off the tongue. The formal vocabulary is what defines the data; the casual names are just friendly handles.

**Locked in?**

Also worth flagging the STEP_1 refactoring implication: the current code vocabulary (`conservation`, `loss_at_origin`, `continued_absence`, implicit pre-origin) would shift to the new 5-state set. That's a meaningful but scoped refactor — not now, but worth a TODO in the brainstorming doc so we don't forget.

---

### Eric
> use words not abbreivations not letters etc
>
> I think for the algorithm - and for accurate discussion we have to use these 5 terms for their clarity and symmetry and consistency.
>
> However, in a general sense the analysis is origin, conservation, loss - I think this can still hold for general discussion and framing - or what do you think

### Claude
Yes, that tiering works cleanly — and it's already how GIGANTIC talks about itself. The subproject is **orthogroups_X_ocl** → **O**rigin-**C**onservation-**L**oss as the analytical umbrella. That framing is correct at the narrative level: we're studying when features appear (origin), persist (conservation), and disappear (loss).

**Two-tier vocabulary:**

| Tier | When used | Vocabulary |
|------|-----------|------------|
| **Framework / narrative** | Subproject names, paper framing, general discussion, figure titles | **O**rigin–**C**onservation–**L**oss (OCL) |
| **Formal / algorithmic** | Data columns, per-node state labels, precise methods text, code | **Inherited Absence** / **Origin** / **Inherited Presence** / **Loss** / **Inherited Loss** |

At the narrative level, "conservation" captures the whole positive side (origin + inherited presence) — which is what biologists mean colloquially when they say "this orthogroup is conserved in metazoans." At the data level, we need to distinguish the node of appearance from the descendants who inherit it, because those are different event types with different phylogenetic implications.

When we write methods or talk about the algorithm, we always use the 5-state words (full words, never abbreviations). When we introduce the work or frame it ("we study origin, conservation, and loss of orthogroups across..."), we use the 3-word umbrella.

Both are accurate at their level. The OCL umbrella doesn't contradict the 5 states — it's a coarser slice of the same reality.

**Proposal for the brainstorming doc:** explicitly capture this two-tier vocabulary as a design choice, so future readers (and our future selves) don't conflate the levels. Want me to append the vocabulary decisions to `brainstorming.md` now, or keep iterating and append in batches?

---

### Eric
> you can add the conversation verbatim to the brainstorming document - at the end of brainstorming we can have you generate a detailed summary and TODO

### Claude
_[Verbatim conversation appended to this document. Continuing the brainstorm below.]_

---

### Eric
> One other data type that overlaps with orthogroups but is also a different evolutionary scale / depth - gene families.
>
> some gene families will match an orthogroup - so we should filter these out based on ranking of say gene family > orthogroup - given expert knowledge and I would say greater rigor of gene family pipeline in gigantic - but maybe rigor is less - not sure what others will say.
>
> anyways - one limitation of orthogroups is how conservative they are - which is great - you get high-quality high-accuracy homolog detection across species.  But often times our natural focus is at a higher level of conservation - maybe all TRP ion channels not just TRP A ion channels (although I think there is a TRP orthogroup so need a better example here - but gene families can potential pull together deep conservation across orthogroups that otherwise are not recognized as being related to one another)
>
> operationally we could use gene family data similar to orthogroup data by pulling in the gene families at the level of AGS sequences and map these onto the species. Thus, again we avoid problems of alignment and treebuilding but still leverage the phylogenetic signal of homology across the species tree.

### Claude
Gene families as a third data type fits the framework cleanly — same mechanics (AGS-based presence/absence), different scale of signal, same alignment-free advantage. Natural extension.

**Where they add value that orthogroups miss:**
Gene families capture ancient homology that spans multiple orthogroup-level subfamilies. An ion-channel gene family's origin event sits at a DEEPER node than any of its constituent TRPA/TRPV/TRPC orthogroups' origins. For the 105 topology ranking, deeper events in the ambiguous zone carry just-as-useful signal for distinguishing topologies — and sometimes more, if the ambiguous nodes are themselves deep.

**Scale distinction — and the phylogenetic implication:**

| Level | Origin typically sits at | Signal for cteno/porifera/plac/cnid/bilateria ambiguous zone |
|-------|--------------------------|---------------------------------------------------------------|
| Gene family | Deep — often pre-Metazoan or Metazoan root | Often in the ambiguous zone → carries topology signal |
| Orthogroup | Shallower — usually within a clade or at a subfamily origin within Metazoa | May or may not — depends on origin depth |

So gene families are MORE LIKELY to contribute topology-relevant origin events than orthogroups on average, for the specific ambiguous nodes species70 permutes.

**On the dedup rule "gene family > orthogroup" — one refinement to consider:**

An orthogroup's origin can be at the same node as its parent gene family (redundant, drop) OR at a deeper/more-recent node than its parent (distinct event). Specifically, orthogroup origin ≥ gene family origin — never earlier, because the orthogroup is a subset of the family.

Cases:
- **Gene family origin in ambiguous zone, orthogroups with origins inside clades**: gene family wins, drop orthogroups (they contribute no topology signal anyway — origins inside clades are invariant across the 105)
- **Gene family origin before ambiguous zone, orthogroups with origins IN ambiguous zone**: KEEP the orthogroups, the gene family contributes no topology signal
- **Both have origins coinciding at the same ambiguous-zone node**: redundant, gene family wins

So the refined rule: **prefer the feature whose origin event lands in the ambiguous zone**. When both have ambiguous-zone origins at the same node → gene family wins (your preference, based on pipeline rigor). When one does and the other doesn't → keep the one that does.

This also naturally integrates with the 4/5 clade representation filter from earlier — features with origins in the ambiguous zone are exactly those with 4/5 or 5/5 representation (conserved across or past the deepest ambiguous node but with variation at shallower ambiguous nodes).

**Practical implication:** dedup has to be done at the *event* level (where does this feature's origin sit?) rather than at the *entity* level (is it a gene family or orthogroup?). Slightly more bookkeeping, cleaner signal.

Does that nuance land, or do you want to keep the simpler "gene family > orthogroup" rule and accept some signal loss?

---

### Eric
> Good thinking! So the refined rule: prefer the feature whose origin event lands in the ambiguous zone. When both have ambiguous-zone origins at the same node → gene family wins (your preference, based on pipeline rigor). When one does and the other doesn't → keep the one that does.
>
> Definitely at the event level - we want to leverage the best possible data relevant to the challenge whereever it may come from!
>
> The next thing with gene families is that it is a lot of work to accurately search the literature and come up with the required RGS sequences for input - please study the trees_gene_families if this is unfamiliar - I avoid lettered abbreviations but RGS, CGS, and AGS are exceptions in gigantic
>
> HOWEVER
>
> HUGO HGNC provides gene groups - see trees_gene_groups for details on this - there are nearly 2,000 gene groups - each one a set of genes in human that has been expert curated. Most of these are gene families or superfamilies - however some are functional sets of genes - maybe all ion channels for example (but need to double check on this) - and in the case of functional sets that maybe include different sets of complete gene families otherwise but the different families unrelated - but this could be tolerated - however they may also include incomplete sets of gene families unrelated to each other and this incompleteness will break the base assumption required for the GIGANTIC tree_gene_families algorithm to work.
>
> SO we have generated the HGNC gene group sequence sets for species70 using the trees_gene_families pipeline to generate HGNC AGS sequence sets - but we need to determine which ones are appropriate for the pipeline. I may have to do this by hand - probably just a long afternoon - I don't think there is a way to automated - I don't think there is any identifier or annotation in the database - I think I emailed HGNC at one point and the confirmed this a few years ago

### Claude
HGNC gene groups as a bootstrap source for gene family data is elegant — expert-curated, broad coverage, sidesteps the labor of building RGS sets from literature gene by gene. Let me make sure I understand the hazard properly:

**Why incomplete functional sets break the pipeline:**

The trees_gene_families algorithm (as I understand it from a quick read of the AGS/CGS/RGS convention) assumes the RGS captures the full homology scope of a family — every homolog in the target species genome should be findable from at least one RGS member via BLAST/HMM. If the HGNC group is an INCOMPLETE functional set (say, 6 of the 12 ion channel families), then:
- Real homologs in species genomes belonging to the 6 missing families won't be pulled in (no RGS seed to find them)
- These show up as "absent" when they're actually present, just unreachable from the RGS
- Signal becomes: "we see ion channels wherever the 6 seed families happen to reach" — confounded with RGS choice

For STEP_2's presence/absence signal, this is contaminating: an HGNC group with incomplete coverage would report false absences in species that have the family but a subfamily the RGS missed.

**Confirming the scope:** ~2000 HGNC groups total; the triage is deciding which are safe (bona fide gene families, even if broad superfamilies with full coverage) vs. risky (functional mixes with partial family representation). A one-afternoon manual curation pass for 2000 entries is ~8 seconds each — plausibly doable if you can skim a group's description and member list.

**On automating even partially:** A few programmatic heuristics that might pre-triage:

1. **Domain-architecture coherence**: pull Pfam profiles of each member gene in a group. If ≥90% of members share a dominant domain architecture → likely family. If domains are heterogeneous → likely functional mix. Easy to compute since annotations_hmms already runs.

2. **Orthogroup clustering of members**: for each HGNC group, check how its human members partition across your species70 orthogroups. If they cluster into 1 orthogroup → tight family. If they cluster into several small orthogroups that are clearly related (sharing a domain) → superfamily (still valid). If they scatter across many unrelated orthogroups → functional mix.

3. **Cross-reference HGNC group name/description**: regex for telltale functional descriptors like "receptors", "channels", "enzymes" (functional) vs. "family", "superfamily", "subunits" (likely structural family). Not deterministic but can pre-rank for review.

Combining these could reduce the manual review from "all 2000" to "review the ~200 ambiguous ones" — still an afternoon, but shorter. Not automated; just pre-sorted.

**For STEP_2 planning purposes** — can we assume: after triage, we'll have some subset of HGNC groups (~N bona fide families) whose AGS-based presence/absence data becomes feature input for the ranking? And this adds to orthogroups + Pfam domains as the three feature classes?

---

### Eric
> I don't think the automate methods are fool-proof/complete enough to leverage. The failures at edges are there - and the edges can be substantial / complex - so making more trouble I suspect in the end.
>
> that said - domains are next to discuss!
>
> gene groups are often hierarchical - so I can process often 5-20 at a time.
>
> For STEP_2 planning purposes  - ~N bona fide families to integrate with orthogroups for greater analysis of orthogroups and gene families - but for OCL
>
> there are also things like PANTHER Families within the InterProScan proteome annotation data for example in annotations_hmms - this should overlap or encompass HGNC gene groups - but I haven't explored this level of redundancy. I think the phylogenetic scope building PANTHER families in terms of initial seeding sequences and species is greater than HGNC - but maybe less comprehensive of the human genome. Again, not sure but there are features that made HGNC a good place to start within gigantic several years ago. So that it is HGNC and not yet Panther or other phylogenetic annotation tools of proteomes is more historical than best option

### Claude
Noted — manual triage it is. And the hierarchical batching (5–20 at a time) makes the afternoon more realistic. Useful to know.

**On HGNC vs PANTHER:**

This is a case where STEP_2's design shouldn't lock in to a specific source. What matters is the feature matrix (presence/absence per species per feature); the source can be:
- HGNC gene groups (now, historically)
- PANTHER families (from InterProScan — broader phylogenetic scope, maybe less complete for human)
- Expert-curated RGS sets (high quality, limited breadth)
- Future tools

**Design implication for STEP_2 input spec:**

STEP_2 should accept a feature matrix with columns like:
```
feature_id | feature_source | feature_type | species_1 | species_2 | ... | species_N
```

Where `feature_source` and `feature_type` are free-form metadata (HGNC / PANTHER / OrthoHMM / Pfam). The algorithm treats them uniformly — feeds them to the dedup rule (event-level) and the parsimony scorer. The source matters for:
- Dedup decisions (which source wins when overlapping)
- Provenance/traceability (which claim came from which tool)
- But NOT the scoring math — features are features

That way when PANTHER becomes the preferred gene-family source later, STEP_2 doesn't need rewriting — just swap the input feed.

**Bridge to domains:** PANTHER Families living inside InterProScan alongside Pfam is a natural segue. The InterProScan ecosystem produces multiple feature types (families, domains, sites, motifs, repeats, etc.) — and your rank-order dedup rule from earlier applies directly. Your move on domains.

---

### Eric
> the other thing with domains is that the are homology within proteins - but we are already leveraging the proteins themselves in orthogroups and gene families. Importantly, these two methods are leveraging blast or hmms - and at least blast is using only a small portion of the sequence in its evaluation for a threshold of inclusion or not.
>
> SO
>
> its possible or often likely that a pfam domain and a top blast hit in a gene family pipeline are leveraging the same sequence - meaning the same phylogenetic signal - making it a cryptic duplication and inflation artefact.  On the otherhand - for OrthoHMM maybe its HMMs are full-length sequences? I'm not sure - but also maybe it is just blast hits lined up to generate an HMM model. In which case - domain HMMs, orthohmm, and gene families may have cryptic duplications of phylogenetic signal.....
>
> HGNC we have no idea what was used - will varying widely and is unknowable.
>
> the only solution I guess would be to know coordinates of sequence signal - I've included this information in gigantic's parsing of annotation_hmms subproject - and I think it would be trivial to implement in a few hours for gene families (capturing the coordinates) - we could then assess for same sequence overlap across tools pulling on similar types of phylogenetic signal - but this is getting complicated - so for development purposes for now - can stick to each tool as a stand-alone assessment without integration. Can then compare tools to structure ranks and see what we think - this can probably inform / inspire for optimization and collapse/expansion of the subproject and workflow(s).

### Claude
Your concern is sharper than I credited earlier. The "category-level dedup" from before (Pfam wins domains, orthogroups wins families, etc.) assumes the categories don't overlap at the sequence level — but they do. A Pfam domain hit at residues 50–150 of gene X and a gene-family BLAST hit on the same gene X anchored on the same conserved region are the same phylogenetic signal reported twice. My earlier "truly orthogonal" hierarchy was too optimistic.

**Your coordinate-level solution is the principled answer, and it's deferrable:**

The proper dedup: intersect coordinate ranges per gene across tools. If Pfam call at [50,150] and gene-family BLAST hit at [40,160] overlap substantially, they're one signal. Pick the higher-ranked tool for that coordinate range, drop the other. This catches cryptic duplication the category-level rule misses.

But you're right to defer — implementing coordinate tracking in gene families + overlap-detection logic is meaningful engineering on top of STEP_2's already-substantial scope. Not now.

**Standalone-per-tool analysis as the development path is smart:**

Treating each tool's feature set as an independent parsimony analysis gives us:

1. **Per-tool structure ranking** — each tool produces its own top-ranked topology and confidence
2. **Cross-tool concordance** — if orthogroups AND gene families AND Pfam all vote structure_007, that's strong. If they disagree, we've found something
3. **Diagnostic value on disagreement** — where tools disagree, we can investigate whether tool-specific bias (HMM library coverage, BLAST window length, seed choices) explains the split
4. **Sensitivity check** — if structure_007 wins regardless of tool, the signal is robust. If different tools pick different winners, either we have genuine biological heterogeneity OR cryptic-duplication-adjusted methodology matters

That last point is actually a *better* outcome than integrating everything — if independent analyses converge, you have stronger evidence than a single integrated analysis could provide, because each tool contributes an independent perspective on the same question.

**Implication for STEP_2 design:**

STEP_2 becomes tool-parameterized: given a feature matrix from ANY tool (orthogroups / HGNC / Pfam / PANTHER / future), produce structure ranking with uncertainty. Run it multiple times (once per tool), then a thin downstream comparator reports:
- Per-tool top structure + uncertainty
- Concordance matrix across tools
- Consensus if any

Coordinate-level integration = future research direction (valuable enough to be a paper in itself — "how much of your gene-content phylogenetic signal is cryptically duplicated across annotation tools?").

**Before we move on** — one question: when you say "stick to each tool as a stand-alone assessment," do you mean:
(a) Run STEP_2 separately for orthogroups, separately for HGNC, separately for Pfam — 3 separate runs with 3 separate outputs
(b) Run STEP_2 once with a pooled feature matrix (tool is just metadata), and the COMPARISON happens downstream
(c) Something else

My instinct is (a) — cleaner per-tool output — but (b) is also defensible.

---

### Eric
> Definitely A - and for now just orthogroups!
>
> Lets capture the last part of the consersation - my brain is going to mush and I want to get the tables that should have finished a few hours ago to Leonid tonight.
>
> Capture brainstorm conversation verbatim
> Generate a summary - think deeply about it - turn it into a 2-5 page white paper and with a 300 word abstract at its start
> Generate a TODO list for STEP_1 and STEP_2
>
> and then lets check on the tables - if there is something I can send Leonid that would be great. And we can share the brainstorm documents with others.

### Claude
_[Verbatim conversation appended. Summary white paper and TODO list follow.]_
