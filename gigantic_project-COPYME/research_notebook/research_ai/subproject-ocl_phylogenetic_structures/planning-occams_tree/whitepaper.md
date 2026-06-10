# White Paper: Phylogenetic Species Tree Inference via Genome-Scale Homology-Feature Parsimony

**Working title for the STEP_2-occams_tree method.** Draft synthesis of brainstorming session 2026-04-14.

## Abstract

We propose **STEP_2-occams_tree**, a species-tree inference method that scores candidate
topologies by the total number of evolutionary loss events their branching patterns require
to explain the observed presence/absence distribution of genome-wide homology features across
a species set. The method operates at the GIGANTIC_1 framework's orthogroup, gene-family, and
domain levels — each treated as an independent "unit of evolution" — and sidesteps the
well-known limitations of sequence-alignment-dependent phylogenomic methods by treating the
homology feature as the phylogenetic character, not the sequence within it. Candidate
topologies are enumerated from user-flagged ambiguous nodes via a prior pipeline step
(trees_species: all (2N-3)!! binary resolutions of N unresolved clades), and each candidate
is scored by its minimum-loss accounting under a five-state event vocabulary (Inherited
Absence / Origin / Inherited Presence / Loss / Inherited Loss) that refines classical Dollo
parsimony's event types. Ranking is robust to several well-known failure modes of classical
approaches: sequence-level rate heterogeneity is bypassed entirely at the unit of analysis;
topology-invariant error is a shared constant across candidates and cancels out of ranking;
and law-of-large-numbers averaging across thousands of independent origins reduces the
impact of any individual feature's noise. Outputs include a per-topology total-loss ranking,
per-feature topology-contingent loss decomposition, and bootstrap-analog subsample
confidence. The method is designed as a complement — not replacement — for alignment-based
phylogenomics, particularly for contested deep nodes where sequence signal breaks down and
for organismal groups where rate heterogeneity undermines standard assumptions. Per-tool
(per-feature-class) execution allows cross-tool concordance to serve as an additional
layer of confidence: when orthogroup-based, gene-family-based, and domain-based rankings
converge on the same topology, the evidence multiplies; when they diverge, the method
surfaces the discordance as scientific data rather than hiding it.

---

## 1. Motivation

Species tree inference at genome scale has entered a regime where traditional alignment-based
methods hit three compounding problems:

1. **Alignment quality** — as species sets broaden and deepen, multiple sequence alignment
   becomes inconsistent for fast-evolving regions and highly divergent homologs. Downstream
   trees inherit alignment error.
2. **Rate heterogeneity** — evolutionary rates vary enormously across species and genes;
   even with partition / mixture models, deep nodes and long-branch taxa remain contested
   (the cteno/sponge deep-branching debate being a contemporary example).
3. **Underutilized annotation** — billions of compute-cycles go into generating genome
   annotations (InterProScan, Pfam, TM/signal-peptide prediction, orthology assignment,
   gene family curation). Typically well under 1% of that information is used for any
   given phylogenetic question.

Alignment-free phylogenetic signal classes have emerged — 3D structure comparison (limited
by database coverage and structural convergence), synteny blocks (elegant for rare/derived
events, unclear generalization). This proposal adds a complementary signal class:
**parsimony over homology-feature presence/absence, evaluated across enumerated candidate
topologies.**

## 2. Core Method

**Inputs:**
- A species set (e.g., species70 in the reference GIGANTIC_1 instance)
- A partially-resolved species tree from the user, with N clades flagged as "unresolved"
- Genome-scale homology features: orthogroups (OrthoHMM / OrthoFinder / Broccoli), gene
  families (HGNC / PANTHER / expert RGS), protein domains (Pfam / SMART / etc.)

**Candidate topology enumeration (STEP trees_species, prior step):**
- The (2N-3)!! binary resolutions of the N unresolved clades. For N=5 this is 105.
- `structure_001` is reserved for the user's input topology.

**Per-feature Origin-Conservation-Loss (OCL) analysis (STEP_1):**
- For each candidate topology and each feature, classify each tree node as one of five
  states (see Section 4 vocabulary).
- Count Loss events per topology per feature.

**Tree scoring (STEP_2):**
- Aggregate Loss events across all features per topology.
- Rank topologies by ascending total-loss score — lowest-loss topology is most parsimonious.
- `structure_001` (user's input tree) is simply one of the candidates — it may or may not
  rank first, and its ranking is itself a diagnostic.

**Confidence via subsampling:**
- Subsample features, recompute rankings, observe stability of the top-ranked topology.
- Report: "topology_X ranked first in Y% of subsamples" and/or ties / near-ties.

## 3. The Ambiguous-Zone Insight

Not all features contribute to topology differentiation. Only features whose origin event
lands *between* the deepest unresolved node and the clade roots provide topology signal.

| Origin zone | Contribution to ranking |
|-------------|-------------------------|
| Before deepest unresolved node (all clades have it) | Zero — invariant |
| Inside a single clade | Zero — clade-internal events don't depend on clade position |
| Between deepest unresolved node and clade roots | All the differentiating signal |

Practically, topology-discriminating features have **4/5 or near-4/5 clade representation**
(present in most but not all unresolved clades, forcing loss accounting to depend on where
the missing clade sits). Features with 5/5 representation act as noise-reducing controls
(they should score identical across topologies; if not, that's a diagnostic).

## 4. Event Vocabulary (5-State Formal Set)

| State | Meaning | Event or Inheritance |
|-------|---------|----------------------|
| Inherited Absence | Pre-origin; feature has not yet arisen | inheritance |
| Origin | Node where feature first appears | event |
| Inherited Presence | Descendant of origin; conservation | inheritance |
| Loss | Node where feature is first lost | event |
| Inherited Loss | Descendant of a loss; continued absence | inheritance |

Two events (Origin, Loss) flanked by three inherited states. This vocabulary refines
classical Dollo parsimony by explicitly separating pre-origin absence from post-loss
inherited absence — distinct biological meanings that standard Dollo conflates.

For narrative framing the umbrella term **Origin-Conservation-Loss (OCL)** is retained; the
5-state set is used for data columns, per-node labels, and methods text.

## 5. Novelty Claims (Bounded)

What is **not new**: parsimony itself. Dollo parsimony. Gene-content phylogenetics (long
tradition in microbial COG/KEGG analyses). Ancestral state reconstruction.

What **is new** (as an integrated approach):
- **Orthogroup-as-phylogenetic-unit** — alignment-free because the feature is the
  clustering-level entity, not the sequence
- **5-state event accounting** — standard Dollo flattens inherited-absence vs
  inherited-loss; we preserve the distinction, which matters for downstream hypothesis
  testing about pre-origin absences
- **Constrained candidate space** — ranking against enumerated, structurally meaningful
  topologies (the (2N-3)!! resolutions from trees_species) rather than unconstrained tree
  search — tractable and interpretable
- **Per-tool standalone execution** — orthogroups / gene families / domains each generate
  an independent ranking; cross-tool concordance is emergent evidence rather than forced
  integration
- **Integrated GIGANTIC architecture** — the pipeline composes cleanly with the upstream
  phylogenetic feature extraction in trees_species and the annotation subprojects,
  providing end-to-end reproducibility at genome scale

## 6. Robustness Analysis

| Concern | Robustness argument |
|---------|---------------------|
| Sequence rate heterogeneity | Unit of analysis is the feature, not the sequence. Heterogeneity within a feature's member sequences doesn't propagate to the parsimony score. |
| Lineage-specific high loss rates | Topology-invariant losses are a shared constant across all 105 candidates → cancel out of ranking. Only topology-contingent losses differentiate. |
| Correlated losses (genome-assembly quality, chromosome region co-loss, pathway co-loss) | Bias score magnitude but typically not ranking. Independence argument for the method is about origins (genuinely independent events), not about absences. |
| LBA at the clustering stage (rapid-evolvers pulled into phantom orthogroups) | Real concern. Mitigated by requiring ≥4/5 clade representation for inclusion (the discriminating-signal criterion) — most phantom orthogroups won't satisfy this. |
| Incomplete genomes / failed annotations | Real. Mitigated by scale (noise averages across thousands of features) and by cross-tool concordance (same signal should appear in orthogroups AND gene families if genuine). |
| Cryptic phylogenetic signal duplication across tools | Real. Deferred to future work — coordinate-level dedup proposed but not in the initial implementation. Per-tool standalone analysis allows diagnostic cross-tool comparison in the meantime. |

## 7. Validation Plan

Before deploying for contested nodes, the method must recover **known-resolved clades**
from the same dataset. Mammalian relationships within species70 are well-resolved; if the
method fails there, the deep-node claim is moot. Validation checks:
1. Within clade-level species, does the rank-one topology recover expert-accepted resolution?
2. Across orthogroups / gene families / domains (STEP_2 per-tool runs), is concordance
   high where biology is settled?
3. For the known-contested ambiguous nodes (cteno/sponge/placozoa placement), how does
   ranking stability compare to alignment-based methods' bootstrap support?

## 8. Scope and Limitations

- Depends on the user's confidence that species are assigned to the correct unresolved
  clade (species-to-clade membership). Internal clade topology errors are tolerated.
- Bounded by the (2N-3)!! candidate space — if the true tree requires permuting a node
  the user did not flag as unresolved, the method picks best-among-wrong.
- Per-tool standalone analyses are the initial deliverable; pooled and coordinate-dedup'd
  integrations are future work.

## 9. Relationship to Prior Art

This method sits alongside and complements, not replaces:
- **Alignment-based phylogenomics** (RAxML, IQ-TREE) — primary method for most cases;
  struggles at the deep/rapid boundary
- **Coalescent methods** (ASTRAL) — orthogonal data (gene tree distributions); doesn't
  address alignment quality
- **Synteny phylogenomics** (Simakov/Rokhsar) — complementary alignment-free signal;
  targets rare/derived events vs. our common/abundant events
- **Classical Dollo parsimony at gene-content level** (COG-based microbial work) — direct
  methodological ancestor; we refine event accounting and operationalize at modern
  animal-genome scale

---
