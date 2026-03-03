# AI_GUIDE-metapredict_workflow.md (Level 3: Workflow Execution Guide)

**For AI Assistants**: Read the BLOCK guide (`../AI_GUIDE-metapredict.md`) first. This guide focuses on running the workflow.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../AI_GUIDE-project.md` |
| Annotations overview | `../../../AI_GUIDE-annotations_hmms.md` |
| MetaPredict concepts | `../../AI_GUIDE-metapredict.md` |
| Running the workflow | This file |

## Quick Start

```bash
vi metapredict_config.yaml
bash RUN-workflow.sh
```

## Pipeline Steps

1. **Validate inputs** - Check proteome files exist and are valid FASTA format
2. **Run MetaPredict** - Execute MetaPredict disorder prediction on each species proteome

## Key Configuration

- `metapredict_config.yaml` - Set disorder threshold, and species list
- `INPUT_user/` - Proteome FASTA files or manifest pointing to genomesDB proteomes

## Verification Commands

```bash
# Check output files exist (one per species)
ls OUTPUT_pipeline/2-output/*.tsv | wc -l

# Check file sizes are reasonable (not empty)
wc -l OUTPUT_pipeline/2-output/*.tsv

# Check output headers (should include disorder scores)
head -1 OUTPUT_pipeline/2-output/*.tsv

# Verify all species were processed
ls OUTPUT_pipeline/2-output/*.tsv | wc -l
ls INPUT_user/*.aa | wc -l
```

## Common Errors

| Error | Solution |
|-------|----------|
| `ModuleNotFoundError: metapredict` | Install metapredict in conda environment: `pip install metapredict` |
| `No input files found` | Check INPUT_user/ contains proteome files and config points to correct directory |
| Unexpected empty output | Check input FASTA files are valid (no corrupt sequences or empty files) |
| Stale cached results after script update | Delete `work/` and `.nextflow*`, re-run without `-resume` |
