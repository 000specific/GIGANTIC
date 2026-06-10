# TODO: STEP_1 and STEP_2

## BLOCK_ocl_analysis

### Now (blocker for current species70 run)
- [ ] **Debug validation failure in structure_003** (script 005): orthogroup count mismatch
      (139628 vs expected 170027). Root-cause likely single-species orthogroups being dropped
      silently. Decide whether the validator or the upstream filter is wrong. 2 validation
      checks failing — review `5_ai-validation_error_log.txt` for the full list.
- [ ] **Re-run RUN_01 with fix** to generate complete per-structure 4-output summaries for
      all 105 structures (94 completed before fail-fast halted).

### Near-term (blocks STEP_2)
- [ ] **Adopt 5-state event vocabulary project-wide**: migrate `conservation`,
      `loss_at_origin`, `continued_absence`, and implicit pre-origin absence in scripts
      003 / 004 / 005 to the new explicit vocabulary (`Inherited Absence`, `Origin`,
      `Inherited Presence`, `Loss`, `Inherited Loss`).
- [ ] **Surface pre-origin absence as an explicit accounted-for state** (currently
      implicit / ignored). Diagnostically useful for understanding why some features
      contribute no topology signal.
- [ ] **Ensure per-feature topology-contingent loss decomposition is available** in
      `4-output/` summaries (STEP_2 needs this, not just the aggregate).
- [ ] **Add feature classification to complete_ocl_summary**: is this feature topology-
      invariant, topology-discriminating (ambiguous-zone origin), or not-applicable?
      STEP_2 will filter by this.

### Deferred
- [ ] Vocabulary migration may require refactoring STEP_1 scripts — scope separately.
- [ ] Coordinate tracking in trees_gene_families for future coordinate-level dedup.

## STEP_2-occams_tree

### Design (documented; not yet coded)
- [x] Scope confirmed: orthogroups only, for now
- [x] Per-tool standalone execution (Option A — one run per tool, compare downstream)
- [x] 5-state event vocabulary locked in
- [x] Two-tier vocabulary: OCL for narrative, 5-state for algorithm / code
- [x] Source-agnostic feature matrix input spec (columns include `feature_source`,
      `feature_type`)
- [x] Dedup at event level, not entity level (feature whose origin lands in the
      ambiguous zone wins)
- [x] Tie-handling / subsample confidence intended (bootstrap-analog)

### Near-term (first implementation)
- [ ] **Define the input feature matrix spec**: `feature_id | feature_source |
      feature_type | origin_zone | species_1 | ... | species_N`. Loaded from STEP_1's
      per-structure summaries.
- [ ] **Implement total-loss aggregator**: per topology, sum Loss events across all
      features. Output: `structure_ranking.tsv` with columns `structure_id | total_loss
      | rank | is_user_tree`.
- [ ] **Implement 4/5 clade representation filter**: features present in 4 of 5
      unresolved clades are "discriminating"; included. 5/5 features are "controls";
      tracked separately for diagnostics. Features with <4/5 either rejected or
      flagged for LBA-at-clustering risk.
- [ ] **Implement bootstrap-analog subsampling**: N subsamples of features,
      recompute ranking, report per-topology "ranked first in X% of subsamples".
- [ ] **Per-topology detail table**: `per_structure_loss_detail.tsv` — which features
      contributed how many losses to each structure's score. Essential for diagnosis.

### Medium-term
- [ ] **Validation harness**: run on data where answer is known (within-mammals,
      within-arthropods) — confirm recovery of expert-accepted clade resolution.
- [ ] **Sensitivity analysis to lineage-specific loss rates**: partition features by
      loss-rate quintile, rerun, check ranking stability. Required for publishability.
- [ ] **Gene families integration** (once HGNC triage is done; uses same STEP_2 logic).
- [ ] **Domains integration** (Pfam via annotations_hmms output).

### Future work (research direction in itself)
- [ ] **Cross-tool concordance analysis**: after per-tool runs, implement concordance
      matrix + consensus top-ranked topology.
- [ ] **Coordinate-level dedup**: add sequence-coordinate tracking to gene families +
      Pfam, detect cryptic duplication of phylogenetic signal at the sequence level.
      Own publication.
- [ ] **Weighting experiments**: unweighted vs clade-depth-weighted vs feature-
      importance-weighted loss counts. Quantify effect on ranking.
- [ ] **Null distribution / significance**: permutation null for ranking; confidence
      that top-ranked topology is meaningfully better than a random tree.
- [ ] **STEP_LEONID / STEP_3-gigantic_data_diver** integration: once rankings are
      stable, expose queryable interface for collaborator-driven exploration.

---

_End of brainstorming document for STEP_2-occams_tree design session 2026-04-14._
