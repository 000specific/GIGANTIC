# AI Guide: analyze_gene_sizes Workflow — `gene_vs_protein` (Tier 2)

**AI**: Claude Code | Opus 4.6 | 2026 March 04
**Human**: Eric Edsinger

**For AI Assistants**: Read the subproject guide (`../../../AI_GUIDE-gene_sizes.md`)
first for the dual-tier architecture and concepts. This guide focuses on running
the **Tier 2 (`gene_vs_protein`)** workflow.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../AI_GUIDE-project.md` |
| gene_sizes concepts (incl. dual-tier) | `../../../AI_GUIDE-gene_sizes.md` |
| BLOCK overview | `../../AI_GUIDE-analyze_gene_sizes.md` |
| Running this Tier 2 workflow | This file |
| Running the Tier 1 workflow | `../../workflow-COPYME-analyze_gene_sizes-all_inclusive/ai/AI_GUIDE-analyze_gene_sizes_workflow.md` |

---

## Tier 2 in one paragraph

This workflow processes the broad-coverage tier: every species whose source
annotation has gene + CDS records (no UTR or full exon records required).
Inputs are **9-col TSVs** named `Genus_species-gene_coordinates_gene_vs_protein.tsv`.
Outputs are **4 universally-comparable cross-species metrics**: `Gene_Size`,
`CDS_Size`, `Protein_Size`, `CDS_Segment_Count`. ~64 species qualify.
Tier 1 species are also written as Tier 2 (superset overlap), so this tier
is a strict superset of the Tier 1 species set.

---

## Step-by-Step Execution

### Prerequisites
1. genomesDB STEP_4 completed (species list available)
2. Upstream `gene_coordinates` extractors have produced 9-col Tier 2 TSVs in
   `research_notebook/research_user/<speciesN>/gene_coordinates/output_to_input/gene_coordinates_gene_vs_protein/`
3. INPUT_user/ contains the per-species 9-col TSVs (typically symlinked from
   the upstream extractor output) and `gigantic_species_list.txt`
4. `START_HERE-user_config.yaml` edited with correct paths (and optional
   `proteome_dir` for GIGANTIC ID linkage)

### Running

```bash
cd workflow-COPYME-analyze_gene_sizes-gene_vs_protein/

# Local execution
bash RUN-workflow.sh

# SLURM cluster
sbatch RUN-workflow.sbatch
```

### What Happens

1. **Script 001** validates 9-col Tier 2 TSVs against the GIGANTIC species list
   - Classifies each species as PROCESSED, SKIPPED_NO_DATA, or SKIPPED_INCOMPLETE
2. **Script 002** runs in parallel per species — reads gene + CDS intervals
   and computes 11-col per-gene metrics (no UTR, no exon, no intron metrics)
   - Optionally links Source_Gene_IDs to GIGANTIC identifiers via proteome
3. **Script 003** runs in parallel per species — computes 4 ranks (Gene_Size,
   CDS_Size, Protein_Size, CDS_Segment_Count) and the 4-metric genome summary
4. **Script 004** collects all species, compiles cross-species 4-metric summary
   with processing status
5. **Script 005** writes a timestamped run-success log to `ai/logs/`
6. **RUN-workflow.sh** creates symlinks under
   `output_to_input/BLOCK_analyze_gene_sizes/gene_vs_protein/`

---

## Script Pipeline

| Process | Script | Parallelized? | Key Output |
|---------|--------|---------------|------------|
| 1 | `001_ai-python-validate_gene_size_inputs.py` | No | `1_ai-species_processing_status.tsv` |
| 2 | `002_ai-python-extract_gene_metrics.py` | Yes (per species) | `2_ai-gene_metrics-{species}.tsv` (11 cols) |
| 3 | `003_ai-python-compute_genome_wide_statistics.py` | Yes (per species) | `3_ai-ranked_gene_metrics-{species}.tsv` |
| 4 | `004_ai-python-compile_cross_species_summary.py` | No | `4_ai-cross_species_summary.tsv` (4 metrics) |
| 5 | `005_ai-python-write_run_log.py` | No | `ai/logs/run_<timestamp>-gene_sizes_success.log` |

---

## Verification Commands

```bash
# Check pipeline completed
ls OUTPUT_pipeline/4-output/4_ai-cross_species_summary.tsv

# Check species processing status
cat OUTPUT_pipeline/1-output/1_ai-species_processing_status.tsv

# Count species processed (Tier 2)
cat OUTPUT_pipeline/1-output/1_ai-species_count.txt

# Check per-species metrics
ls OUTPUT_pipeline/2-output/2_ai-gene_metrics-*.tsv | wc -l

# Confirm 4 metrics (look at header) — should see Gene_Size, CDS_Size, Protein_Size, CDS_Segment_Count
head -1 OUTPUT_pipeline/4-output/4_ai-cross_species_summary.tsv | tr '\t' '\n' | grep _Gene_count

# Check downstream symlinks under tier-specific subdir
ls -L ../../output_to_input/BLOCK_analyze_gene_sizes/gene_vs_protein/

# View 4-metric summary for one species
cat OUTPUT_pipeline/3-output/3_ai-genome_summary-Homo_sapiens.tsv
```

---

## Common Execution Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Species list not found` | Wrong path in config | Verify `gigantic_species_list` in `START_HERE-user_config.yaml` |
| `No species have valid gene structure data` | INPUT_user/ has no `*_gene_vs_protein.tsv` files | Re-run upstream `gene_coordinates` extractor or symlink its output |
| `Gene structure file not found` | Species file missing or wrong tier suffix | Look for `Genus_species-gene_coordinates_gene_vs_protein.tsv` (NOT `_all_inclusive.tsv`) |
| `No valid gene metrics computed` | TSV is not the 9-col Tier 2 schema | Verify TSV has 9 tab-separated columns matching the Tier 2 layout |
| `CRITICAL ERROR: No genome summary files` | Script 002 produced no output | Check `2-output/` per-species logs for failures |
| Tier 1 species missing here | Bug — superset behavior is broken | Re-run upstream `gene_coordinates` extractor (Tier 1 species should ALSO emit Tier 2 file) |

---

## Key Files

| File | User Edits? | Purpose |
|------|-------------|---------|
| `START_HERE-user_config.yaml` | Yes | Input paths (incl. optional `project_name`, `proteome_dir`) |
| `INPUT_user/*_gene_vs_protein.tsv` | Yes | 9-col Tier 2 gene structure data per species |
| `INPUT_user/gigantic_species_list.txt` | Yes | GIGANTIC species list |
| `RUN-workflow.sh` | No | Local runner; derives tier name from this directory's basename |
| `RUN-workflow.sbatch` | Yes (account/qos) | SLURM runner |
| `ai/main.nf` | No | Pipeline definition (9-col schema, 4 metrics) |
| `ai/nextflow.config` | No | NextFlow settings + YAML param loading |
