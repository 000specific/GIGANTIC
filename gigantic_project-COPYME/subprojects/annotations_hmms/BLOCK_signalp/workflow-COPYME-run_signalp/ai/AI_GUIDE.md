# AI_GUIDE-signalp_workflow.md (Level 3: Workflow Execution Guide)

**For AI Assistants**: Read the BLOCK guide (`../AI_GUIDE-signalp.md`) first. This guide focuses on running the workflow.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../AI_GUIDE-project.md` |
| Annotations overview | `../../../AI_GUIDE-annotations_hmms.md` |
| SignalP concepts | `../../AI_GUIDE-signalp.md` |
| Running the workflow | This file |

## Quick Start

```bash
vi START_HERE-user_config.yaml
bash RUN-workflow.sh
```

## Pipeline Steps

1. **Validate inputs** - Check proteome files exist and are valid FASTA format
2. **Run SignalP** - Execute SignalP signal peptide prediction on each species proteome

## Key Configuration

- `START_HERE-user_config.yaml` - Set SignalP install path, organism type (eukarya/gram+/gram-), and species list
- `INPUT_user/` - Proteome FASTA files or manifest pointing to genomesDB proteomes

## Verification Commands

```bash
# Check output files exist (one per species)
ls OUTPUT_pipeline/2-output/*.tsv | wc -l

# Check file sizes are reasonable (not empty)
wc -l OUTPUT_pipeline/2-output/*.tsv

# Check output headers (should include signal peptide type columns)
head -1 OUTPUT_pipeline/2-output/*.tsv

# Verify all species were processed
ls OUTPUT_pipeline/2-output/*.tsv | wc -l
ls INPUT_user/*.aa | wc -l
```

## Common Errors

| Error | Solution |
|-------|----------|
| `signalp6: command not found` | Set correct SignalP install path in config YAML; ensure conda env is activated |
| `License error` / `License expired` | Re-download SignalP from DTU Health Tech (academic license may need renewal) |
| `Organism type not recognized` | Use `eukarya` for all GIGANTIC species (eukaryotic proteomes) |
| `No input files found` | Check INPUT_user/ contains proteome files and config points to correct directory |
| Stale cached results after script update | Delete `work/` and `.nextflow*`, re-run without `-resume` |
