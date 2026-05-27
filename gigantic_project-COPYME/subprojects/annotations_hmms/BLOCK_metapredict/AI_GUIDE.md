# AI_GUIDE.md (Level 2: Tool Project Guide)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (subproject): [`../AI_GUIDE.md`](../AI_GUIDE.md)
- Parent (subproject README): [`../README.md`](../README.md)
- Workflow template: [`workflow-COPYME-run_metapredict/`](workflow-COPYME-run_metapredict/)
- This BLOCK's workflow AI guide: [`workflow-COPYME-run_metapredict/ai/AI_GUIDE.md`](workflow-COPYME-run_metapredict/ai/AI_GUIDE.md)
- Tool: MetaPredict
- Scripts: 4 (final = `write_run_log` per §45)
- Conda env: `aiG-annotations_hmms-metapredict`
- Reads FROM: `../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs TO: `../output_to_input/BLOCK_metapredict/` (symlinks)
- Downstream: `../BLOCK_build_annotation_database/` consumes for integrated 7-column DB
- Note: Pip-installed inside its conda env.

---

**For AI Assistants**: Read `../AI_GUIDE.md` first for subproject overview and tool comparison. This guide covers MetaPredict-specific concepts.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE.md` |
| Annotations overview, tool comparison | `../AI_GUIDE.md` |
| MetaPredict concepts | This file |
| Running the workflow | `workflow-COPYME-run_metapredict/ai/AI_GUIDE.md` |

## MetaPredict Overview

MetaPredict predicts intrinsic disorder in proteins using deep learning. It identifies intrinsically disordered regions (IDRs) - segments of proteins that lack stable 3D structure under physiological conditions. These regions are functionally important for protein-protein interactions, signaling, and regulation.

**Key feature**: Lightweight, CPU-only tool with fast execution. Predicts three complementary properties: per-residue disorder scores, IDR boundary regions, and predicted pLDDT (AlphaFold confidence) scores.

## Pipeline Scripts (2 steps)

| # | Script | Purpose |
|---|--------|---------|
| 001 | `001_ai-python-validate_proteome_manifest.py` | Validate proteome manifest and file existence |
| 002 | `002_ai-bash-run_metapredict.sh` | Run MetaPredict on each species proteome |

## MetaPredict Prediction Types

Three outputs per species:
1. **Disorder scores**: Per-residue disorder probability (0-1)
2. **IDR regions**: Boundaries of intrinsically disordered regions
3. **pLDDT scores**: Predicted AlphaFold confidence scores

The database builder uses IDR region boundaries as coordinates (Start=region_start, Stop=region_end), creating one row per disordered region.

## Configuration

Edit `workflow-COPYME-run_metapredict/START_HERE-user_config.yaml`:
- `prediction_types`: Which predictions to run (default: disorder, idrs, plddt)

## Resource Requirements

MetaPredict is lightweight and CPU-only:
- **CPU**: 2 cores
- **Memory**: 8 GB
- **Time**: 24 hours for large species sets
- **No GPU needed**

## Cluster-Side Failure: Drain-Node Race

MetaPredict burst submissions can hit the HiPerGator post-upgrade drain-node race documented at the subproject level — jobs die in 0-1 sec with `ExitCode 0:53` on `c0706a-s7/9/10/12`. If you adopt high-volume burst mode for MetaPredict and start seeing these, see [`../AI_GUIDE.md`](../AI_GUIDE.md) ("HiPerGator Drain-Node Race") for the diagnosis and the canonical `errorStrategy='ignore'` + `detect_failed_chunks` pattern (reference implementation in [`../BLOCK_interproscan/`](../BLOCK_interproscan/)).
