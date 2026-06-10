<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 04
Human:   Eric Edsinger
Purpose: User-facing overview of BLOCK_orthogroups_ocl_X_features.
Scope:   BLOCK_orthogroups_ocl_X_features.
============================================================================ -->

# BLOCK_orthogroups_ocl_X_features

Integrates the **OCL orthogroup analysis** (Origin/Conservation/Loss per
phylogenetic species-tree structure) with three per-gene feature sources —
**dark proteome**, **hotspots**, and **secretome** — anchored on each
orthogroup's member sequence IDs.

## Where this fits

- Parent (subproject): [`../README.md`](../README.md) · [`../AI_GUIDE.md`](../AI_GUIDE.md)
- This BLOCK's AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)
- Workflow: [`workflow-COPYME-orthogroups_ocl_X_features/`](workflow-COPYME-orthogroups_ocl_X_features/)
- Inputs: OCL orthogroups + dark/hotspot/secretome `output_to_input/` (see AI guide)
- Outputs: `../output_to_input/BLOCK_orthogroups_ocl_X_features/<run_label>/`

## What you get (per species-tree structure)

1. **Integrated orthogroup summary** — one row per orthogroup: OCL origin +
   conservation/loss, plus how many (and which) member genes are dark / in a
   hotspot / secreted.
2. **Block-state expanded** — the same, broken out per node where the
   orthogroup originated (O), is conserved (P), or was lost (L).
3. **Gene-level drill-down** — one row per member gene with its dark / hotspot /
   secretome status and secretome evidence (SignalP, DeepLoc, Pfam).

The research question it answers: *do orthogroups with a particular evolutionary
origin / conservation / loss pattern preferentially contain secreted, dark, or
hotspot genes?*

## Quick start

```bash
cd workflow-COPYME-orthogroups_ocl_X_features    # (copy to workflow-RUN_N for a real run)
# 1. Edit START_HERE-user_config.yaml: run_label, species_set_name,
#    execution_mode (+ slurm_account/slurm_qos if slurm), input paths
# 2. Edit INPUT_user/structure_manifest.tsv (structure IDs to integrate)
# 3. Run:
bash RUN-workflow.sh
```

See [`workflow-COPYME-orthogroups_ocl_X_features/README.md`](workflow-COPYME-orthogroups_ocl_X_features/README.md)
for the full runbook and [`AI_GUIDE.md`](AI_GUIDE.md) for the integration design
and output schema.

## Status

Built 2026-06-04 — scaffold, scripts, and docs complete; join logic validated
against real ID strings. **Not yet run end-to-end** (the full run is heavy I/O
and should be launched on SLURM). Server publishing
(`upload_to_server/`) will be wired after first-run review.
