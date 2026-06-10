<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 09
Human:   Eric Edsinger
Purpose: User-facing overview of BLOCK_annotations_X_orthogroups.
Scope:   BLOCK_annotations_X_orthogroups.
============================================================================ -->

# BLOCK_annotations_X_orthogroups

Integrates **pfam annogroups** (annotation groups) with **orthogroups**, anchored
on shared member proteins and focused on **non-bilaterian-only** orthogroups.

## Where this fits

- Parent (subproject): [`../README.md`](../README.md) · [`../AI_GUIDE.md`](../AI_GUIDE.md)
- This BLOCK's AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)
- Workflow: [`workflow-COPYME-annotations_X_orthogroups/`](workflow-COPYME-annotations_X_orthogroups/)
- Inputs: pfam annogroups (`ocl_phylogenetic_structures/BLOCK_annotations_X_ocl`), orthogroups (`orthogroups/BLOCK_orthohmm_GIGANTIC`), Bilateria species set (`trees_species`) — see AI guide
- Outputs: `../output_to_input/BLOCK_annotations_X_orthogroups/<run_label>/`

## What you get

1. **Table 1 — annogroups X orthogroups** (one row per annogroup). An annogroup
   is **kept** when at least one of the orthogroups its member proteins fall into
   is **non-bilaterian-only**; annogroups whose orthogroups are all bilaterian-only
   are dropped. Every orthogroup of a kept annogroup is reported (non-bilaterian-only,
   bilaterian-only, and mixed) with per-class counts + ID lists + pfam
   accessions/definitions.
2. **Table 2 — non-bilaterian-only orthogroups** (one row per orthogroup): every
   orthogroup whose member species contain no bilaterian.

The research question: *which pfam annotation groups are represented in
orthogroups confined to the non-bilaterian part of the tree?*

## In one sentence

"Non-bilaterian" = any species **not** in the Bilateria clade (`C103_Bilateria`,
from `trees_species`) — non-bilaterian metazoans (ctenophores, sponges, cnidarians,
placozoans) **and** non-metazoan outgroups. The annogroup↔orthogroup link is
shared member proteins (full GIGANTIC IDs); the integration is
**structure-independent** (no per-structure fan-out).

## Quick start

```bash
cd workflow-COPYME-annotations_X_orthogroups   # (copy to workflow-RUN_N for a real run)
# 1. Edit START_HERE-user_config.yaml: run_label, annogroup_subtypes,
#    execution_mode (+ slurm_account/slurm_qos if slurm), input paths
# 2. Run:
bash RUN-workflow.sh
```

See [`workflow-COPYME-annotations_X_orthogroups/README.md`](workflow-COPYME-annotations_X_orthogroups/README.md)
for the runbook and [`AI_GUIDE.md`](AI_GUIDE.md) for the join design + output schema.

## Status

Built 2026-06-09 — scaffold, scripts, and docs complete; the join logic was
**validated end-to-end against real species70_pfam_X_OrthoHMM data** (validation
PASS). Server publishing (`upload_to_server/`) will be wired after first-run review.
