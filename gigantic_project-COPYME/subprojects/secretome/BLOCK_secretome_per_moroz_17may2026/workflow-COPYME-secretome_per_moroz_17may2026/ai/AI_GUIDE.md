# AI_GUIDE: secretome workflow (BLOCK_secretome_per_moroz_17may2026)

<!-- ============================================================================
AI:      Claude Code | Opus 4.7 | 2026 May 21 (initial scoping)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — BLOCK_secretome_per_moroz_17may2026 (scaffold only)
- Parent (subproject AI guide): [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md) — secretome overview + full Moroz spec detail
- Parent (project): [`../../../../AI_GUIDE.md`](../../../../AI_GUIDE.md)
- Workflow README: [`../README.md`](../README.md)
- Reads from (per Moroz spec — when scripted):
  - `../../../../annotations_hmms/output_to_input/BLOCK_signalp/`
  - `../../../../annotations_hmms/output_to_input/BLOCK_deeploc/`
  - `../../../../annotations_hmms/output_to_input/BLOCK_interproscan_parsed/pfam/`
- Outputs to: `../../../output_to_input/BLOCK_secretome_per_moroz_17may2026/` (when scripted)
- 0 scripts currently (scaffold only)
- Conda env: `aiG-secretome-secretome_per_moroz_17may2026`

---

**For AI Assistants**: Read the subproject guide (`../../../AI_GUIDE.md`) first. This guide focuses on running the workflow.

## Quick Reference

| User needs… | Go to… |
|---|---|
| GIGANTIC overview | `../../../../AI_GUIDE.md` |
| Subproject concepts, output schema, path portability | `../../../AI_GUIDE.md` |
| Running the workflow | This file |

## Quick Start

1. Edit `START_HERE-user_config.yaml` at the workflow root:
   - Set `execution_mode:` to `"local"` (run here) or `"slurm"` (submit as job)
   - If `"slurm"`: set `slurm_account:` and `slurm_qos:`
   - Verify input paths (species70 phyloname map + upstream subproject inputs)
2. Run: `bash RUN-workflow.sh`

A single entrypoint handles both modes. When `execution_mode: "slurm"`, `RUN-workflow.sh` self-submits to SLURM via `sbatch --wrap` and re-enters itself on the compute node.

On first run, the conda env `aiG-secretome-secretome_per_moroz_17may2026` is auto-created from `ai/conda_environment.yml` using `mamba` (preferred) or `conda` (fallback). Subsequent runs activate the existing env.

## Pipeline Steps

TODO — fill in once scripts are defined. Template row:

| # | Script | Purpose | Primary output |
|---|---|---|---|
| 1 | `001_ai-python-<name>.py` | TODO | `1-output/1_ai-<filename>.tsv` |

## Output Layout

```
workflow-COPYME-secretome_per_moroz_17may2026/
└── OUTPUT_pipeline/
    └── N-output/N_ai-<filename>.<ext>
```

After successful run, `RUN-workflow.sh` creates symlinks from `../../output_to_input/BLOCK_secretome_per_moroz_17may2026/<stable_name>` → the corresponding `N-output/N_ai-<filename>`. Downstream subprojects can read stable paths regardless of run number.

## Verification Commands

TODO — add table-shape / row-count / cross-source sanity checks once outputs are defined. Pattern:

```bash
# Column-count sanity
head -1 OUTPUT_pipeline/N-output/N_ai-<filename>.tsv | tr '\t' '\n' | wc -l

# Row-count sanity
wc -l OUTPUT_pipeline/N-output/*.tsv

# Symlinks created
ls -la ../../output_to_input/BLOCK_secretome_per_moroz_17may2026/
```

## Common Errors

| Error | Cause | Solution |
|---|---|---|
| `species70_phyloname_map: file not found` | Path moved or `/blue/` not mounted on host | Confirm path resolves: `ls -l <path>` |
| `aiG-secretome-secretome_per_moroz_17may2026: env exists with conflicts` | Partial previous create | `mamba env remove -n aiG-secretome-secretome_per_moroz_17may2026 -y` then re-run |
| `mamba: command not found` and `conda: command not found` | Conda module not loaded (HPC) | `module load conda` before running, or run from a node where conda is on PATH |
| SLURM job submitted but pipeline doesn't run | `execution_mode: "slurm"` set without `slurm_account` / `slurm_qos` | Edit `START_HERE-user_config.yaml`, set both, then re-run |

## NextFlow Cache Reset

Before re-running after edits to scripts or config:

```bash
rm -rf work .nextflow .nextflow.log* slurm_logs
bash RUN-workflow.sh
```

Do NOT use `-resume` after script changes — stale cached scripts can mask the fix.
