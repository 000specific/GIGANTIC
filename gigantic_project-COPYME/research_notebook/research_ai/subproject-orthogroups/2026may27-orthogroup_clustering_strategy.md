<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 27
Human:   Eric Edsinger
Purpose: Strategy document for orthogroup clustering architecture across
         multiple GIGANTIC subprojects. Captures the initial deep-research
         findings (OrthoFinder/OrthoHMM/Broccoli/OrthoVenn3 + the
         subsample-vs-recluster methodology literature) and the evolved
         design decisions: flat OGs (not HOGs), slight over-clustering,
         HHsearch as superfamily-isolation backstop.
============================================================================ -->

# Orthogroup clustering strategy — 2026-05-27

This document is the durable record of the methodology audit that
underpins GIGANTIC's orthogroup architecture. It synthesizes the
literature (Laumer hidden orthologs, Brassicaceae cross-tool benchmark,
OrthoFinder HOG framework, QfO consortium consensus), the GitHub-issue
trail for the four candidate tools, and the design conversation that
followed.

The strategy applies platform-wide: the `orthogroups/` subproject is the
foundation that every species-set-restricted downstream subproject
(`z_dark_sono/`, `annotations_X_ocl/`, `trees_gene_groups/`, etc.)
inherits orthogroup definitions from.

---

## 1. Executive summary

**Decision**: Run orthogroup clustering ONCE on the full species70 set
per tool (OrthoFinder, OrthoHMM, Broccoli). Each downstream subproject
gets a **filtered view of the flat orthogroups** with species70-level
metadata retained.

**Reasoning** (compressed):
- Dense species sampling rescues real orthologs that sparse sets fragment
  into spurious singletons (Laumer 2017 demonstrated this empirically:
  3,427 hidden orthologs in flatworms recovered via bridge species)
- OrthoFinder's HOG framework is the textbook answer but fails in
  GIGANTIC's context because (a) the species70 species tree is unresolved
  — `trees_species/` produces up to 105 candidate structures, so feeding
  one resolved tree to OrthoFinder is methodologically ill-defined; (b)
  gene-tree noise from FastTree-default propagates into HOG splits
- Flat orthogroups with species70-level metadata preserve the
  dense-sampling benefit without inheriting gene-tree errors
- **Slight over-clustering is preferred** (lower MCL inflation) because
  the asymmetric cost of orthogroup isolation: it's cheap to split an
  over-clustered OG with a targeted gene tree later, but expensive to
  merge under-clustered OGs that should share a superfamily
- **HHsearch / HHblits between per-OG HMMs** is the recommended backstop
  for any OG split that should have stayed together (OrthoHMM produces
  these HMMs for free as a side-effect of its algorithm)

---

## 2. The research question

The user has ~70 high-quality annotated genomes (BUSCO ≥95% target —
species70 is the canonical set; species88 and other candidate sets exist
for adjacent projects). Multiple subprojects analyze different
overlapping subsets:

- `z_dark_sono/` — ion-channel candidates without human orthologs
- `annotations_X_ocl/` — orthogroup-conditioned origin/conservation/loss
- `orthogroups_X_species_tree/` — OG projection onto species phylogeny
- Future subprojects — TBD

The methodological question: **cluster once and subsample, or cluster
per subset?** Specifically:

**Option A** — Run ONE clustering on all 70 species; each subproject
post-filters orthogroups to its species set. Retain species70-level
metadata so an apparent singleton in a 20-species subset is annotated
as part of a larger orthogroup at the full-resolution level.

**Option B** — Run clustering SEPARATELY on each subproject's species
subset.

Initial hypothesis: Option A gives more robust cluster formation (more
sequences → better cluster boundaries, fewer spurious singletons).
Initial concern: different tools and parameters give different
orthogroups, so post-hoc subsampling might violate methodological
soundness.

---

## 3. Initial deep research — findings

Two parallel research agents surveyed (a) tool-specific behavior across
OrthoFinder / OrthoHMM / Broccoli / OrthoVenn3 and their GitHub issue
trails, and (b) the methodological literature on orthogroup inference
stability under varying species sampling. The key findings:

### 3.1 Hidden-ortholog rescue (Laumer et al. 2017)

The single most directly-relevant empirical study:
[doi:10.1101/gr.216226.116](https://doi.org/10.1101/gr.216226.116).

Orthology pipelines run on sparsely-sampled clades fragment
rapidly-evolving genes into spurious singletons. Adding intermediate
"bridge" species via transitive homology recovered **3,427 putative
hidden orthologs** in 29 flatworm lineages. OrthoFinder alone on the
sparse set found 82.7% of these; HaMStR found just 2 of 75 in
*Schmidtea mediterranea*.

**Mechanism**: rapidly-evolving orthologs need intermediate-divergence
species to bridge similarity gaps. Without them, they fragment into
apparent singletons.

**Implication for GIGANTIC**: Option A's intuition is correct. Dense
sampling at the clustering stage materially improves orthogroup
recovery; it is not a marginal optimization.

### 3.2 Cross-tool agreement is moderate-to-poor (Beric et al. 2025)

Brassicaceae 8-genome benchmark of OrthoFinder, SonicParanoid, Broccoli,
OrthNet: [doi:10.1002/aps3.11627](https://doi.org/10.1002/aps3.11627).

- Exact orthogroup composition agreement: **51–66%** (diploids only),
  **29–44%** (with polyploids)
- Jaccard similarity stays high (0.7–0.9), but exact identity is rare
- *"No two algorithms produced identical orthogroup gene compositions
  for every orthogroup inferred."*

**Implication for GIGANTIC**: Running multiple tools on the same species
set will produce substantially different orthogroup catalogs. The
"right" answer is not a single tool's output; it is a multi-tool
analysis where intersection = high-precision and union =
high-recall views.

### 3.3 OrthoFinder HOGs as the "textbook" answer

OrthoFinder ≥2.4 writes `Phylogenetic_Hierarchical_Orthogroups/N0.tsv`,
`N1.tsv`, ... — one TSV per internal node of the rooted species tree.
For a subproject's species subset, find the MRCA node and read the
corresponding `Nk.tsv`. Orthogroups at each node are inferred from rooted
gene trees, not from post-hoc filtering of the flat catalog.

Key numbers from
[Emms & Kelly 2019, doi:10.1186/s13059-019-1832-y](https://doi.org/10.1186/s13059-019-1832-y):
- HOGs are 12–20% more accurate than flat orthogroups on OrthoBench
- Adding outgroup species gives a further ~20% accuracy gain

OrthoFinder v3 (2025 preprint,
[doi:10.1101/2025.07.15.664860](https://doi.org/10.1101/2025.07.15.664860))
adds `--core` + `--assign` (SHOOT algorithm) for adding species without
re-clustering. The documentation explicitly endorses the "include
outgroups + use HOG files for your clade" workflow.

**This is the textbook answer to the user's question.** Section 4
explains why it was rejected for GIGANTIC's context.

### 3.4 Per-tool species-set sensitivity

**OrthoFinder**: HIGH dependence. Pairwise bit-score normalization is
species-pair-specific (2015 paper); HOG inference is rooted-species-tree
dependent. Changing the species set changes the tree, changes normalization,
changes HOG splits. The `--core` + `--assign` workflow exists precisely
because the maintainers recognize re-clustering produces different
results.

**OrthoHMM**: MODERATE-HIGH dependence at the graph stage
(phmmer + MCL), LOWER at the per-OG HMM stage. The initial all-vs-all
connectivity graph differs when species are added/removed; HMM profiles
built per OG are functions of which sequences landed in that initial
cluster.

**Broccoli**: PRESENT but redundancy-buffered. Label-propagation on the
orthology network benefits from network density; the paper's robustness
claim is design-philosophical rather than empirically validated.
[GitHub issue #11](https://github.com/rderelle/Broccoli/issues/11) (63
butterfly species, only ~400 single-copy OGs) and
[#15](https://github.com/rderelle/Broccoli/issues/15) (reproducibility
concerns with `ratio_ortho`) flag real limits.

**OrthoVenn3**: inherits whatever engine you select (OrthoFinder or
OrthoMCL). Not a backbone tool — it's a visualization layer with a Venn
UI, intended for small comparative sets.

### 3.5 QfO consortium guidance (Altenhoff et al. 2024)

[doi:10.1093/nargab/lqae167](https://doi.org/10.1093/nargab/lqae167)
explicitly declines to crown a single best method:

> *"deciding which method is the best depends on which aspect is
> considered most important"*

Methods sit on a precision/recall Pareto frontier. The multi-tool
posture is therefore the principled scientific choice.

---

## 4. Why HOGs were rejected for GIGANTIC

The textbook answer (Section 3.3) fails in GIGANTIC's specific context.
Three independent reasons:

### 4.1 The species70 species tree is unresolved

`trees_species/` is built around the explicit recognition that the input
species tree has ambiguous/polytomy zones, and the pipeline enumerates
candidate resolutions: up to **105 binary `structure_NNN` variants** per
unresolved input. The whole `trees_species/` architecture exists because
"the" species tree is not knowable.

HOG inference requires committing to a single resolved species tree.
Options:
- Pick one structure → bake an arbitrary phylogenetic choice into every
  orthogroup definition
- Run OrthoFinder 105 times → infeasible computationally and analytically

Both are bad. Flat orthogroups (Section 5) sidestep this entirely.

### 4.2 Gene-tree noise propagates into HOG splits

OrthoFinder defaults to FastTree for per-OG gene trees. Across ~20–30k
orthogroups with mixed-quality 70-species inputs, FastTree-default trees
have many weakly-supported nodes. HOG splits at those nodes inherit the
noise. The OrthoBench accuracy gains were measured on curated reference
trees, not on real heterogeneous datasets.

### 4.3 Multi-tool consensus becomes apples-to-oranges

Only OrthoFinder offers HOGs. OrthoHMM, Broccoli, and OrthoVenn3 all
produce flat orthogroups. Using OrthoFinder HOGs + flat OGs from three
other tools forces an analysis mismatch that has to be reconciled
artificially. Treating OrthoFinder as a flat-OG producer keeps the
four-tool consensus internally consistent.

---

## 5. Why slight over-clustering is preferred

A recognized weakness of every orthogroup approach is **orthogroup
isolation**: closely-related families end up in separate bins with no
programmatic link back to their shared superfamily. Pfam's clan system
and EggNOG's hierarchical levels exist precisely because of this.

The information cost is asymmetric:

| Operation | Cost | When needed |
|-----------|------|-------------|
| **Split** an over-clustered OG later | Cheap, targeted — gene tree on one OG | Only when biologically motivated |
| **Merge** under-clustered OGs later | Expensive, global — re-clustering or all-vs-all HMM-vs-HMM comparison across every OG pair | Required every time the OG catalog changes |

Lump-first-split-selectively is the more defensible direction, and it is
coherent with the rest of GIGANTIC's design: detailed phylogenetics done
per-OG-of-biological-interest (`trees_gene_groups/`, `trees_gene_families/`),
not catalog-wide.

For the user's downstream analyses (presence/absence across species
tree, conservation/loss inference), over-clustered orthogroups still
give meaningful signals: "gene family X is present in Cnidaria" remains
a true statement even when paralog X1 and X2 are lumped in one OG.

---

## 6. HHsearch as the superfamily-isolation backstop

Profile-profile comparison between per-OG HMMs detects related OGs that
got split during clustering. Use cases:

- A tool over-splits a known superfamily despite inflation tuning
- A specific downstream subproject needs superfamily-level grouping that
  isn't apparent at the OG-pair level

**Why this is cheap in GIGANTIC**: OrthoHMM produces per-OG HMMs as a
side-effect of its algorithm. They live in `BLOCK_orthohmm/`'s output and
are immediately consumable by HHsearch / HHblits without re-building.

This is a **backstop, not a replacement** for over-clustering. The
catalog-level lump-first design still drives clustering; HMM-vs-HMM is a
targeted recovery pass for the specific OGs where lumping wasn't
sufficient.

---

## 7. Recommended strategy

### 7.1 Architecture

```
species70 (canonical set)
   │
   ├── BLOCK_orthohmm/    ← OrthoHMM (current canonical run)
   ├── BLOCK_orthofinder/ ← OrthoFinder (planned)
   ├── BLOCK_broccoli/    ← Broccoli (planned)
   │
   ├── flat orthogroups per tool, with species70 metadata retained
   │     • orthogroup_id
   │     • full species70 membership list
   │     • full species70 sequence count
   │     • per-tool consensus tags (added by downstream consensus pass)
   │
   ├── HHsearch per-OG HMM-vs-HMM     ← superfamily backstop, on demand
   │
   └── output_to_input/  → consumed by downstream subprojects with
                            per-subproject species filtering applied
                            in post-processing
```

Each downstream subproject (`z_dark_sono/`, `annotations_X_ocl/`,
`orthogroups_X_species_tree/`) reads the full-species70 orthogroup
tables, filters to its species subset for the analysis at hand, but
**always reports species70-level orthogroup statistics** alongside
subset-level statistics. This avoids the silent inflation of "loss"
calls that would result from treating subset singletons as biological
singletons.

### 7.2 Per-tool parameter recommendations

| Tool | Parameter | GIGANTIC choice | Rationale |
|------|-----------|-----------------|-----------|
| OrthoFinder | `-I` (MCL inflation) | **1.2–1.3** (down from default 1.5) | Larger OGs; preserve superfamily signal |
| OrthoFinder | `-M dendroblast` vs `-M msa` | dendroblast for speed; msa for quality re-run | Cost-quality tradeoff |
| OrthoFinder | `-s species_tree_file` | **DO NOT** feed a resolved tree | Forces HOG path; conflicts with `trees_species/` design |
| OrthoFinder | HOG outputs | **Ignore** — use only flat `Orthogroups.tsv` | See Section 4 |
| OrthoHMM | `-i` (MCL inflation) | **1.2–1.3** (same direction) | Match OrthoFinder choice for apples-to-apples consensus |
| OrthoHMM | per-OG HMMs | **Retain** for HHsearch backstop | Side-effect of algorithm; cheap to keep |
| Broccoli | `-ratio_orthologs` | Default for now; flag if reproducibility issues persist | [Issue #15](https://github.com/rderelle/Broccoli/issues/15) noted concerns |
| OrthoVenn3 | — | **Skip as backbone**; use only for final per-subproject Venn visualization | Wrapper, not a primary tool |

### 7.3 Downstream metadata convention

Every orthogroup row in any per-tool output table should carry, at
minimum:

```
orthogroup_id
species70_member_count           ← canonical, from full clustering
species70_member_species_list    ← comma-delimited, full
species70_sequence_count
subset_member_count              ← computed per downstream subproject
subset_member_species_list
subset_sequence_count
tool_source                      ← orthofinder | orthohmm | broccoli
consensus_tag                    ← strict | majority | discovery
```

This is the metadata-retention discipline that makes Option A
methodologically sound: a subset singleton always carries its full
species70 context, so downstream code never silently mistakes "absent
from my subset" for "biologically lineage-restricted."

### 7.4 Cross-tool consensus interpretation

Per Beric et al. (Section 3.2), inter-tool agreement is moderate. Report
both:
- **Intersection (strict)** — orthogroups whose composition agrees across
  all 3 tools. Publication-grade, high-precision.
- **Union (discovery)** — orthogroups present in at least 1 tool.
  Discovery-grade, high-recall.
- **Majority (consensus-of-2)** — middle ground for routine analyses.

Never silently filter by consensus without flagging which tool(s)
supported each orthogroup. Per QfO consortium guidance, no single tool
is universally best; the "right" set depends on the downstream task's
precision/recall priority.

---

## 8. Open questions / future research

These items are deferred but worth flagging:

1. **Empirical inflation audit** — Does inflation 1.2–1.3 measurably
   preserve more known superfamily relationships on species70 compared
   to default 1.5? Concrete test: count OGs that capture both
   `Ion_trans` (PF00520) and `Ion_chan` (PF07885) Pfam domains together
   vs separately at different inflation values.

2. **HHsearch threshold tuning** — What HHsearch probability or e-value
   threshold reliably identifies "should have stayed together" OG pairs
   without inflating false superfamily merges? Calibrate against known
   Pfam clan groupings on species70.

3. **Polyploid-rich subprojects** — Beric showed cross-tool agreement
   collapses with polyploids. Does GIGANTIC have any planned subprojects
   that would need per-subset re-clustering despite the general Option A
   stance? If so, document the exception explicitly.

4. **Ancient paralog detection** — Even with over-clustering, some flat
   OGs will contain ancient paralogs. Profile-level diagnostics (copy-number
   variance across species, bimodal within-OG identity, OG size outliers)
   should be standard QC outputs, even if no automatic splitting is done.

5. **Reconciling with existing `BLOCK_orthohmm/` run** — The current
   canonical OG run was made at default inflation. Re-running at lower
   inflation has downstream cost (every dependent subproject re-validates).
   Worth doing once if the empirical audit (item 1) shows clear
   superfamily-recovery gains; not worth doing speculatively.

---

## 9. References

**Primary literature**
- Laumer et al. 2017, *Genome Research* — hidden orthologs in flatworms:
  [doi:10.1101/gr.216226.116](https://doi.org/10.1101/gr.216226.116)
- Emms & Kelly 2015, *Genome Biology* — OrthoFinder algorithm:
  [doi:10.1186/s13059-015-0721-2](https://doi.org/10.1186/s13059-015-0721-2)
- Emms & Kelly 2019, *Genome Biology* — OrthoFinder phylogenetic inference:
  [doi:10.1186/s13059-019-1832-y](https://doi.org/10.1186/s13059-019-1832-y)
- Emms & Kelly 2025 bioRxiv — OrthoFinder v3:
  [doi:10.1101/2025.07.15.664860](https://doi.org/10.1101/2025.07.15.664860)
- Derelle et al. 2020, *MBE* — Broccoli:
  [link](https://academic.oup.com/mbe/article/37/11/3389/5865275)
- Beric et al. 2025, *Applications in Plant Sciences* — Brassicaceae
  cross-tool benchmark:
  [doi:10.1002/aps3.11627](https://doi.org/10.1002/aps3.11627)
- Altenhoff et al. 2024, *NAR Genomics & Bioinformatics* — QfO benchmark:
  [doi:10.1093/nargab/lqae167](https://doi.org/10.1093/nargab/lqae167)

**Tool repositories**
- OrthoFinder: https://github.com/davidemms/OrthoFinder
- OrthoHMM: https://github.com/JLSteenwyk/orthohmm
- Broccoli: https://github.com/rderelle/Broccoli
- SHOOT: https://github.com/davidemms/SHOOT
- OrthoVenn3: https://orthovenn3.bioinfotoolkits.net/

**Relevant GitHub issues** (000generic, OrthoFinder repo)
- [#891 (Apr 2024)](https://github.com/davidemms/OrthoFinder/issues/891)
  — "Orthogroups vs Superfamily Family Tree" — directly addresses the
  orthogroup-isolation concern that drives the Section 5 design choice
- [#942 (Nov 2024)](https://github.com/davidemms/OrthoFinder/issues/942)
  — "More species with lower quality genomes finishes faster"
- [#943 (Nov 2024)](https://github.com/davidemms/OrthoFinder/issues/943)
  — "Are there HOG alignments and gene trees in OrthoFinder output?"
- [#955 (Dec 2024)](https://github.com/davidemms/OrthoFinder/issues/955)
  — "Adding more species takes less time - unclear why?"
- [#724 (Jul 2022)](https://github.com/davidemms/OrthoFinder/issues/724)
  — "Setting Blastp evalue and other parameters"

**Relevant GitHub issues** (Broccoli repo)
- [#11](https://github.com/rderelle/Broccoli/issues/11) — low single-copy
  OGs on 63 butterfly species
- [#15](https://github.com/rderelle/Broccoli/issues/15) —
  `ratio_ortho` parameter reproducibility concerns

---

## 10. Provenance

This document was produced 2026-05-27 in a Claude Code Opus 4.7 session
with Eric Edsinger. The conversation included:

1. Two parallel research agents conducting deep web research (tool-specific
   behavior + GitHub issues; methodology literature)
2. A pushback-and-refine discussion that rejected the textbook HOG answer
   on the basis of GIGANTIC's unresolved species tree and gene-tree noise
3. An evolved design preference for slight over-clustering motivated by
   the orthogroup-isolation problem (closely-related OGs cannot find each
   other after clustering — a real, named weakness of every flat-OG
   approach, documented in Pfam clans and EggNOG hierarchical levels)
4. A GitHub-issue verification pass for the user's prior SHOOT inquiry
   (none found under 000generic; the closest existing issue is the user's
   own #891 on the superfamily-family-tree problem, which is directly
   relevant to the Section 5 design choice)

The full chat transcript will be captured to
`research_notebook/research_ai/sessions/` via the standard hook
mechanism.
