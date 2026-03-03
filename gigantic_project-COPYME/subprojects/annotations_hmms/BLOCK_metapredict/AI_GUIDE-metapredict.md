# AI_GUIDE-metapredict.md (Level 2: Tool Project Guide)

**For AI Assistants**: Read `../AI_GUIDE-annotations_hmms.md` first for subproject overview and tool comparison. This guide covers MetaPredict-specific concepts.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE-project.md` |
| Annotations overview, tool comparison | `../AI_GUIDE-annotations_hmms.md` |
| MetaPredict concepts | This file |
| Running the workflow | `workflow-COPYME-run_metapredict/ai/AI_GUIDE-metapredict_workflow.md` |

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

Edit `workflow-COPYME-run_metapredict/metapredict_config.yaml`:
- `prediction_types`: Which predictions to run (default: disorder, idrs, plddt)

## Resource Requirements

MetaPredict is lightweight and CPU-only:
- **CPU**: 2 cores
- **Memory**: 8 GB
- **Time**: 24 hours for large species sets
- **No GPU needed**
