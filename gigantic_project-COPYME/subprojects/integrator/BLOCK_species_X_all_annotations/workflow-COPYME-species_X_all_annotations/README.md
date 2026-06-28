<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 28
Human:   Eric Edsinger
Purpose: User-facing runbook for the species_X_all_annotations workflow.
Scope:   workflow-COPYME-species_X_all_annotations.
============================================================================ -->

# Workflow: species_X_all_annotations

Builds a **per-species proteome annotation table**: one row per protein, every
per-gene feature joined onto it. Structure-invariant features once; OCL columns
per species-tree structure.

## Where this fits

- Parent (BLOCK): [`../README.md`](../README.md) · [`../AI_GUIDE.md`](../AI_GUIDE.md)
- This workflow's AI guide: [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md)
- Inputs (all from upstream `output_to_input/`, including the spine from
  `genomesDB/output_to_input/STEP_4-create_final_species_set/species70_gigantic_T1_sequence_tables/`; set in `START_HERE-user_config.yaml`)
- Outputs: `../../../output_to_input/BLOCK_species_X_all_annotations/<run_label>/`

## What you get

- **Per-species base tables** (`OUTPUT_pipeline/1-output/_shared/`): one row per
  protein, every structure-invariant feature joined (gene sizes, hotspots, top-3
  nr hits, Pfam / IPR-GO / PANTHER-GO / PANTHER, pfam/go/panther annogroup
  membership, orthogroup id+size, secretome, gene-group/family AGS membership,
  dark status). Plus a `feature_availability_summary.tsv`.
- **Per-structure wide tables** (`OUTPUT_pipeline/2-output/<structure>/`): the
  base columns plus that structure's orthogroup-OCL and pfam-annogroup-OCL
  columns — a full wide table per species per structure.
- **Validation report** (`OUTPUT_pipeline/3-output/`): fail-fast cross-checks.

## Join model

The spine is the genomesDB proteome (one row per protein). Most sources join on
the full GIGANTIC protein id; gene_sizes and hotspots join on the bare `g_` gene
field within a species. Multi-row sources (annotations_hmms, annogroups) collapse
into per-protein lists; hotspots and orthogroups are inverted (member → gene).
AGS membership is read from the gene-group / gene-family FASTA headers. Only the
OCL columns depend on the species-tree structure — those are added per structure
in Phase 2. See [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md) and [`../AI_GUIDE.md`](../AI_GUIDE.md).

## Quick start

```bash
cd workflow-COPYME-species_X_all_annotations   # (copy to workflow-RUN_N for a real run)
# 1. Edit START_HERE-user_config.yaml: run_label, species_set_name,
#    structures (all | list), execution_mode (+ slurm_account/slurm_qos),
#    input paths
# 2. Run:
bash RUN-workflow.sh
```

## Inputs / Outputs

| | Path | Notes |
|---|---|---|
| In | `inputs.spine_dir` | genomesDB STEP_4 per-species sequence tables (spine) |
| In | `inputs.gene_sizes_dir` / `inputs.hotspots_dir` | per-species; join on bare `g_` field (64/70) |
| In | `inputs.nr_hits_dir` | per-species nr top hits |
| In | `inputs.hmms_databases_dir` | pfam / go / panther consolidated tables |
| In | `inputs.annogroups_dir` | pfam / go / panther annogroup membership |
| In | `inputs.orthogroups_file` | headerless orthogroup membership |
| In | `inputs.secretome_dir` / `inputs.dark_dir` | per-species secretome / dark proteome |
| In | `inputs.gene_groups_ags_root` / `inputs.gene_families_ags_root` | AGS FASTA roots |
| In | `inputs.orthogroups_ocl_dir` / `inputs.annogroup_ocl_dir` (+ run labels) | per-structure OCL |
| Out | `OUTPUT_pipeline/1-output/_shared/<phyloname>-proteome_annotations-base.tsv` | invariant base, per species |
| Out | `OUTPUT_pipeline/2-output/<structure>/<phyloname>-proteome_all_annotations.tsv` | full wide, per structure |
| Out | `OUTPUT_pipeline/3-output/3_ai-validation_report.txt` | fail-fast validation (§36) |

## See also

- [`ai/AI_GUIDE.md`](ai/AI_GUIDE.md) — pipeline wiring + execution detail
- [`../AI_GUIDE.md`](../AI_GUIDE.md) — BLOCK join keys + output schema
