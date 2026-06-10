<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 09
Human:   Eric Edsinger
Purpose: User-facing runbook for the annotations_X_orthogroups workflow.
Scope:   workflow-COPYME-annotations_X_orthogroups.
============================================================================ -->

# Workflow: annotations_X_orthogroups

Integrates **pfam annogroups** with **orthogroups**, focused on
**non-bilaterian-only** orthogroups. Produces two tables.

## Where this fits

- Parent (BLOCK): [`../README.md`](../README.md) · [`../AI_GUIDE.md`](../AI_GUIDE.md)
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Inputs (all from upstream `output_to_input/`, set in `START_HERE-user_config.yaml`):
  pfam annogroups (`ocl_phylogenetic_structures/BLOCK_annotations_X_ocl`),
  orthogroups (`orthogroups/BLOCK_orthohmm_GIGANTIC`),
  Bilateria species set (`trees_species`)
- Outputs: `../../../output_to_input/BLOCK_annotations_X_orthogroups/<run_label>/`

## What you get

- **Table 1 — annogroups X orthogroups** (`OUTPUT_pipeline/3-output/`): one row
  per **kept annogroup**. An annogroup is kept when at least one of the
  orthogroups its member proteins fall into is **non-bilaterian-only**; annogroups
  whose orthogroups are all bilaterian-only are dropped. All of a kept annogroup's
  orthogroups are reported (non-bilaterian-only, bilaterian-only, and mixed), with
  per-class counts and ID lists, plus the annogroup's pfam accessions/definitions.
- **Table 2 — non-bilaterian-only orthogroups** (`OUTPUT_pipeline/2-output/`): one
  row per orthogroup whose member species contain **no bilaterian** (every member
  is a non-bilaterian metazoan or a non-metazoan outgroup).
- **Supporting** (`OUTPUT_pipeline/1-output/`): every orthogroup classified
  `bilaterian_only` / `non_bilaterian_only` / `mixed` (the basis for both tables).

The research question: *which pfam annotation groups are represented in
orthogroups confined to the non-bilaterian part of the tree?*

## Join model

The annogroup↔orthogroup link is **shared member proteins** (full GIGANTIC IDs).
Each protein belongs to exactly one annogroup (a clean single+combo partition) and
at most one orthogroup. "Non-bilaterian" = any species **not** in the Bilateria
clade (`C103_Bilateria`) — non-bilaterian metazoans AND non-metazoan outgroups.
This is a **structure-independent** integration (annogroup membership, orthogroup
membership, and the Bilateria species set are all invariant across the 105
species-tree structures), so there is no per-structure fan-out.

## Quick start

```bash
cd workflow-COPYME-annotations_X_orthogroups   # (copy to workflow-RUN_N for a real run)
# 1. Edit START_HERE-user_config.yaml: run_label, species_set_name,
#    annogroup_subtypes, execution_mode (+ slurm_account/slurm_qos if slurm),
#    input paths, bilateria_clade_id_name
# 2. Run:
bash RUN-workflow.sh
```

## Inputs / Outputs

| | Path | Notes |
|---|---|---|
| In | `inputs.annogroups_dir/<reference_structure>/1_ai-*-annogroups-{single,combo}.tsv` | annogroup member `Sequence_IDs` |
| In | `inputs.annogroups_dir/<reference_structure>/4_ai-*-complete_ocl_summary-all_types.tsv` | pfam accessions/definitions |
| In | `inputs.orthogroups_file` | headerless orthogroup membership |
| In | `inputs.bilateria_clade_species_mappings` (+ `bilateria_clade_id_name`) | Bilateria species set |
| Out | `OUTPUT_pipeline/1-output/1_ai-orthogroups-species_composition.tsv` | all orthogroups classified |
| Out | `OUTPUT_pipeline/2-output/2_ai-nonbilaterian_orthogroups.tsv` | Table 2 |
| Out | `OUTPUT_pipeline/3-output/3_ai-annogroups_X_orthogroups.tsv` | Table 1 |
| Out | `OUTPUT_pipeline/4-output/4_ai-validation_report.txt` | fail-fast validation (§36) |

## See also

- [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md) — pipeline wiring + execution detail
- [`../AI_GUIDE.md`](../AI_GUIDE.md) — BLOCK output schema + join model
