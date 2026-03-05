# AI_GUIDE-signalp.md (Level 2: Tool Project Guide)

**For AI Assistants**: Read `../AI_GUIDE-annotations_hmms.md` first for subproject overview and tool comparison. This guide covers SignalP-specific concepts.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE-project.md` |
| Annotations overview, tool comparison | `../AI_GUIDE-annotations_hmms.md` |
| SignalP concepts | This file |
| Running the workflow | `workflow-COPYME-run_signalp/ai/AI_GUIDE-signalp_workflow.md` |

## SignalP Overview

SignalP 6 predicts the presence of signal peptides and their cleavage sites using deep learning. Signal peptides are short N-terminal sequences that direct proteins to the secretory pathway. SignalP distinguishes between Sec/SPI (standard signal peptides), Tat/SPI (twin-arginine), and lipoprotein signal peptides.

**Key feature**: Provides cleavage site position, enabling coordinate-based annotation (Start=1, Stop=cleavage_site).

## Pipeline Scripts (2 steps)

| # | Script | Purpose |
|---|--------|---------|
| 001 | `001_ai-python-validate_proteome_manifest.py` | Validate proteome manifest and file existence |
| 002 | `002_ai-bash-run_signalp.sh` | Run SignalP on each species proteome |

## SignalP Command

```bash
signalp6 --fastafile INPUT --output_dir OUTPUT --mode slow --organism_group eukarya
```

The "slow" mode provides maximum prediction accuracy.

## SignalP Output Format

TSV output with columns including: protein ID, prediction (SP/NO_SP), signal peptide type, cleavage site position, and probability scores. The database builder includes only proteins with predicted signal peptides, using coordinates Start=1, Stop=cleavage_site_position.

## Configuration

Edit `workflow-COPYME-run_signalp/START_HERE-user_config.yaml`:
- `organism_type`: "eukarya", "gram_positive", "gram_negative", or "archaea" (default: eukarya)
- `mode`: "slow" or "fast" (default: slow)

## Resource Requirements

SignalP is CPU-based:
- **CPU**: 4 cores
- **Memory**: 16 GB
- **Time**: 72 hours for large species sets

## Installation Notes

SignalP 6 requires a license from DTU:
- Download from: https://services.healthtech.dtu.dk/services/SignalP-6.0/
- Install into the `ai_gigantic_signalp` conda environment
