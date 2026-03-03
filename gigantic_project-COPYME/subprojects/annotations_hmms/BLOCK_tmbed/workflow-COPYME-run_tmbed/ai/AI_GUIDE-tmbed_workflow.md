# AI_GUIDE-tmbed_workflow.md (Level 3: Workflow Execution Guide)

**For AI Assistants**: Read the BLOCK guide (`../AI_GUIDE-tmbed.md`) first. This guide focuses on running the workflow.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../AI_GUIDE-project.md` |
| Annotations overview | `../../../AI_GUIDE-annotations_hmms.md` |
| tmbed concepts | `../../AI_GUIDE-tmbed.md` |
| Running the workflow | This file |

## Quick Start

```bash
vi tmbed_config.yaml
bash RUN-workflow.sh
```

## Pipeline Steps

1. **Validate inputs** - Check proteome files exist and are valid FASTA format
2. **Run tmbed** - Execute tmbed transmembrane topology prediction on each species proteome

## Key Configuration

- `tmbed_config.yaml` - Set batch size, GPU settings, and species list
- `INPUT_user/` - Proteome FASTA files or manifest pointing to genomesDB proteomes

## Verification Commands

```bash
# Check output files exist (one per species)
ls OUTPUT_pipeline/2-output/*.3line | wc -l

# Check file sizes are reasonable (not empty)
wc -l OUTPUT_pipeline/2-output/*.3line

# Check output format (3-line format: header, sequence, topology)
head -3 OUTPUT_pipeline/2-output/*.3line

# Verify all species were processed
ls OUTPUT_pipeline/2-output/*.3line | wc -l
ls INPUT_user/*.aa | wc -l
```

## Common Errors

| Error | Solution |
|-------|----------|
| `CUDA out of memory` | Reduce batch size in config YAML; large proteins need more GPU memory |
| `Batch size too large` | Reduce batch size; start with 1 if GPU memory is limited |
| `RuntimeError: CUDA` | Check GPU availability with `nvidia-smi`; switch to CPU mode if no GPU |
| `No input files found` | Check INPUT_user/ contains proteome files and config points to correct directory |
| Very slow runtime | Enable GPU mode; CPU prediction is significantly slower |
| Stale cached results after script update | Delete `work/` and `.nextflow*`, re-run without `-resume` |
