# secretome — Per-Protein Secretome Identification

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 21 (initial; Moroz spec scoping)
AI:      Claude Code | Opus 4.7 | 2026 May 23 (BLOCK_secretome_evidence_table scaffold)
AI:      Claude Code | Opus 4.7 | 2026 May 25 (STEP_2-filter_secretome scripts)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent: [`../../README.md`](../../README.md) — gigantic_project-COPYME overview
- Subproject AI guide: [`AI_GUIDE.md`](AI_GUIDE.md)
- Reads from:
  - `../annotations_hmms/output_to_input/BLOCK_build_annotation_database/` — long-format standardized annotation DB
  - `../annotations_hmms/output_to_input/BLOCK_signalp/` — SignalP6 predictions (signal peptides)
  - `../annotations_hmms/output_to_input/BLOCK_deeploc/` — DeepLoc 2.0 predictions (TM + subcellular localization)
  - `../annotations_hmms/output_to_input/BLOCK_interproscan_parsed/pfam/` — Pfam domain annotations
  - `../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/` — proteomes
- Outputs to (`output_to_input/`):
  - `BLOCK_secretome_evidence_table/` — per-species wide evidence tables
  - `STEP_2-filter_secretome/` — per-species filtered secretome tables
  - `BLOCK_secretome_per_moroz_17may2026/` — (future, when scripted)
- Downstream consumers: comparative analyses, `upload_to_server/` (later)

---

## Purpose

Identify the secretome (proteins exported to extracellular space) across
the species70 set, using sequential KEEPER/DROPPER filters on
signal-peptide, membrane-topology/localization, and Pfam-domain-composition
annotations from the `annotations_hmms` subproject.

Per Moroz lab specification (2026-05-17).

## Architecture — three units

| Path | Type | Status | Purpose |
|------|------|--------|---------|
| `BLOCK_secretome_evidence_table/` | BLOCK (logically STEP_1 — see AI_GUIDE naming note) | Implemented (validate + scaffold for evidence-table builder) | Pivot the long-format `annotations_hmms` DB into one wide per-protein TSV per species |
| `STEP_2-filter_secretome/` | STEP_2 | Implemented (6 scripts: validate / 3 augmenters / filter / write_run_log) | Consume the evidence tables; augment with derived cols + orthogroups + top-10 BLAST; apply user-defined filters → per-species secretome |
| `BLOCK_secretome_per_moroz_17may2026/` | BLOCK (orthogonal — separate implementation track) | Scaffold only (awaiting upstream SignalP refresh) | Direct implementation of the Moroz 2026-05-17 spec with sequential KEEPER/DROPPER filters |

(See `AI_GUIDE.md` for the BLOCK-vs-STEP naming inconsistency and full
upstream-data table.)

## Prerequisites

- **annotations_hmms** complete (BLOCK_build_annotation_database +
  BLOCK_signalp + BLOCK_deeploc + BLOCK_interproscan with Pfam parser)
- **genomesDB** complete (proteomes for species70 phyloname headers)
- Conda envs auto-created on first run per workflow:
  - `aiG-secretome-build_evidence_table`
  - `aiG-secretome-filter_secretome`
  - `aiG-secretome-secretome_per_moroz_17may2026`
  (per-§28 strict form — three separate envs since each unit has
  distinct dependency needs)

## Quick Start

```bash
# Recommended sequence: build evidence tables, then filter
# 1. Build evidence tables (logically STEP_1)
cd BLOCK_secretome_evidence_table
cp -r workflow-COPYME-build_evidence_table workflow-RUN_1-build_evidence_table
cd workflow-RUN_1-build_evidence_table
vi START_HERE-user_config.yaml
bash RUN-workflow.sh

# 2. Filter to secretome (STEP_2)
cd ../../STEP_2-filter_secretome
cp -r workflow-COPYME-filter_secretome workflow-RUN_1-filter_secretome
cd workflow-RUN_1-filter_secretome
vi START_HERE-user_config.yaml
bash RUN-workflow.sh
```

The Moroz-spec branch (`BLOCK_secretome_per_moroz_17may2026/`) is a
scaffold awaiting upstream SignalP refresh — see its AI_GUIDE.md before
attempting to run.

## Documentation

| File | Purpose |
|---|---|
| `AI_GUIDE.md` | Subproject concepts, Moroz spec detail, naming-inconsistency note |
| `BLOCK_*/AI_GUIDE.md` and `STEP_2-*/AI_GUIDE.md` | Per-unit AI guide |
| `BLOCK_*/workflow-COPYME-*/README.md` and `.../ai/AI_GUIDE.md` | Workflow-level docs |
| `*/workflow-COPYME-*/START_HERE-user_config.yaml` | User-editable run configuration |

## Status (2026-05-26)

- `BLOCK_secretome_evidence_table/` — scaffold + validate implemented;
  evidence-table builder script designed but pending finalization.
- `STEP_2-filter_secretome/` — 6 scripts implemented and tested
  (augment with derived cols / orthogroups / blastp_top10 + filter + run log).
- `BLOCK_secretome_per_moroz_17may2026/` — scaffold only, awaiting fresh
  SignalP run from annotations_hmms.
