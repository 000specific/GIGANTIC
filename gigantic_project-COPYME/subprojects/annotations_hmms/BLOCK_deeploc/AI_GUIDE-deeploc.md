# AI_GUIDE-deeploc.md (Level 2: Tool Project Guide)

**For AI Assistants**: Read `../AI_GUIDE-annotations_hmms.md` first for subproject overview and tool comparison. This guide covers DeepLoc-specific concepts.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE-project.md` |
| Annotations overview, tool comparison | `../AI_GUIDE-annotations_hmms.md` |
| DeepLoc concepts | This file |
| Running the workflow | `workflow-COPYME-run_deeploc/ai/AI_GUIDE-deeploc_workflow.md` |

## DeepLoc Overview

DeepLoc 2.1 predicts subcellular protein localization using deep learning. It classifies proteins into cellular compartments (cytoplasm, nucleus, extracellular, membrane, mitochondrion, etc.) and predicts whether proteins are membrane-bound or soluble, and whether they have signal peptides.

**Key feature**: Whole-protein prediction (no domain coordinates). Each protein gets a single localization assignment with confidence scores.

## Pipeline Scripts (2 steps)

| # | Script | Purpose |
|---|--------|---------|
| 001 | `001_ai-python-validate_proteome_manifest.py` | Validate proteome manifest and file existence |
| 002 | `002_ai-bash-run_deeploc.sh` | Run DeepLoc on each species proteome |

## DeepLoc Command

```bash
deeploc2 -f INPUT -o OUTPUT --model Accurate
```

The "Accurate" model provides higher-quality predictions at the cost of longer runtime.

## DeepLoc Output Format

CSV with columns including: protein ID, localization, signal peptide, membrane type, and confidence scores per compartment. The database builder parses this into the standardized 7-column format with Start=NA, Stop=NA (whole-protein prediction).

## Configuration

Edit `workflow-COPYME-run_deeploc/deeploc_config.yaml`:
- `model_type`: "Accurate" or "Fast" (default: Accurate)

## Resource Requirements

DeepLoc uses GPU acceleration:
- **GPU**: a100 recommended
- **CPU**: 4 cores
- **Memory**: 32 GB
- **Time**: 48 hours for large species sets

## Installation Notes

DeepLoc requires manual download from DTU (academic license):
- Download from: https://services.healthtech.dtu.dk/services/DeepLoc-2.1/
- Requires Python 3.10 (not compatible with 3.11+)
- Install into the `ai_gigantic_deeploc` conda environment
