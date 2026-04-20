# moroz_innovations

Subproject for computing clade-level "innovation" tables (Leonid's definition)
alongside GIGANTIC's formally-defined "origin-at-clade" tables.

## Terminology

This subproject intentionally maintains TWO distinct vocabularies:

**Innovation** (Leonid's operational definition) -- a feature is an "innovation
of clade X" when the feature's species presence pattern is restricted to clade X:

- `innovations_any(X)`: present in >=1 species of X AND absent from every
  species NOT in X
- `innovations_all(X)`: present in ALL species of X AND absent from every
  species NOT in X

Innovation is a **set-membership criterion** computed from species-presence
lists. It does NOT depend on the species tree topology (for clades whose
species content is stable across structures).

**Origin** (GIGANTIC's evolutionary definition) -- a feature's origin is the
phylogenetic block where the feature is inferred to have arisen, via the OCL
engine's MRCA algorithm. Origin IS topology-dependent.

These are NOT interchangeable. Innovation is a presence/absence summary.
Origin is an evolutionary inference on a specific species tree.

## Directory layout

```
moroz_innovations/
  README.md  (this file)
  BLOCK_moroz_innovations_analysis/
    workflow-COPYME-moroz_innovations_analysis/
      START_HERE-user_config.yaml
      RUN-workflow.sh
      INPUT_user/
      ai/
        scripts/001_ai-python-compute_innovations_and_origins.py
        conda_environment.yml
```

## Usage

1. Copy `workflow-COPYME-moroz_innovations_analysis` to `workflow-RUN_NN-...`
2. Edit `START_HERE-user_config.yaml` -- set `target_clades` (bare names),
   `target_structures`, and confirm `feature_sources` paths point at your
   orthogroups_X_ocl and annotations_X_ocl outputs.
3. `bash RUN-workflow.sh`

## Dependencies on other subprojects

- **trees_species** -- provides `clade_species_mappings-all_structures.tsv`
  (authoritative clade-to-species mapping per structure)
- **orthogroups_X_ocl** -- provides per-structure
  `4_ai-orthogroups-complete_ocl_summary.tsv`
- **annotations_X_ocl** -- provides per-structure
  `4_ai-structure_NNN_annogroups-complete_ocl_summary-all_types.tsv`

All three must have current output_to_input or OUTPUT_pipeline before running.
