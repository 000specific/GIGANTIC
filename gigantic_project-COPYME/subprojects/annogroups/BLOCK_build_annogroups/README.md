<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 18
Human:   Eric Edsinger
Purpose: User-facing overview of BLOCK_build_annogroups.
Scope:   BLOCK_build_annogroups.
============================================================================ -->

# BLOCK_build_annogroups

Builds the four canonical annogroup types — **feature**, **combination**,
**architecture**, **absent** — **per annotation source**, from `annotations_hmms`
outputs and the species-set proteome universe.

## Where this fits

- Parent (subproject): [`../README.md`](../README.md) · [`../AI_GUIDE.md`](../AI_GUIDE.md)
- This BLOCK's AI guide (the parser contract): [`AI_GUIDE.md`](AI_GUIDE.md)
- Workflow: [`workflow-COPYME-build_annogroups/`](workflow-COPYME-build_annogroups/)
- Inputs: per-source annotations (`annotations_hmms/output_to_input/`), proteome universe (`genomesDB/output_to_input/STEP_4-…`)
- Outputs: `../output_to_input/BLOCK_build_annogroups/<species_set>/<source>/`

## What you get

Per source, two tables:

1. **`2_ai-<source>-annogroup_map.tsv`** — one row per annogroup (all four
   types): the type, its defining features, and member sequence/species counts.
2. **`2_ai-<source>-annogroup_membership.tsv`** — one row per
   `(sequence, annogroup)`: the full GIGANTIC protein ID, its `Genus_species`,
   the annogroup, the type, and (for architecture rows) the coordinate-tagged
   ordered features.

Plus a per-source validation report and a dropped-orphan audit file.

## In one sentence

For each source, every sequence's parsed features become memberships in
`feature` (one per distinct feature), `combination` (the alphabetical distinct
feature set), and `architecture` (the N→C ordered positional-feature pattern,
grouped coord-free); every proteome sequence with no feature from the source
goes to `annogroup_<source>_absent`.

**`combination` is whole-protein** (the feature *set*, position-independent);
**`architecture` is sub-protein** (the *ordered* arrangement along the sequence,
which needs residue coordinates). A source whose annotations have no sub-protein
coordinates cannot form an architecture and yields only 3 types (feature +
combination + absent) — e.g. **GO** and **DeepLoc**. Positional sources (pfam,
panther) yield all four.

## How sources are added

One parser plugin per source: `ai/scripts/parsers/<source>.py` exposing
`SOURCE` and `parse_source_features(workflow_root, config) -> {sequence_id:
[Feature]}`. The four-type construction (Script 002) is shared and never changes.
Parsers implemented: **pfam** and **panther** (positional → 4 types) and **go**
(whole-protein → 3 types; reads the raw InterProScan results, origin selectable via
the `go_term_origins` config knob). See [`AI_GUIDE.md`](AI_GUIDE.md) for the contract.

## Quick start

```bash
cd workflow-COPYME-build_annogroups   # (copy to workflow-RUN_N for a real run)
# 1. Edit START_HERE-user_config.yaml: species_set_name, sources,
#    execution_mode (+ slurm_account/slurm_qos if slurm), input paths
# 2. Run:
bash RUN-workflow.sh
```

See [`workflow-COPYME-build_annogroups/README.md`](workflow-COPYME-build_annogroups/README.md)
for the runbook and [`workflow-COPYME-build_annogroups/ai/AI_GUIDE.md`](workflow-COPYME-build_annogroups/ai/AI_GUIDE.md)
for the execution detail.

## Status

Built 2026-06-18 — scaffold, scripts, docs, and the NextFlow workflow complete.
**pfam validated end-to-end** against real species70 data (137,762 annogroups:
10,635 feature + 46,846 combination + 80,280 architecture + 1 absent; validation
PASS).

**2026-06-28: expanded to 12 sources, all validated end-to-end** (full DAG,
species70, validation PASS — universe 1,375,926 sequences). Total annogroups per
source (feature / combination / architecture):

| Source | annot% | feature | combination | architecture |
|--------|-------:|--------:|------------:|-------------:|
| pfam | 67.0 | 10,635 | 46,846 | 80,280 |
| panther | 69.6 | 11,033 | 11,033 | 11,051 |
| gene3d | 61.1 | 3,289 | 25,748 | 50,886 |
| cdd | 28.5 | 11,239 | 18,657 | 26,037 |
| smart | 31.4 | 1,171 | 10,974 | 35,042 |
| superfamily | 58.4 | 1,412 | 18,386 | 37,579 |
| funfam | 23.1 | 36,784 | 51,917 | 56,422 |
| go | 60.8 | 8,994 | 27,974 | — |
| deeploc | 100.0 | 10 | 177 | — |
| signalp | 12.0 | 1 | 1 | — |
| tmbed | 29.4 | 3 | 7 | 122 |
| metapredict | 78.7 | 1 | 1 | 85 |

(`—` = whole-protein source, no architecture. signalp/metapredict feature counts are
small by nature: one signal-peptide type called in species70, one generic `IDR`
accession; tmbed's 3 = TM_helix / beta_barrel / signal_peptide. go carries 6
GO-aspect split columns.)

One known, user-accepted caveat: truncated multi-locus annotation IDs are
dropped — see [`workflow-COPYME-build_annogroups/ai/ai_FYIs/WARNING-truncated_orphan_annotations.md`](workflow-COPYME-build_annogroups/ai/ai_FYIs/WARNING-truncated_orphan_annotations.md).
