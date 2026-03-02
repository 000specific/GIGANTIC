# AI Guide: analyze_gene_sizes Workflow

**AI**: Claude Code | Opus 4.6 | 2026 March 04
**Human**: Eric Edsinger

**For AI Assistants**: Read the subproject guide (`../../AI_GUIDE-gene_sizes.md`) first.
This guide focuses on running the workflow.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../AI_GUIDE-project.md` |
| gene_sizes concepts | `../../AI_GUIDE-gene_sizes.md` |
| BLOCK overview | `../AI_GUIDE-analyze_gene_sizes.md` |
| Running this workflow | This file |

---

## Step-by-Step Execution

### Prerequisites
1. genomesDB STEP_4 completed (species list available)
2. User has created per-species gene structure TSV files in `INPUT_user/`
3. GIGANTIC species list copied to `INPUT_user/gigantic_species_list.txt`
4. `gene_sizes_config.yaml` edited with correct paths

### Running

```bash
cd workflow-COPYME-analyze_gene_sizes/

# Local execution
bash RUN-workflow.sh

# SLURM cluster
sbatch RUN-workflow.sbatch
```

### What Happens

1. **Script 001** validates user-provided gene structure TSV files against the GIGANTIC species list
   - Classifies each species as PROCESSED, SKIPPED_NO_DATA, or SKIPPED_INCOMPLETE
2. **Script 002** runs in parallel per species - reads CDS intervals and computes gene metrics
   - Optionally links Source_Gene_IDs to GIGANTIC identifiers via proteome
3. **Script 003** runs in parallel per species - computes ranks and genome summaries
4. **Script 004** collects all species, compiles cross-species summary with processing status
5. **RUN-workflow.sh** creates symlinks in output_to_input/

---

## Script Pipeline

| Process | Script | Parallelized? | Key Output |
|---------|--------|---------------|------------|
| 1 | 001_ai-python-validate_gene_size_inputs.py | No | `1_ai-species_processing_status.tsv` |
| 2 | 002_ai-python-extract_gene_metrics.py | Yes (per species) | `2_ai-gene_metrics-{species}.tsv` |
| 3 | 003_ai-python-compute_genome_wide_statistics.py | Yes (per species) | `3_ai-ranked_gene_metrics-{species}.tsv` |
| 4 | 004_ai-python-compile_cross_species_summary.py | No | `4_ai-cross_species_summary.tsv` |

---

## Verification Commands

```bash
# Check pipeline completed
ls OUTPUT_pipeline/4-output/4_ai-cross_species_summary.tsv

# Check species processing status
cat OUTPUT_pipeline/1-output/1_ai-species_processing_status.tsv

# Count species processed
cat OUTPUT_pipeline/1-output/1_ai-species_count.txt

# Check per-species metrics
ls OUTPUT_pipeline/2-output/2_ai-gene_metrics-*.tsv | wc -l

# Check downstream symlinks
ls ../output_to_input/

# View summary for one species
head OUTPUT_pipeline/3-output/3_ai-genome_summary-Homo_sapiens.tsv
```

---

## Common Execution Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Species list not found` | Wrong path in config | Verify gigantic_species_list in gene_sizes_config.yaml |
| `No species have valid gene structure data` | INPUT_user/ is empty | Add per-species TSV files to INPUT_user/ |
| `Gene structure file not found` | Species file missing | Create Genus_species-gene_coordinates.tsv in INPUT_user/ |
| `No valid gene metrics computed` | TSV data fails validation | Check column format, integer values, CDS_Intervals syntax |
| `CRITICAL ERROR: No genome summary files` | Script 002 produced no output | Check 2-output/ logs for per-species errors |

---

## Key Files

| File | User Edits? | Purpose |
|------|-------------|---------|
| `gene_sizes_config.yaml` | Yes | Input paths |
| `INPUT_user/*.tsv` | Yes | Gene structure data per species |
| `INPUT_user/gigantic_species_list.txt` | Yes | GIGANTIC species list |
| `RUN-workflow.sh` | No | Local runner |
| `RUN-workflow.sbatch` | Yes (account/qos) | SLURM runner |
| `ai/main.nf` | No | Pipeline definition |
| `ai/nextflow.config` | No | Nextflow settings |
