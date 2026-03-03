# AI_GUIDE-tmbed.md (Level 2: Tool Project Guide)

**For AI Assistants**: Read `../AI_GUIDE-annotations_hmms.md` first for subproject overview and tool comparison. This guide covers tmbed-specific concepts.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE-project.md` |
| Annotations overview, tool comparison | `../AI_GUIDE-annotations_hmms.md` |
| tmbed concepts | This file |
| Running the workflow | `workflow-COPYME-run_tmbed/ai/AI_GUIDE-tmbed_workflow.md` |

## tmbed Overview

tmbed predicts transmembrane protein topology using protein language models (ProtTrans). It identifies transmembrane helices, beta-barrels, and signal peptides from amino acid sequences alone, producing a per-residue topology annotation.

**Key feature**: Produces topology strings where each residue is assigned a state (H/h for transmembrane helices, B/b for beta-barrels, S for signal peptides, . for other). The database builder parses these to extract transmembrane helix boundary coordinates.

## Pipeline Scripts (2 steps)

| # | Script | Purpose |
|---|--------|---------|
| 001 | `001_ai-python-validate_proteome_manifest.py` | Validate proteome manifest and file existence |
| 002 | `002_ai-bash-run_tmbed.sh` | Run tmbed on each species proteome |

## tmbed Command

```bash
tmbed predict -f INPUT -p OUTPUT --use-gpu --cpu-fallback --batch-size 1
```

- `--use-gpu`: Use GPU acceleration if available
- `--cpu-fallback`: Fall back to CPU if GPU unavailable
- `--batch-size 1`: Process one sequence at a time (prevents GPU memory issues)

## tmbed Output Format

3-line format per protein:
```
>protein_id
MKLF...  (amino acid sequence)
....HHHHHHHHHH....hhhhhhhhhh....  (topology string)
```

Topology codes:
- `H`/`h`: Transmembrane helix (inside-to-outside / outside-to-inside)
- `B`/`b`: Beta-barrel transmembrane (inside-to-outside / outside-to-inside)
- `S`: Signal peptide
- `.`: Other (cytoplasmic, extracellular, periplasmic)

The database builder parses consecutive H/h characters to extract helix boundary coordinates, creating one row per transmembrane helix.

## Configuration

Edit `workflow-COPYME-run_tmbed/tmbed_config.yaml`:
- `batch_size`: Sequences per batch (default: 1)
- `use_gpu`: Enable GPU (default: true)
- `cpu_fallback`: Fall back to CPU if no GPU (default: true)

## Resource Requirements

tmbed uses GPU acceleration:
- **GPU**: a100 recommended
- **CPU**: 4 cores (fallback mode)
- **Memory**: 32 GB
- **Time**: 48 hours for large species sets
