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
vi deeploc_config.yaml
bash RUN-workflow.sh
```

## Pipeline Steps

1. **Validate inputs** - Check proteome files exist and are valid FASTA format
2. **Run DeepLoc** - Execute DeepLoc subcellular localization prediction on each species proteome

## Key Configuration

- `deeploc_config.yaml` - Set DeepLoc install path, model type (fast/accurate), GPU settings, and species list
- `INPUT_user/` - Proteome FASTA files or manifest pointing to genomesDB proteomes

## Verification Commands

```bash
# Check output files exist (one per species)
ls OUTPUT_pipeline/2-output/*.tsv | wc -l

# Check file sizes are reasonable (not empty)
wc -l OUTPUT_pipeline/2-output/*.tsv

# Check output headers (should include localization categories)
head -1 OUTPUT_pipeline/2-output/*.tsv

# Verify all species were processed
ls OUTPUT_pipeline/2-output/*.tsv | wc -l
ls INPUT_user/*.aa | wc -l
```

## Common Errors

| Error | Solution |
|-------|----------|
| `CUDA not available` / `GPU not found` | Install CUDA drivers or switch to CPU mode in config (much slower) |
| `Model not downloaded` | Run DeepLoc model download step first (see DeepLoc documentation) |
| `Python version mismatch` | DeepLoc requires specific Python version; check conda environment matches |
| `No input files found` | Check INPUT_user/ contains proteome files and config points to correct directory |
| Very slow runtime | Enable GPU mode; CPU prediction for large proteomes can take days per species |
| Stale cached results after script update | Delete `work/` and `.nextflow*`, re-run without `-resume` |
