# AI_GUIDE: secretome

**For AI Assistants**: Read the project-level guide (`../../AI_GUIDE-project.md`) first for GIGANTIC overview, directory structure, and general patterns. This guide covers the `secretome` subproject specifically.

> **Build location note** (May 2026): This subproject is currently being developed at `~/secretome/` because `/blue/` is out of space. Once space is restored, contents will be rsync'd into `gigantic_project-COPYME/subprojects/secretome/` (stub to be created) and absolute paths in `START_HERE-user_config.yaml` will be swapped to relative paths.

## Quick Reference

| User needs… | Go to… |
|---|---|
| GIGANTIC overview, directory structure | `../../AI_GUIDE-project.md` |
| Subproject concepts, output schema | This file |
| Running the workflow | `BLOCK_secretome_per_moroz_17may2026/workflow-COPYME-secretome_per_moroz_17may2026/ai/AI_GUIDE-secretome_per_moroz_17may2026_workflow.md` |

## Purpose

Identify the secretome (proteins exported to extracellular space) across the species70 set, using sequential KEEPER/DROPPER filters on signal-peptide, membrane-topology/localization, and Pfam-domain-composition annotations. Each script's KEEPER output is the input to the next script.

This is the first BLOCK of the subproject: `BLOCK_secretome_per_moroz_17may2026` — defined per Moroz lab specification on 2026-05-17.

## Status (as of 2026-05-21)

**Scaffold only — no scripts written yet.** Awaiting two pieces of data from `annotations_hmms` before scripting can resume:

| Upstream | Status | Notes |
|---|---|---|
| **SignalP6** on species70 | 🟡 Pipeline rerunning at `~/temporary_annotations/BLOCK_signalp/` (SLURM job `32899825`, moroz-b burst, fast mode, started 2026-05-21 03:58 — pending on a SLURM reservation until ~08:29 today, then 9-wide parallel for ~70 species) | Previous attempt produced 2/70 species. Awaiting fresh full-coverage output. |
| **DeepLoc 2.0** on species70 | ✅ Complete, 70/70 species | Lives at `/blue/.../annotations_hmms/output_to_input/BLOCK_deeploc/*_deeploc_predictions.csv` |
| **InterProScan Pfam** on species70 | ✅ Complete, 70/70 species | Lives at `/blue/.../annotations_hmms/output_to_input/BLOCK_interproscan_parsed/pfam/pfam-<phyloname>.tsv` |
| ~~**TMBed** on species70~~ | ❌ Abandoned — DeepLoc replaces it (better fit: predicts TM probability **and** cell-membrane/extracellular localization in one tool) | Original TMBed run failed due to `transformers<5` incompatibility with `tmbed 1.0.2`. Not pursued. |

## Pipeline Logic (Moroz spec, 2026-05-17)

Sequential KEEPER/DROPPER filters. Each script's KEEPER output is the next script's input.

| # | Script | Filter | KEEPER definition | DROPPER definition |
|---|---|---|---|---|
| 001 | SignalP6 signal peptide | `Sec/SPI` only (classical secretory) | protein has SignalP6 prediction = `Sec/SPI` | no SignalP prediction OR `Sec/SPII` (lipoprotein) OR `Tat/SPI` (Tat) |
| 002 | DeepLoc TM / localization | replaces the originally-spec'd TMBed step | low `Transmembrane` probability AND/OR high `Extracellular` probability (exact thresholds TBD with user when scripting resumes) | high TM probability OR localized away from secretory path |
| 003 | Pfam domain composition (strict) | unchanged from original spec | (unique Pfam accessions = 1 AND total Pfam hits ≤ 4) OR (unique Pfam accessions = 2 AND total Pfam hits = 2) | everything else (e.g., 5+ copies of one domain; 3+ unique domains; mixed like 2-of-A + 1-of-B) |
| 004–010 | TBD | TBD | TBD | TBD |

### Decisions captured 2026-05-20/21

- **Build location**: `~/secretome/` (typo `secreteome` corrected to `secretome`); will rsync into `gigantic_project-COPYME/subprojects/secretome/` once `/blue/` space is restored.
- **First BLOCK name**: `BLOCK_secretome_per_moroz_17may2026`.
- **SignalP keeper type**: `Sec/SPI` only.
- **TM/membrane tool**: DeepLoc 2.0 (replaces TMBed). Reason: DeepLoc gives TM probability AND specific compartment probabilities (Cell membrane, Extracellular, Cytoplasm, Nucleus, ER, Golgi, etc.), which matches the original "cell membrane only" intent natively. TMBed only predicts per-residue TM topology — no localization — and is currently broken in the shared conda env.
- **Pfam edge cases**: Strict interpretation (1–4 of one OR exactly 2 different).

### Known open questions (revisit when scripting resumes)

1. **DeepLoc thresholds** for Script 002: choose probability cutoffs for `Transmembrane` (e.g., < 0.5) and `Extracellular` (e.g., ≥ 0.5). Also decide if "Cell membrane only" is a separate downstream track or just a secondary annotation column.
2. **SignalP `SP_Probability` anomaly**: a 2-species sample from the prior partial run showed all rows with probability ~0.0001 despite `Prediction = SP`. Verify on the new fresh run that values look biologically plausible (e.g., median ≥ 0.5 for keepers). If they still look strange, investigate SignalP run config.
3. **DeepLoc `Signals` column** has signal-peptide info too — decide whether SignalP6 remains canonical or whether DeepLoc's signal-peptide call is used as a cross-check.
4. **Pfam hit overlap**: multiple HMM hits at overlapping residue ranges for the same accession — count as 1 or N for the "≤ 4 copies" rule?

## Subproject Structure

```
secretome/
├── AI_GUIDE-secretome.md
├── README.md
├── output_to_input/                                          # symlink hub for downstream subprojects
│   └── BLOCK_secretome_per_moroz_17may2026/                  # populated by RUN-workflow.sh
├── upload_to_server/                                         # curated outputs for the GIGANTIC server (later)
└── BLOCK_secretome_per_moroz_17may2026/
    └── workflow-COPYME-secretome_per_moroz_17may2026/
        ├── START_HERE-user_config.yaml                       # USER edits this before running
        ├── RUN-workflow.sh                                   # unified entrypoint: local or SLURM via execution_mode in YAML
        ├── INPUT_user/                                       # user-supplied inputs (manifests, FASTAs, ...)
        └── ai/
            ├── main.nf
            ├── nextflow.config
            ├── conda_environment.yml                         # auto-created on first run
            ├── AI_GUIDE-secretome_per_moroz_17may2026_workflow.md
            └── scripts/                                      # NNN_ai-python-*.py (to be defined)
```

Single BLOCK because the work is independently runnable — no internal sequential phases. Multi-BLOCK structure can be added later if the subproject grows (e.g., `BLOCK_secretome_per_moroz_17may2026`, `BLOCK_<later_analysis>/`).

## Upstream Sources

| Source | Path (absolute, current build phase) | Format / key columns | Used by |
|---|---|---|---|
| species70 proteome FASTAs | `/blue/.../genomesDB/output_to_input/STEP_4-create_final_species_set/species70_gigantic_T1_proteomes/<phyloname>-T1-proteome.aa` | FASTA; headers `g_<gene>-t_<rna>-p_<protein>-n_<phyloname>` | Script 001 (parse identifiers) |
| species70 phyloname map | `/blue/.../phylonames/output_to_input/STEP_1-generate_and_evaluate/maps/species70_map-genus_species_X_phylonames.tsv` | TSV: `genus_species`, `phyloname`, `phyloname_taxonid` | All scripts (canonical species order) |
| SignalP6 predictions | (post-rerun) `~/temporary_annotations/BLOCK_signalp/workflow-COPYME-run_signalp/OUTPUT_pipeline/2-output/<phyloname>_signalp_predictions.tsv` → eventually `/blue/.../annotations_hmms/output_to_input/BLOCK_signalp/` | TSV: `Protein_Identifier`, `Prediction` (Sec/SPI \| Sec/SPII \| Tat/SPI), `Cleavage_Site_Position`, `SP_Probability` | Script 001 |
| DeepLoc 2.0 predictions | `/blue/.../annotations_hmms/output_to_input/BLOCK_deeploc/<phyloname>_deeploc_predictions.csv` | CSV: `Protein_ID`, `Localizations`, `Signals`, `Membrane types`, `Cytoplasm`, `Nucleus`, `Extracellular`, `Cell membrane`, `Mitochondrion`, `Plastid`, `Endoplasmic reticulum`, `Lysosome/Vacuole`, `Golgi apparatus`, `Peroxisome`, `Peripheral`, `Transmembrane`, `Lipid anchor`, `Soluble` | Script 002 |
| InterProScan Pfam | `/blue/.../annotations_hmms/output_to_input/BLOCK_interproscan_parsed/pfam/pfam-<phyloname>.tsv` | TSV (multi-row per protein): `Protein_Identifier`, `MD5`, `Sequence_Length`, `Analysis_Database` (Pfam), `Accession` (PF#####), `Description`, `Match_Start`, `Match_End`, `Score_Or_Evalue`, … | Script 003 |

## Output Schema

TODO — define once table outputs are specified (column headers must follow GIGANTIC self-documenting convention: `Header_ID (description with spaces)`).

## Path Portability

Two ways inputs can be specified in `START_HERE-user_config.yaml`:

| Build phase | Path style |
|---|---|
| Under `~/secretome/` (current) | Absolute `/blue/moroz/share/.../` |
| Inside `gigantic_project-COPYME/subprojects/secretome/` (post-rsync) | Relative `../../../<subproject>/output_to_input/...` |

The workflow code reads these from YAML — no `main.nf` edits needed when switching path styles.

## Server Hosting

To be added after first run review, matching the canonical pattern (`upload_to_server/upload_manifest.tsv` + subproject-root `RUN-update_upload_to_server.sh`).

## Where to Look Next

- `BLOCK_secretome_per_moroz_17may2026/workflow-COPYME-secretome_per_moroz_17may2026/ai/AI_GUIDE-secretome_per_moroz_17may2026_workflow.md` — workflow execution
- `BLOCK_secretome_per_moroz_17may2026/workflow-COPYME-secretome_per_moroz_17may2026/START_HERE-user_config.yaml` — edit before running
