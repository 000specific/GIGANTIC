# AI_GUIDE.md (Level 2: Tool Project Guide)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (subproject): [`../AI_GUIDE.md`](../AI_GUIDE.md)
- Parent (subproject README): [`../README.md`](../README.md)
- Workflow template: [`workflow-COPYME-run_signalp/`](workflow-COPYME-run_signalp/)
- This BLOCK's workflow AI guide: [`workflow-COPYME-run_signalp/ai/AI_GUIDE.md`](workflow-COPYME-run_signalp/ai/AI_GUIDE.md)
- Tool: SignalP 6
- Scripts: 5 (final = `write_run_log` per §45)
- Conda env: `aiG-annotations_hmms-signalp`
- Reads FROM: `../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs TO: `../output_to_input/BLOCK_signalp/` (symlinks)
- Downstream: `../BLOCK_build_annotation_database/` consumes for integrated 7-column DB
- Note: Includes EvidentialGene multi-locus-ID filter (script 000) per memory feedback_evigene_multilocus_id_filename_limit.

---

**For AI Assistants**: Read `../AI_GUIDE.md` first for subproject overview and tool comparison. This guide covers SignalP-specific concepts.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE.md` |
| Annotations overview, tool comparison | `../AI_GUIDE.md` |
| SignalP concepts | This file |
| Running the workflow | `workflow-COPYME-run_signalp/ai/AI_GUIDE.md` |

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

## Cluster-Side Failure: Drain-Node Race

SignalP burst submissions can hit the same HiPerGator post-upgrade drain-node race documented at the subproject level — chunks die in 0-1 sec with `ExitCode 0:53` on `c0706a-s7/9/10/12`. If you adopt high-volume burst mode for SignalP and start seeing these, see [`../AI_GUIDE.md`](../AI_GUIDE.md) ("HiPerGator Drain-Node Race") for the diagnosis and the canonical `errorStrategy='ignore'` + `detect_failed_chunks` pattern (reference implementation in [`../BLOCK_interproscan/`](../BLOCK_interproscan/)).
