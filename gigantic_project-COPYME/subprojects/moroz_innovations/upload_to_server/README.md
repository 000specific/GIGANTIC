# moroz_innovations — published outputs

**State**: test run (1 of 105 phylogenetic species-tree structures computed; `structure_001` only).

The `BLOCK_moroz_innovations_analysis/workflow-COPYME-moroz_innovations_analysis/structure_001/1-output/`
tree below contains six TSVs from a development run of the innovations + origins
computation. The workflow itself is still in COPYME (template) state — a full
RUN across all 105 structures has not yet been executed.

## Two vocabularies, kept distinct

This subproject deliberately maintains two separate vocabularies side-by-side
(see `subprojects/moroz_innovations/README.md` for the canonical text):

- **Innovation** (Leonid's operational definition) — a feature is an
  "innovation of clade X" when its species-presence pattern is restricted
  to clade X. Set-membership criterion. Topology-independent.

- **Origin** (GIGANTIC's evolutionary definition) — a feature's origin is
  the phylogenetic block where it is inferred to have arisen via the OCL
  engine's MRCA algorithm. Topology-dependent.

These are NOT interchangeable. Innovation is a presence/absence summary;
origin is an evolutionary inference on a specific species tree.

## Files (structure_001 only)

| File | Vocabulary | Feature type |
|---|---|---|
| `1_ai-structure_001-clade_innovations_any_species_orthogroups.tsv` | innovation (any species) | orthogroups |
| `1_ai-structure_001-clade_innovations_any_species_annotations.tsv` | innovation (any species) | annogroups |
| `1_ai-structure_001-clade_innovations_all_species_orthogroups.tsv` | innovation (all species) | orthogroups |
| `1_ai-structure_001-clade_innovations_all_species_annotations.tsv` | innovation (all species) | annogroups |
| `1_ai-structure_001-clade_ocl_origins_orthogroups.tsv` | origin (GIGANTIC OCL) | orthogroups |
| `1_ai-structure_001-clade_ocl_origins_annotations.tsv` | origin (GIGANTIC OCL) | annogroups |

## Caveat

Until a full RUN is executed and rolled out to all 105 structures, downstream
comparisons across structures are not possible from these files alone. Use
with the test-run framing in mind.
