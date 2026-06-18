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

## How sources are added

One parser plugin per source: `ai/scripts/parsers/<source>.py` exposing
`SOURCE` and `parse_source_features(workflow_root, config) -> {sequence_id:
[Feature]}`. The four-type construction (Script 002) is shared and never changes.
The first parser is `pfam`. See [`AI_GUIDE.md`](AI_GUIDE.md) for the contract.

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
PASS). One known, user-accepted caveat: truncated multi-locus annotation IDs are
dropped — see [`workflow-COPYME-build_annogroups/ai/ai_FYIs/WARNING-truncated_orphan_annotations.md`](workflow-COPYME-build_annogroups/ai/ai_FYIs/WARNING-truncated_orphan_annotations.md).
