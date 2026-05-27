# AI_GUIDE.md (Level 2: Tool Project Guide)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent (subproject): [`../AI_GUIDE.md`](../AI_GUIDE.md)
- Parent (subproject README): [`../README.md`](../README.md)
- Workflow template: [`workflow-COPYME-run_tmbed/`](workflow-COPYME-run_tmbed/)
- This BLOCK's workflow AI guide: [`workflow-COPYME-run_tmbed/ai/AI_GUIDE.md`](workflow-COPYME-run_tmbed/ai/AI_GUIDE.md)
- Tool: TMBed
- Scripts: 5 (final = `write_run_log` per §45)
- Conda env: `aiG-annotations_hmms-tmbed`
- Reads FROM: `../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs TO: `../output_to_input/BLOCK_tmbed/` (symlinks)
- Downstream: `../BLOCK_build_annotation_database/` consumes for integrated 7-column DB
- Note: Requires transformers<5 pin (memory project_tmbed_transformers_pinning_needed); shares the EvidentialGene long-header filter pattern from BLOCK_signalp.

---

**For AI Assistants**: Read `../AI_GUIDE.md` first for subproject overview and tool comparison. This guide covers tmbed-specific concepts.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../AI_GUIDE.md` |
| Annotations overview, tool comparison | `../AI_GUIDE.md` |
| tmbed concepts | This file |
| Running the workflow | `workflow-COPYME-run_tmbed/ai/AI_GUIDE.md` |

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

Edit `workflow-COPYME-run_tmbed/START_HERE-user_config.yaml`:
- `batch_size`: Sequences per batch (default: 1)
- `use_gpu`: Enable GPU (default: true)
- `cpu_fallback`: Fall back to CPU if no GPU (default: true)

## Resource Requirements

tmbed uses GPU acceleration:
- **GPU**: a100 recommended
- **CPU**: 4 cores (fallback mode)
- **Memory**: 32 GB
- **Time**: 48 hours for large species sets

## Cluster-Side Failure: Drain-Node Race

TMBed burst submissions can hit the same HiPerGator post-upgrade drain-node race documented at the subproject level — jobs die in 0-1 sec with `ExitCode 0:53` on `c0706a-s7/9/10/12`. If you adopt high-volume burst mode for TMBed and start seeing these, see [`../AI_GUIDE.md`](../AI_GUIDE.md) ("HiPerGator Drain-Node Race") for the diagnosis and the canonical `errorStrategy='ignore'` + `detect_failed_chunks` pattern (reference implementation in [`../BLOCK_interproscan/`](../BLOCK_interproscan/)).
