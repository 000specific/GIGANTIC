# AI Guide: analyze_gene_sizes Workflow — `all_inclusive` (Tier 1)

<!-- ============================================================================
AI:      Claude Code | Opus 4.6 | 2026 March 04 (initial)
AI:      Claude Code | Opus 4.7 (1M context) | 2026 May 26 (detailed eval pass)
Human:   Eric Edsinger
============================================================================ -->

## Where this fits

- Parent BLOCK guide: [`../../AI_GUIDE.md`](../../AI_GUIDE.md) — BLOCK_analyze_gene_sizes
- Parent (subproject AI guide): [`../../../AI_GUIDE.md`](../../../AI_GUIDE.md) — dual-tier architecture
- Workflow README: [`../README.md`](../README.md)
- Tier: **Tier 1** (15-col TSV; 7 metrics; ~40 species)
- Reads from: per-species gene-coordinate TSVs in `../INPUT_user/`
- Outputs to: `../../../output_to_input/BLOCK_analyze_gene_sizes/all_inclusive/`
- 5 scripts: 001 validate / 002 extract / 003 stats / 004 cross-species / 005 `write_run_log`
- Conda env: `aiG-gene_sizes-analyze_gene_sizes`

---

**For AI Assistants**: Read the subproject guide (`../../../AI_GUIDE.md`)
first for the dual-tier architecture and concepts. This guide focuses on running
the **Tier 1 (`all_inclusive`)** workflow.

---

## Quick Reference

| User needs... | Go to... |
|---------------|----------|
| GIGANTIC overview | `../../../../AI_GUIDE.md` |
| gene_sizes concepts (incl. dual-tier) | `../../../AI_GUIDE.md` |
| BLOCK overview | `../../AI_GUIDE.md` |
| Running this Tier 1 workflow | This file |
| Running the Tier 2 workflow | `../../workflow-COPYME-analyze_gene_sizes-gene_vs_protein/ai/AI_GUIDE.md` |

---

## Tier 1 in one paragraph

This workflow processes the methodology-strict tier: only species whose source
annotations include UTR-bearing exon records for ≥50% of genes. Inputs are
**15-col TSVs** named `Genus_species-gene_coordinates_all_inclusive.tsv`.
Outputs are **7 cross-species metrics**: `Gene_Size`, `Transcript_Size`,
`CDS_Size`, `Protein_Size`, `Exon_Count`, `Intron_Total_Size`, `UTR_Total_Size`.
~40 species qualify. Tier 1 species are a strict subset of Tier 2 species.

---

## Step-by-Step Execution

### Prerequisites
1. genomesDB STEP_4 completed (species list available)
2. Upstream `gene_coordinates` extractors have produced 15-col Tier 1 TSVs in
   `research_notebook/research_user/<speciesN>/gene_coordinates/output_to_input/gene_coordinates_all_inclusive/`
3. INPUT_user/ contains the per-species 15-col TSVs (typically symlinked from
   the upstream extractor output) and `gigantic_species_list.txt`
4. `START_HERE-user_config.yaml` edited with correct paths (and optional
   `proteome_dir` for GIGANTIC ID linkage)

### Running

```bash
cd workflow-COPYME-analyze_gene_sizes-all_inclusive/

# Local execution
bash RUN-workflow.sh

# SLURM cluster: edit START_HERE-user_config.yaml
#   set execution_mode: "slurm", fill in slurm_account / slurm_qos
# Then run the same command (script self-submits):
bash RUN-workflow.sh
```

### What Happens

1. **Script 001** validates 15-col Tier 1 TSVs against the GIGANTIC species list
   - Classifies each species as PROCESSED, SKIPPED_NO_DATA, or SKIPPED_INCOMPLETE
2. **Script 002** runs in parallel per species — reads exon + CDS + UTR intervals
   and computes 15-col per-gene metrics
   - Optionally links Source_Gene_IDs to GIGANTIC identifiers via proteome
3. **Script 003** runs in parallel per species — computes 6 ranks (Gene_Size,
   Transcript_Size, CDS_Size, Protein_Size, Exon_Count, Intron_Total_Size) and
   the 7-metric genome summary
4. **Script 004** collects all species, compiles cross-species 7-metric summary
   with processing status
5. **Script 005** writes a timestamped run-success log to `ai/logs/`
6. **RUN-workflow.sh** creates symlinks under
   `output_to_input/BLOCK_analyze_gene_sizes/all_inclusive/`

---

## Script Pipeline

| Process | Script | Parallelized? | Key Output |
|---------|--------|---------------|------------|
| 1 | `001_ai-python-validate_gene_size_inputs.py` | No | `1_ai-species_processing_status.tsv` |
| 2 | `002_ai-python-extract_gene_metrics.py` | Yes (per species) | `2_ai-gene_metrics-{species}.tsv` (15 cols) |
| 3 | `003_ai-python-compute_genome_wide_statistics.py` | Yes (per species) | `3_ai-ranked_gene_metrics-{species}.tsv` |
| 4 | `004_ai-python-compile_cross_species_summary.py` | No | `4_ai-cross_species_summary.tsv` (7 metrics) |
| 5 | `005_ai-python-write_run_log.py` | No | `ai/logs/run_<timestamp>-gene_sizes_success.log` |

---

## Verification Commands

```bash
# Check pipeline completed
ls OUTPUT_pipeline/4-output/4_ai-cross_species_summary.tsv

# Check species processing status
cat OUTPUT_pipeline/1-output/1_ai-species_processing_status.tsv

# Count species processed (Tier 1)
cat OUTPUT_pipeline/1-output/1_ai-species_count.txt

# Check per-species metrics
ls OUTPUT_pipeline/2-output/2_ai-gene_metrics-*.tsv | wc -l

# Confirm 7 metrics (look at header) — should see Gene_Size, Transcript_Size, CDS_Size, Protein_Size, Exon_Count, Intron_Total_Size, UTR_Total_Size
head -1 OUTPUT_pipeline/4-output/4_ai-cross_species_summary.tsv | tr '\t' '\n' | grep _Gene_count

# Check downstream symlinks under tier-specific subdir
ls -L ../../output_to_input/BLOCK_analyze_gene_sizes/all_inclusive/

# View 7-metric summary for one species
cat OUTPUT_pipeline/3-output/3_ai-genome_summary-Homo_sapiens.tsv
```

---

## Common Execution Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `Species list not found` | Wrong path in config | Verify `gigantic_species_list` in `START_HERE-user_config.yaml` |
| `No species have valid gene structure data` | INPUT_user/ has no `*_all_inclusive.tsv` files | Re-run upstream `gene_coordinates` extractor or symlink its output |
| `Gene structure file not found` | Species file missing or wrong tier suffix | Look for `Genus_species-gene_coordinates_all_inclusive.tsv` (NOT `_gene_vs_protein.tsv`) |
| `No valid gene metrics computed` | TSV is not the 15-col Tier 1 schema | Verify TSV has 15 tab-separated columns matching the Tier 1 layout |
| `CRITICAL ERROR: No genome summary files` | Script 002 produced no output | Check `2-output/` per-species logs for failures |
| Many species PROCESSED in Tier 2 but missing here | Expected — those species are Tier 2-only | Run the Tier 2 workflow for the broader set |

---

## Key Files

| File | User Edits? | Purpose |
|------|-------------|---------|
| `START_HERE-user_config.yaml` | Yes | Input paths (incl. optional `project_name`, `proteome_dir`) |
| `INPUT_user/*_all_inclusive.tsv` | Yes | 15-col Tier 1 gene structure data per species |
| `INPUT_user/gigantic_species_list.txt` | Yes | GIGANTIC species list |
| `RUN-workflow.sh` | No | Unified runner (local or SLURM via execution_mode in YAML); derives tier from this directory's basename |
| `ai/main.nf` | No | Pipeline definition (15-col schema, 7 metrics) |
| `ai/nextflow.config` | No | NextFlow settings + YAML param loading |
