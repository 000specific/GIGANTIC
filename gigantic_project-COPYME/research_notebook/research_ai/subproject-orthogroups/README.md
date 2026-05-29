<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 27
Human:   Eric Edsinger
Purpose: AI-staged research notebook for the orthogroups subproject — the
         "thinking and reasoning" side, distinct from the operational
         subproject scaffold under subprojects/orthogroups/.
============================================================================ -->

# `subproject-orthogroups/` — research_ai notebook

This directory is the **research-notebook side** for the `orthogroups`
subproject. It holds design reasoning, methodological audits, and any
AI-staged artifacts that inform how orthogroup clustering is architected
across the GIGANTIC platform.

The **operational side** — NextFlow workflows, scripts, configs — lives
at:
- [`../../../subprojects/orthogroups/`](../../../subprojects/orthogroups/)

Currently the operational subproject contains `BLOCK_orthohmm/` (OrthoHMM
canonical run). Additional blocks for OrthoFinder, Broccoli, and OrthoVenn3
are anticipated as the multi-tool consensus strategy (this notebook) is
implemented.

---

## Project concept

**Orthogroups** is the foundation subproject for every downstream feature
analysis in GIGANTIC. Orthogroup quality directly shapes the validity of:

- `annotations_X_ocl/` — orthogroup-conditioned conservation/loss inference
- `orthogroups_X_species_tree/` — phylogenetic projection of OGs
- `trees_gene_groups/` — gene-tree inference within orthogroups
- `z_dark_sono/` and every other species-set-restricted subproject — uses
  flat OGs filtered by species membership

The architectural question that drives this notebook: **how should
orthogroup clustering be run when multiple subprojects analyze different
overlapping subsets of the species70 set?** Two options:

1. **Option A** — cluster once on the full species70, subsample per-subproject
2. **Option B** — re-cluster per subproject on its species subset

The strategy document `2026may27-orthogroup_clustering_strategy.md` captures
the deep-research evaluation of this question (across OrthoFinder, OrthoHMM,
Broccoli, OrthoVenn3) and the evolved design decisions: Option A wins, but
with specific architectural choices (flat OGs, not HOGs; slight
over-clustering preferred; HHsearch as superfamily-isolation backstop).

---

## Files in this directory

| File | Purpose | Status |
|------|---------|--------|
| `README.md` | This file | static |
| `2026may27-orthogroup_clustering_strategy.md` | Full strategy doc — research findings, design rationale, parameter recommendations, implementation knobs per tool | static, dated |

---

## History / provenance

- **2026-05-27** (Eric Edsinger + Claude Opus 4.7) — initial methodology
  audit for orthogroup clustering architecture across multiple subprojects.
  Two parallel deep-research agents surveyed the literature (Laumer
  hidden orthologs, Brassicaceae cross-tool benchmark, OrthoFinder HOG
  framework, QfO consensus) and the GitHub-issue trails for OrthoFinder,
  OrthoHMM, Broccoli, OrthoVenn3. Evolved into a conversation about why
  HOGs are not the right fit for GIGANTIC (unresolved species tree,
  gene-tree noise) and why slight over-clustering is preferred (orthogroup
  isolation breaks superfamily signal at the catalog level).

- **Upstream completed (prior to 2026-05-27):**
  - `genomesDB/` STEP_4 — species70 finalized; T1 proteomes + blastp DBs built
  - `orthogroups/` `BLOCK_orthohmm/` — first canonical OG run with OrthoHMM

---

## Related conversations

Look in `research_notebook/research_ai/sessions/` for the canonical
captured chat transcripts. The 2026-05-27 orthogroup strategy
conversation will appear there once captured (via the PreCompact hook
or a "Save Chat!" trigger).

---

## Future additions to this notebook

As the multi-tool consensus strategy is implemented, this directory may
grow to include:

- `mcl_inflation_audit-YYYYmonthDD.md` — empirical comparison of
  OrthoFinder/OrthoHMM at inflation 1.5 (default) vs 1.2–1.3 (over-clustered)
  on the species70 set
- `hhsearch_superfamily_backstop-YYYYmonthDD.md` — design + results of
  the HMM-vs-HMM cross-OG comparison pass for superfamily recovery
- `cross_tool_consensus-YYYYmonthDD.md` — comparison of OrthoFinder /
  OrthoHMM / Broccoli outputs on species70; intersection (strict) and
  union (discovery) sets

Anything that lives here is a deliberate, dated artifact. Ephemeral
exploratory work belongs in
`research_notebook/research_user/subproject-orthogroups/` instead (create
on demand).
