# AI_GUIDE-deeploc_workflow.md (Level 3: Workflow Execution Guide)

**For AI Assistants**: Read the BLOCK guide (`../AI_GUIDE-deeploc.md`) first. This guide focuses on running the workflow.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../AI_GUIDE-project.md` |
| Annotations overview | `../../../AI_GUIDE-annotations_hmms.md` |
| DeepLoc concepts | `../../AI_GUIDE-deeploc.md` |
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
sbatch RUN-workflow.sbatch # SLURM GPU job (edit account/qos first)
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
