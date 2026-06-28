<!-- ============================================================================
AI:      Claude Code | Opus 4.8 (1M context) | 2026 June 28
Human:   Eric Edsinger
Purpose: User-facing overview of BLOCK_species_X_all_annotations.
Scope:   BLOCK_species_X_all_annotations.
============================================================================ -->

# BLOCK_species_X_all_annotations

Builds a **per-species proteome annotation table** — **one row per protein
sequence**, with every per-gene feature GIGANTIC produces joined onto it. The
spine is the proteome itself (genomesDB sequence id + amino acid sequence).

## Where this fits

- Parent (subproject): [`../README.md`](../README.md) · [`../AI_GUIDE.md`](../AI_GUIDE.md)
- This BLOCK's AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)
- Workflow: [`workflow-COPYME-species_X_all_annotations/`](workflow-COPYME-species_X_all_annotations/)
- Outputs: `../output_to_input/BLOCK_species_X_all_annotations/<run_label>/`

## What you get

For each protein in each species' proteome, one row with:

- **Identity / sequence** — full GIGANTIC ID, phyloname, Genus_species, length, amino acid sequence
- **gene_sizes** — gene / CDS / protein size
- **hotspots** — hotspot membership + paralog count
- **nr hits** — top 3 NCBI nr DIAMOND hit headers (with e-values)
- **annotations_hmms** — Pfam, InterPro-GO, PANTHER-GO, PANTHER family hits
- **annogroups** — pfam / go / panther annogroup membership
- **orthogroups** — orthogroup id + size + species count
- **secretome** — SignalP call/probability + DeepLoc localization
- **AGS membership** — trees_gene_groups + trees_gene_families gene set lists
- **dark_proteomes** — DARK / ANNOTATED status
- **per species-tree structure** — orthogroup OCL (origin block/path,
  conservation/loss/continued-absence) and pfam annogroup OCL (parallel lists)

The structure-invariant columns are built once (base table per species); the
OCL columns are added per species-tree structure (a full wide table per
structure), for the structures you list in the config (`all` or a list).

## In one sentence

Take every protein in every species' proteome and attach, in one wide table,
every annotation GIGANTIC has for it — so any protein can be read across all
axes (function, homology, orthology, secretion, gene-set membership, darkness,
and per-structure evolutionary origin) at a glance.

## Quick start

```bash
cd workflow-COPYME-species_X_all_annotations   # (copy to workflow-RUN_N for a real run)
# 1. Edit START_HERE-user_config.yaml:
#    - run_label, species_set_name
#    - structures (default: structure_001, 003, 032, 033; or "all")
#    - execution_mode (+ slurm_account/slurm_qos if slurm), input paths
# 2. Run:
bash RUN-workflow.sh
```

See [`workflow-COPYME-species_X_all_annotations/README.md`](workflow-COPYME-species_X_all_annotations/README.md)
for the runbook and [`AI_GUIDE.md`](AI_GUIDE.md) for the join keys + output schema.

## Coverage notes

- gene_sizes and hotspots cover 64 of 70 species (6 lack genome coordinates) —
  those proteins get `NA` + an availability flag, never a silent drop.
- annogroup **membership** is available for pfam, go, and panther; annogroup
  **OCL** is currently pfam-only (`species70_pfam`), so the per-structure
  annogroup-OCL columns are pfam-only.
- The spine reads from genomesDB STEP_4's canonical exposure
  `genomesDB/output_to_input/STEP_4-create_final_species_set/species70_gigantic_T1_sequence_tables/`.

## Status

Built 2026-06-28 — scaffold, scripts, and docs complete; **not yet run
end-to-end**. Set `slurm_account`/`slurm_qos` and launch from a `workflow-RUN_N`
copy.
