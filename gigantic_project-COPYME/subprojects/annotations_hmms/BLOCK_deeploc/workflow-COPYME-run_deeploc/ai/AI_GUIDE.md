# AI_GUIDE.md (Level 3: Workflow Execution Guide)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — DeepLoc 2.1 concepts
- Parent (subproject AI guide): [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md)
- Workflow README: [`../README.md`](../README.md)
- Reads from: `../../../../genomesDB/output_to_input/STEP_4-create_final_species_set/speciesN_gigantic_T1_proteomes/`
- Outputs to: `../../../output_to_input/BLOCK_deeploc/`
- 3 scripts in `scripts/` (final = `write_run_log` per §45)
- Conda env: `aiG-annotations_hmms-deeploc`
- Note: GPU workflow (hpg-turin L4 or hpg-b200).

---

**For AI Assistants**: Read the BLOCK guide (`../AI_GUIDE.md`) first. This guide focuses on running the workflow.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../AI_GUIDE.md` |
| Annotations overview | `../../../AI_GUIDE.md` |
| DeepLoc concepts | `../../AI_GUIDE.md` |
| Running the workflow | This file |

## Quick Start

```bash
# 1. Copy template for your run
cp -r workflow-COPYME-run_deeploc workflow-RUN_1-run_deeploc
cd workflow-RUN_1-run_deeploc

# 2. Edit configuration (model type, device, SLURM settings)
vi START_HERE-user_config.yaml

# 3. Copy proteome manifest
cp /path/to/proteome_manifest.tsv INPUT_user/

# 4. Run
bash RUN-workflow.sh       # Local (needs GPU)
# For SLURM GPU job: edit execution_mode: "slurm" + slurm_account/slurm_qos in
# START_HERE-user_config.yaml; then bash RUN-workflow.sh self-submits.
```

## Pipeline Steps

1. **Validate inputs** - Check proteome files exist and are valid FASTA format
2. **Run DeepLoc** - Execute DeepLoc 2.1 subcellular localization prediction on each species proteome (GPU-accelerated)

## Key Configuration

In `START_HERE-user_config.yaml`:
- `model_type`: "Fast" (ESM1b, recommended for large datasets) or "Accurate" (ProtT5, higher quality)
- `device`: "cuda" (GPU, recommended), "cpu" (very slow), or "mps" (Mac)
- `slurm_partition`: "hpg-turin" (L4 GPUs) or "hpg-b200" (B200 GPUs)
- `slurm_gpu_type`: "l4" or "b200"
- `execution_mode`: "local" or "slurm"

In `INPUT_user/`:
- `proteome_manifest.tsv` - Tab-separated manifest with Species_Name, Proteome_Path, Phyloname columns

## Verification Commands

```bash
# Check output files exist (one CSV per species)
ls OUTPUT_pipeline/2-output/*_deeploc_predictions.csv | wc -l

# Check file sizes are reasonable (not empty)
wc -l OUTPUT_pipeline/2-output/*_deeploc_predictions.csv

# Check output headers
head -1 OUTPUT_pipeline/2-output/*_deeploc_predictions.csv | head -1

# Count species processed
ls OUTPUT_pipeline/2-output/*_deeploc_predictions.csv | wc -l
```

## Common Errors

| Error | Solution |
|-------|----------|
| `GLIBCXX_3.4.30 not found` | RUN-workflow.sh should set LD_LIBRARY_PATH automatically; verify conda env has libstdcxx-ng |
| `No module named 'pkg_resources'` | `pip install "setuptools<70"` in ai_gigantic_deeploc env |
| `invalid partition specified: gpu` | Use `hpg-turin` (L4) or `hpg-b200` (B200), not "gpu" |
| `CUDA not available` | Ensure SLURM job requests GPU via `--gres=gpu:l4:1` and uses GPU partition |
| CUDA out of memory | Switch from "Accurate" to "Fast" model, or request B200 GPU |
| Very slow runtime | Likely running on CPU; verify `device: "cuda"` and GPU is allocated |
| Stale cached results | Delete `work/` and `.nextflow*`, re-run without `-resume` |
