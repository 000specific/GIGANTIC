# AI_GUIDE-interproscan_workflow.md (Level 3: Workflow Execution Guide)

**For AI Assistants**: Read the BLOCK guide (`../AI_GUIDE-interproscan.md`) first. This guide focuses on running the workflow.

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../AI_GUIDE-project.md` |
| Annotations overview | `../../../AI_GUIDE-annotations_hmms.md` |
| InterProScan concepts | `../../AI_GUIDE-interproscan.md` |
| Running the workflow | This file |

## Quick Start

```bash
vi interproscan_config.yaml
bash RUN-workflow.sh
```

## Pipeline Steps

1. **Validate inputs** - Check proteome files exist and are valid FASTA format
2. **Chunk proteomes** - Split large proteomes into smaller batches for parallel InterProScan execution
3. **Run InterProScan** - Execute InterProScan on each chunk (19 component databases + GO terms)
4. **Combine results** - Merge per-chunk outputs into per-species annotation files

## Key Configuration

- `interproscan_config.yaml` - Set InterProScan install path, database path, chunk size, and species list
- `INPUT_user/` - Proteome FASTA files or manifest pointing to genomesDB proteomes

## Verification Commands

```bash
# Check output files exist (one per species)
ls OUTPUT_pipeline/4-output/*.tsv | wc -l

# Check file sizes are reasonable (not empty)
wc -l OUTPUT_pipeline/4-output/*.tsv

# Check output headers
head -1 OUTPUT_pipeline/4-output/*.tsv

# Verify all species were processed
ls OUTPUT_pipeline/4-output/*.tsv | wc -l
ls INPUT_user/*.aa | wc -l
```

## Common Errors

| Error | Solution |
|-------|----------|
| `interproscan.sh: not found` | Set correct InterProScan install path in config YAML |
| `java.lang.OutOfMemoryError: Java heap space` | Increase Java heap in InterProScan config or reduce chunk size |
| `Out of memory` (system) | Reduce chunk size or request more memory in SLURM sbatch |
| `No input files found` | Check INPUT_user/ contains proteome files and config points to correct directory |
| Stale cached results after script update | Delete `work/` and `.nextflow*`, re-run without `-resume` |
